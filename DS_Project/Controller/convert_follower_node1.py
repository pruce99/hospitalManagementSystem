import json
import socket
import traceback
import time
import threading


def msg_rpc_listener(sock: socket.socket):
    print('Starting controller listener')
    while True:
        the_msg, addr = sock.recvfrom(1024)
        response = json.loads(the_msg.decode('utf-8'))  # decoded msg
        print(response)


msg_rpc_listener_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
msg_rpc_listener_socket.bind(('Controller', 5555))
threading.Thread(target=msg_rpc_listener, args=[msg_rpc_listener_socket]).start()


# Wait following seconds below sending the controller request
time.sleep(5)

# Read Message Template
msg = json.load(open("Message.json"))

# Initialize
sender = "Controller"
target = "Node2"
port = 5555

# Request
msg['sender_name'] = sender
msg['request'] = "LEADER_INFO"
print(f"Request Created : {msg}")

# Socket Creation and Binding
skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# skt.bind((sender, port))

# Send Message
try:
    # Encoding and sending the message
    skt.sendto(json.dumps(msg).encode('utf-8'), (target, port))
    pass
except:
    #  socket.gaierror: [Errno -3] would be thrown if target IP container does not exist or exits, write your listener
    print(f"ERROR WHILE SENDING REQUEST ACROSS : {traceback.format_exc()}")

while True:  # to keep the listener alive
    pass
