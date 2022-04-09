# imports
import enum
import random
import os
import time
import socket
import json
import threading
from MainApp import nodes

# RAFT environment
current_term = voted_for = log = state = None
timeout_interval = heartbeat_interval = 0
kill_threads_flag = False
# ports
request_vote_rpc_listener_port = 9000
vote_acknowledgement_listener_port = 9001
append_entry_rpc_listener_port = 9002
msg_rpc_listener_port = 9003
controller_rpc_listener_port = 5555
# controller details
controller_id = 'Controller'
controller_port = 5555
# timers
timeout_timer = threading.Timer(0, lambda _: _)  # Dummy Timer
heartbeat_timer = threading.Timer(0, lambda _: _)  # Dummy Timer


# state enum
class State(enum.Enum):
    Follower = 0
    Candidate = 1
    Leader = 2


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


def init():
    global current_term, voted_for, log, heartbeat_interval, state
    current_term = 0  # very first term is zero
    voted_for = dict()
    log = list()
    heartbeat_interval = 100  # in milliseconds
    state = State.Follower  # every node starts as Follower


def append_entry_rpc(node: str, is_heartbeat: bool):
    global current_term, append_entry_rpc_listener_port
    msg = {
        'term': current_term,
        'leader_id': os.environ['node_id'],
        'entries': None if is_heartbeat else None,  # temp
        'prev_log_index': -1,  # temp
        'prev_log_term': 0,  # temp
    }
    udp_send(target=(node, append_entry_rpc_listener_port), msg=msg)
    # print(f"Sent {'heartbeat' if is_heartbeat else 'append_entry_rpc'} - term - {current_term} SENT to {node}")


def append_entry_rpc_listener(sock: socket.socket):
    global state, timeout_timer
    print('Starting append_entry_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        if kill_threads_flag:
            print('Stopping append_entry_rpc_listener')
            exit()  # stops this listener
        append_entry = json.loads(msg.decode('utf-8'))  # decoded msg
        # print(f"Received {'heartbeat' if append_entry['entries'] is None else 'append_entry'} from "
        #       f"{append_entry['leader_id']} - term - {append_entry['term']}")
        state = State.Follower
        timeout_timer.cancel()  # stop the timeout_timer
        new_timeout_timer()  # get new timeout_timer
        timeout_timer.start()  # restart timeout_timer with different timeout_interval


def request_vote_rpc(node: str):
    global current_term, state, request_vote_rpc_listener_port
    msg = {
        'term': current_term,
        'candidate_id': os.environ['node_id'],
        'last_log_index': -1,  # temp
        'last_log_term': 0,  # temp
    }
    udp_send(target=(node, request_vote_rpc_listener_port), msg=msg)
    print(f'request_vote_rpc - term - {current_term} SENT to {node}')


def vote_acknowledgement_listener(sock: socket.socket):
    print('Starting vote_acknowledgement_listener')
    global state, heartbeat_timer
    positive_votes = 0
    while True:
        msg, addr = sock.recvfrom(1024)
        if kill_threads_flag:
            print('Stopping vote_acknowledgement_listener')
            exit()  # stops this listener
        ack = json.loads(msg.decode('utf-8'))  # decoded msg
        print(f"Received {'YES' if ack['vote'] else 'NO'} vote from {ack['from']}")
        if ack['vote'] == 1:
            positive_votes += 1
        # only elect leader if state is Candidate ( Make sures there is only one Leader at a time )
        # state is changed to Follower in append_entry_rpc_listener
        time.sleep(0.01)  # wait and check if the node is still candidate
        if positive_votes + 1 > len(nodes)//2 and state is State.Candidate:
            timeout_timer.cancel()  # stop the timeout_timer for the leader
            state = State.Leader
            # print('Became Leader')
            positive_votes = 0
            # start sending heartbeats
            heartbeat_timer = threading.Timer(heartbeat_interval / 1000, send_heartbeats)
            heartbeat_timer.start()


def request_vote_rpc_listener(sock: socket.socket):
    print('Starting request_vote_rpc_listener')
    global current_term, voted_for
    while True:
        msg, addr = sock.recvfrom(1024)
        if kill_threads_flag:
            print('Stopping request_vote_rpc_listener')
            exit()  # stops this listener
        candidate = json.loads(msg.decode('utf-8'))  # decoded msg
        print(f"Received vote request from {candidate['candidate_id']} - term - {candidate['term']}")
        vote_sent_flag = False
        if current_term < candidate['term']:
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
    timeout_timer = threading.Timer(timeout_interval/1000, start_election)


def send_heartbeats():
    # print('Sending Heartbeats')
    global current_term, heartbeat_interval, heartbeat_timer
    if kill_threads_flag:
        print('Stopping heartbeats thread')
        exit()  # stops this thread
    if state is not State.Leader:  # stop sending heartbeats once the leader stops being leader
        return
    for node in nodes:
        if node != os.environ['node_id']:
            append_entry_rpc(node, is_heartbeat=True)
    heartbeat_timer = threading.Timer(heartbeat_interval/1000, send_heartbeats)
    heartbeat_timer.start()  # keep sending heartbeats


def controller_rpc_listener(sock: socket.socket):
    global state, kill_threads_flag, timeout_timer
    print('Starting controller_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        if kill_threads_flag:
            print('Stopping controller_rpc_listener')
            exit()  # stops this listener
        controller_request = json.loads(msg.decode('utf-8'))  # decoded msg
        print(f"Controller Request Received - {controller_request['request']}")
        if controller_request['request'] == 'CONVERT_FOLLOWER':
            state = State.Follower
            timeout_timer.cancel()  # stop the timeout_timer
            new_timeout_timer()  # get new timeout_timer
            timeout_timer.start()  # restart timeout_timer with different timeout_interval
        elif controller_request['request'] == 'TIMEOUT':
            timeout_timer.cancel()  # stop the timeout_timer
            start_election()  # immediately start elections
        elif controller_request['request'] == 'SHUTDOWN':
            kill_threads_flag = True
            timeout_timer.cancel()  # stop timeout timer
        elif controller_request['request'] == 'LEADER_INFO':
            if state is state.Leader:  # if current node is leader then send its info
                udp_send(
                    target=(controller_id, controller_port),
                    msg={'LEADER': os.environ['node_id']}
                )
            else:  # ask all others in the cluster to send leader info to Controller, if apply
                for node in nodes:
                    if node != os.environ['node_id']:
                        udp_send(target=(node, msg_rpc_listener_port), msg={'name': 'LEADER_INFO'})


def msg_rpc_listener(sock: socket.socket):
    global state
    print('Starting msg_rpc_listener')
    while True:
        msg, addr = sock.recvfrom(1024)
        if kill_threads_flag:
            print('Stopping msg_rpc_listener')
            exit()  # stops this listener
        msg = json.loads(msg.decode('utf-8'))  # decoded msg
        if msg['name'] == 'LEADER_INFO':
            if state is State.Leader:
                udp_send(
                    target=(controller_id, controller_port),
                    msg={'LEADER': os.environ['node_id']}
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

    # start listeners
    print('Starting Listeners')
    threading.Thread(target=request_vote_rpc_listener, args=[request_vote_rpc_listener_socket]).start()
    threading.Thread(target=vote_acknowledgement_listener, args=[vote_acknowledgement_listener_socket]).start()
    threading.Thread(target=append_entry_rpc_listener, args=[append_entry_rpc_listener_socket]).start()
    threading.Thread(target=msg_rpc_listener, args=[msg_rpc_listener_socket]).start()
    threading.Thread(target=controller_rpc_listener, args=[controller_rpc_listener_socket]).start()

    # sleep for some time to let the listeners start
    time.sleep(1)

    # start timeout_timer
    print('Start timeout_timer')
    new_timeout_timer()
    timeout_timer.start()

    while True:
        print(state, current_term)
        if kill_threads_flag:
            print('Stopping Raft')
            return
        time.sleep(1)
