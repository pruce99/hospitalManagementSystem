import json
import socket
import time
import threading


def send_msg():
    skt.sendto(json.dumps(msg).encode('utf-8'), (target, port))


def msg_rpc_listener(sock: socket.socket):
    print('Starting controller listener')
    while True:
        the_msg, addr = sock.recvfrom(1024)
        response = json.loads(the_msg.decode('utf-8'))  # decoded msg
        print(response)
        try:
            if response['key'] == 'LEADER':
                global target
                target = response['value']
                send_msg()
        except KeyError:
            pass


msg_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
msg_rpc_listener_socket.bind(('Controller', 5555))
threading.Thread(target=msg_rpc_listener, args=[msg_rpc_listener_socket]).start()


# Wait following seconds below sending the controller request
time.sleep(5)

# Read Message Template
msg = json.load(open("Message.json"))

# Initialize
sender = "Controller"
port = 5555
skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

target = 'Node2'
# Request
msg['sender_name'] = sender
msg['request'] = "STORE"
msg['key'] = 'store_patient_madara'
msg['value'] = {
    'first_name': 'madara',
    'last_name': 'uchiha',
    'age': '110',
    'gender': 'Male',
    'phone_number': '+1 1234567890',
    'email': 'madara_uchiha@clan.com',
    'department': 'Cardiology',
}
print(f"Request Created")
send_msg()

time.sleep(.5)

target = 'Node3'
msg['request'] = 'SHUTDOWN'
send_msg()

time.sleep(.5)

target = 'Node2'
msg['sender_name'] = sender
msg['request'] = "STORE"
msg['key'] = 'store_patient_sasuke'
msg['value'] = {
    'first_name': 'sasuke',
    'last_name': 'uchiha',
    'age': '110',
    'gender': 'Male',
    'phone_number': '+1 1234567890',
    'email': 'sasuke_uchiha@clan.com',
    'department': 'Cardiology',
}
print(f"Request Created")
send_msg()

time.sleep(.5)

target = 'Node2'
msg['sender_name'] = sender
msg['request'] = "STORE"
msg['key'] = 'store_patient_itachi'
msg['value'] = {
    'first_name': 'itachi',
    'last_name': 'uchiha',
    'age': '110',
    'gender': 'Male',
    'phone_number': '+1 1234567890',
    'email': 'itachi_uchiha@clan.com',
    'department': 'Cardiology',
}
print(f"Request Created")
send_msg()

time.sleep(.5)

msg['request'] = "RETRIEVE"
send_msg()

# target = 'Node3'
# msg['request'] = "CONVERT_FOLLOWER"
# send_msg()

while True:  # to keep the listener alive
    pass
