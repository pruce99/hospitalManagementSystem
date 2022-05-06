# imports
import enum
import random
import os
import time
import socket
import json
import threading
from MainApp import nodes
from . import models
from django.forms.models import model_to_dict
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist
from collections import defaultdict
import requests
from . import views

# RAFT environment
current_term = voted_for = log = state = None
timeout_interval = heartbeat_interval = 0
kill_threads_flag = False
# log replication
index = 1
commit_index = 0
last_applied = 0
next_index = {node: 1 for node in nodes}
match_index = {node: 0 for node in nodes}
# ports
request_vote_rpc_listener_port = 9000
vote_acknowledgement_listener_port = 9001
append_entry_rpc_listener_port = 9002
msg_rpc_listener_port = 9003
append_reply_rpc_listener_port = 9004
apply_commits_listener_port = 9005
controller_rpc_listener_port = 5555
# controller details
controller_id = 'Controller'
controller_port = 5555
# timers
timeout_timer = threading.Timer(0, lambda _: _)  # Dummy Timer
heartbeat_timer = threading.Timer(0, lambda _: _)  # Dummy Timer
# response
respond_to = controller_id


# state enum
class State(enum.Enum):
    Follower = 0
    Candidate = 1
    Leader = 2


# controller requests
class Request(enum.Enum):
    CONVERT_FOLLOWER = 'CONVERT_FOLLOWER'
    TIMEOUT = 'TIMEOUT'
    SHUTDOWN = 'SHUTDOWN'
    LEADER_INFO = 'LEADER_INFO'
    STORE = 'STORE'
    RETRIEVE = 'RETRIEVE'


# helpers
def set_timeout_interval():
    """
        Returns timeout interval in milliseconds
    """
    return random.randint(200, 300)


def udp_send(target: tuple, msg: dict):
    # create socket for sender
    udp_sender_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    msg_bytes = json.dumps(msg).encode()
    # send the message to target
    udp_sender_socket.sendto(msg_bytes, (target[0], target[1]))


def ask_nodes_to_send_leader_info():
    for node in nodes:
        if node != os.environ['node_id']:
            udp_send(target=(node, msg_rpc_listener_port), msg={'name': 'LEADER_INFO'})


def init():
    global current_term, voted_for, log, heartbeat_interval, state
    current_term = 0  # very first term is zero
    voted_for = dict()
    log = list()
    heartbeat_interval = 100  # in milliseconds
    state = State.Follower  # every node starts as Follower


def append_entry_rpc(node: str):
    global current_term, append_entry_rpc_listener_port, next_index, commit_index
    try:
        entry = models.Logs.objects.get(index=next_index[node])
    except ObjectDoesNotExist:
        entry = None
    prev_log_index = next_index[node] - 1
    try:
        obj = models.Logs.objects.get(index=prev_log_index)
        prev_log_term = obj.term
    except ObjectDoesNotExist:
        prev_log_term = 0
    msg = {
        'term': current_term,
        'leader_id': os.environ['node_id'],
        'entry': None if entry is None else model_to_dict(
            entry,
            fields=['index', 'term', 'key', 'value'],
        ),
        'prev_log_index': prev_log_index,
        'prev_log_term': prev_log_term,
        'commit_index': commit_index,
    }
    udp_send(target=(node, append_entry_rpc_listener_port), msg=msg)
    # print(f"Sent {'heartbeat' if is_heartbeat else 'append_entry_rpc'} - term - {current_term} SENT to {node}")


def append_entry_rpc_listener(sock: socket.socket):
    global state, timeout_timer, current_term, kill_threads_flag, commit_index
    print('Starting append_entry_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        while kill_threads_flag:
            pass
        state = State.Follower
        timeout_timer.cancel()  # stop the timeout_timer
        new_timeout_timer()  # get new timeout_timer
        timeout_timer.start()  # restart timeout_timer with different timeout_interval
        append_entry = json.loads(msg.decode('utf-8'))  # decoded msg
        if append_entry['entry'] is not None:  # skip log replication if heartbeat
            if append_entry['term'] < current_term or not log_consistency_check(append_entry):
                append_reply_rpc(append_entry['leader_id'], success=False)
            else:
                append_reply_rpc(append_entry['leader_id'], success=True)
        # update commit index
        if append_entry['commit_index'] > commit_index:
            commit_index = min(append_entry['commit_index'], index-1)
            # apply the commit to state machine
            udp_send(target=(os.environ['node_id'], apply_commits_listener_port), msg={'dummy': 'dummy'})


def apply_commits_listener(sock: socket.socket):
    global kill_threads_flag, commit_index, last_applied
    print('Starting apply_commits_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        while kill_threads_flag:
            pass
        dummy = json.loads(msg.decode('utf-8'))  # decoded msg
        not_applied_logs = models.Logs.objects.filter(index__gt=last_applied, index__lte=commit_index)
        for the_log in not_applied_logs:
            requests.post(
                url=f"http://{os.environ['node_id']}:8000/MainApp/store_patient_info/",
                data=the_log.value,
            )
            last_applied += 1


def log_consistency_check(append_entry: dict):
    global match_index, index
    # if this is the first log then push directly
    if append_entry['prev_log_index'] == 0:
        models.Logs.objects.create(
            index=index,
            term=append_entry['entry']['term'],
            key=append_entry['entry']['key'],
            value=append_entry['entry']['value'],
        )
        match_index[os.environ['node_id']] = index
        index += 1
        return True
    # check if log exists at prev_log_index
    try:
        log_at_prev_index = models.Logs.objects.get(index=append_entry['prev_log_index'])
    except ObjectDoesNotExist:
        return False
    # if term conflicts, remove the conflicting log and rest of the following logs
    if log_at_prev_index.term != append_entry['prev_log_term']:
        for each_log in models.Logs.objects.filter(index__gte=log_at_prev_index.index):
            each_log.delete()
            index -= 1
        return False
    # do not log bad entries
    if index-1 > append_entry['entry']['index']:
        return True
    # if log is consistent and if logs can be pushed, push the new log
    models.Logs.objects.create(
        index=index,
        term=append_entry['entry']['term'],
        key=append_entry['entry']['key'],
        value=append_entry['entry']['value'],
    )
    match_index[os.environ['node_id']] = index
    index += 1
    return True


def append_reply_rpc(node: str, success: bool):
    global match_index
    msg = {
        'term': current_term,
        'follower_id': os.environ['node_id'],
        'success': success,
        'match_index': match_index[os.environ['node_id']],
    }
    udp_send(target=(node, append_reply_rpc_listener_port), msg=msg)


def append_reply_rpc_listener(sock: socket.socket):
    global kill_threads_flag, match_index, next_index, commit_index, last_applied
    print('Starting append_reply_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        while kill_threads_flag:
            pass
        append_reply = json.loads(msg.decode('utf-8'))  # decoded msg
        if append_reply['success']:
            match_index[append_reply['follower_id']] = append_reply['match_index']
            next_index[append_reply['follower_id']] += 1
            next_index[append_reply['follower_id']] = min(index+1, next_index[append_reply['follower_id']])  # bound
            # update commit index of leader if a majority of the followers replicated logs
            match_index_counter = defaultdict(lambda: 0)
            for value in match_index.values():
                match_index_counter[value] += 1
            commit_index = max(match_index_counter, key=lambda _: match_index_counter[_])
            # apply the commit to state machine
            # if commit_index < last_applied:
            #     # send response back to client
            #     udp_send(
            #         target=(respond_to, controller_port if respond_to == controller_id else views.response_sock_port),
            #         msg={'status_code': 201},
            #     )
            udp_send(target=(os.environ['node_id'], apply_commits_listener_port), msg={'dummy': 'dummy'})
        else:
            next_index[append_reply['follower_id']] -= 1
            next_index[append_reply['follower_id']] = max(1, next_index[append_reply['follower_id']])  # bound


def request_vote_rpc(node: str):
    global current_term, state, request_vote_rpc_listener_port, index
    try:
        last_log = models.Logs.objects.get(index=index-1)
    except ObjectDoesNotExist:
        last_log = None
    msg = {
        'term': current_term,
        'candidate_id': os.environ['node_id'],
        'last_log_index': 0 if last_log is None else last_log.index,
        'last_log_term': 0 if last_log is None else last_log.term,
    }
    udp_send(target=(node, request_vote_rpc_listener_port), msg=msg)
    print(f'request_vote_rpc - term - {current_term} SENT to {node}')


def vote_acknowledgement_listener(sock: socket.socket):
    print('Starting vote_acknowledgement_listener')
    global state, heartbeat_timer, next_index, kill_threads_flag
    positive_votes = 0
    while True:
        msg, addr = sock.recvfrom(1024)
        while kill_threads_flag:
            pass
        ack = json.loads(msg.decode('utf-8'))  # decoded msg
        print(f"Received {'YES' if ack['vote'] else 'NO'} vote from {ack['from']}")
        if ack['vote'] == 1:
            positive_votes += 1
        # only elect leader if state is Candidate ( Make sures there is only one Leader at a time )
        # state is changed to Follower in append_entry_rpc_listener
        time.sleep(0.01)  # wait and check if the node is still candidate
        if positive_votes + 1 > len(nodes) // 2 and state is State.Candidate:
            timeout_timer.cancel()  # stop the timeout_timer for the leader
            state = State.Leader
            # init next_index
            for node in nodes:
                max_index = models.Logs.objects.aggregate(Max('index'))['index__max']
                if max_index is None:  # if log is empty
                    next_index[node] = 1
                else:
                    next_index[node] = models.Logs.objects.aggregate(Max('index'))['index__max'] + 1
            positive_votes = 0
            # start sending heartbeats
            heartbeat_timer = threading.Timer(heartbeat_interval / 1000, send_heartbeats)
            heartbeat_timer.start()


def request_vote_rpc_listener(sock: socket.socket):
    print('Starting request_vote_rpc_listener')
    global current_term, voted_for, kill_threads_flag
    while True:
        msg, addr = sock.recvfrom(1024)
        while kill_threads_flag:
            pass
        candidate = json.loads(msg.decode('utf-8'))  # decoded msg
        print(f"Received vote request from {candidate['candidate_id']} - term - {candidate['term']}")
        vote_sent_flag = False
        try:
            last_log = models.Logs.objects.get(index=index - 1)
        except ObjectDoesNotExist:
            last_log = None
        if current_term < candidate['term'] and \
                (last_log is None or not (
                    (last_log.term > candidate['last_log_term']) or
                    (last_log.term == candidate['last_log_term'] and last_log.index > candidate['last_log_index'])
                )):
            try:
                _ = voted_for[candidate['term']]
            except KeyError:
                voted_for = dict()  # remove previous term's data
                current_term = candidate['term']
                # grant vote
                voted_for[candidate['term']] = 1
                udp_send(
                    target=(candidate['candidate_id'], vote_acknowledgement_listener_port),
                    msg={'vote': 1, 'from': os.environ['node_id']}
                )
                print(f"Sent YES vote to {candidate['candidate_id']}")
                vote_sent_flag = True
        if not vote_sent_flag:
            # do not vote
            udp_send(
                target=(candidate['candidate_id'], vote_acknowledgement_listener_port),
                msg={'vote': 0, 'from': os.environ['node_id']}
            )
            print(f"Sent NO vote to {candidate['candidate_id']}")


def start_election():
    global current_term, voted_for, state
    current_term += 1  # race
    print(f'Starting elections for the term - {current_term}')
    state = State.Candidate  # race
    voted_for = {current_term: os.environ['node_id']}  # vote for itself  # race
    for node in nodes:
        if node != os.environ['node_id']:
            request_vote_rpc(node)
    print("all request_vote_rpc's sent")
    timeout_timer.cancel()  # stop the timeout_timer
    new_timeout_timer()  # get new timeout_timer
    timeout_timer.start()  # restart timeout_timer with different timeout_interval


def new_timeout_timer():
    """
        Sets timeout_timer to a new Timer object ( Used to restart timeout_intervals )
    """
    global timeout_interval, timeout_timer
    # start election when timeout_timer runs out
    timeout_interval = set_timeout_interval()
    timeout_timer = threading.Timer(timeout_interval / 1000, start_election)


def send_heartbeats():
    # print('Sending Heartbeats')
    global current_term, heartbeat_interval, heartbeat_timer, kill_threads_flag
    while kill_threads_flag:
        pass
    if state is not State.Leader:  # stop sending heartbeats once the leader stops being leader
        return
    for node in nodes:
        if node != os.environ['node_id']:
            append_entry_rpc(node)
    heartbeat_timer = threading.Timer(heartbeat_interval / 1000, send_heartbeats)
    heartbeat_timer.start()  # keep sending heartbeats


def controller_rpc_listener(sock: socket.socket):
    global state, current_term, kill_threads_flag, timeout_timer, commit_index, index, respond_to
    print('Starting controller_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        controller_request = json.loads(msg.decode('utf-8'))  # decoded msg
        respond_to = controller_request['sender_name']  # set to respond back
        if not kill_threads_flag:
            print(f"Controller Request Received - {controller_request['request']}")
        if kill_threads_flag and controller_request['request'] == Request.CONVERT_FOLLOWER.value:
            print(f"Controller Request Received - {controller_request['request']}")
        if controller_request['request'] == Request.CONVERT_FOLLOWER.value:
            kill_threads_flag = False  # awake the node if it was shut down before
            state = State.Follower
            timeout_timer.cancel()  # stop the timeout_timer
            new_timeout_timer()  # get new timeout_timer
            timeout_timer.start()  # restart timeout_timer with different timeout_interval
        elif controller_request['request'] == Request.TIMEOUT.value and not kill_threads_flag:
            timeout_timer.cancel()  # stop the timeout_timer
            start_election()  # immediately start elections
        elif controller_request['request'] == Request.SHUTDOWN.value and not kill_threads_flag:
            kill_threads_flag = True
            timeout_timer.cancel()  # stop timeout timer
        elif controller_request['request'] == Request.LEADER_INFO.value and not kill_threads_flag:
            if state is state.Leader:  # if current node is leader then send its info
                udp_send(
                    target=(controller_id, controller_port),
                    msg={
                        'sender_name': os.environ['node_id'],
                        'request': 'LEADER_INFO',
                        'term': None,
                        'key': 'LEADER',
                        'value': os.environ['node_id'],
                    }
                )
            else:  # ask all others in the cluster to send leader info to Controller, if apply
                ask_nodes_to_send_leader_info()
        elif controller_request['request'] == Request.STORE.value and not kill_threads_flag:
            if state is state.Leader:  # if current node is leader then store to its log
                models.Logs.objects.create(
                    index=index,
                    term=current_term,
                    key=controller_request['key'],
                    value=controller_request['value'],
                )
                match_index[os.environ['node_id']] = index
                index += 1
                print('Log Stored')
            else:  # ask all others in the cluster to send leader info to Controller, if apply
                ask_nodes_to_send_leader_info()
        elif controller_request['request'] == Request.RETRIEVE.value and not kill_threads_flag:
            if state is state.Leader:  # if current node is leader then send committed logs
                commited_logs = list()
                for each_log in models.Logs.objects.filter(index__lte=commit_index):
                    commited_logs.append(
                        model_to_dict(
                            each_log,
                            fields=['term', 'key', 'value'],
                        ),
                    )
                udp_send(
                    target=(controller_id, controller_port),
                    msg={
                        'sender_name': os.environ['node_id'],
                        'request': 'RETRIEVE',
                        'term': None,
                        'key': 'COMMITED_LOGS',
                        'value': commited_logs,
                    }
                )
            else:  # ask all others in the cluster to send leader info to Controller, if apply
                ask_nodes_to_send_leader_info()


def msg_rpc_listener(sock: socket.socket):
    global state, kill_threads_flag, controller_id, respond_to
    print('Starting msg_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        while kill_threads_flag:
            pass
        msg = json.loads(msg.decode('utf-8'))  # decoded msg
        if msg['name'] == Request.LEADER_INFO.value:
            if state is State.Leader:
                udp_send(
                    target=(respond_to, controller_port if respond_to == controller_id else views.response_sock_port),
                    msg={
                        'sender_name': os.environ['node_id'],
                        'request': 'LEADER_INFO',
                        'term': None,
                        'key': 'LEADER',
                        'value': os.environ['node_id'],
                    }
                )


def main():
    global timeout_timer

    init()  # initialize raft environment

    # sockets for listeners
    request_vote_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    request_vote_rpc_listener_socket.bind((os.environ['node_id'], request_vote_rpc_listener_port))

    vote_acknowledgement_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    vote_acknowledgement_listener_socket.bind((os.environ['node_id'], vote_acknowledgement_listener_port))

    append_entry_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    append_entry_rpc_listener_socket.bind((os.environ['node_id'], append_entry_rpc_listener_port))

    msg_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    msg_rpc_listener_socket.bind((os.environ['node_id'], msg_rpc_listener_port))

    controller_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    controller_rpc_listener_socket.bind((os.environ['node_id'], controller_rpc_listener_port))

    append_reply_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    append_reply_rpc_listener_socket.bind((os.environ['node_id'], append_reply_rpc_listener_port))

    apply_commits_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    apply_commits_listener_socket.bind((os.environ['node_id'], apply_commits_listener_port))

    # start listeners
    print('Starting Listeners')
    threading.Thread(target=request_vote_rpc_listener, args=[request_vote_rpc_listener_socket]).start()
    threading.Thread(target=vote_acknowledgement_listener, args=[vote_acknowledgement_listener_socket]).start()
    threading.Thread(target=append_entry_rpc_listener, args=[append_entry_rpc_listener_socket]).start()
    threading.Thread(target=msg_rpc_listener, args=[msg_rpc_listener_socket]).start()
    threading.Thread(target=controller_rpc_listener, args=[controller_rpc_listener_socket]).start()
    threading.Thread(target=append_reply_rpc_listener, args=[append_reply_rpc_listener_socket]).start()
    threading.Thread(target=apply_commits_listener, args=[apply_commits_listener_socket]).start()

    # sleep for some time to let the listeners start
    time.sleep(1)

    # start timeout_timer
    print('Start timeout_timer')
    new_timeout_timer()
    timeout_timer.start()

    # while True:
    #     print(state, current_term)
    #     if kill_threads_flag:
    #         print('Stopping Raft')
    #         return
    #     time.sleep(1)
