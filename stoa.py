#!/usr/bin/env python

import sys
import os

folder = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) < 2:
    os.system(folder+"/pipe.py")
    sys.exit(1)

if 'web' not in sys.argv[1]:
    os.system(folder+"/pipe.py "+" ".join(sys.argv[2:]))
    sys.exit(1)

import time
from astropy.vo.samp import SAMPIntegratedClient
from astropy.table import Table
import websocket
import webbrowser


# Instantiate the client and connect to the hub
client = SAMPIntegratedClient(name="samp-ws bridge")
client.connect()

host = "127.0.0.1"
port = "9000"

if len(sys.argv) > 2:
    host = sys.argv[2]

if len(sys.argv) > 3:
    port = int(sys.argv[3])


# Set up a receiver class
class Receiver(object):
    def __init__(self, client):
        self.client = client
        self.received = False

    def receive_call(self, private_key, sender_id,
                     msg_id, mtype, params, extra):
        self.params = params
        self.sender = sender_id
        self.received = True
        self.client.reply(msg_id, {"samp.status":
                                   "samp.ok",
                                   "samp.result": {}})

    def receive_notification(self, private_key, sender_id,
                             mtype, params, extra):
        self.params = params
        self.sender = sender_id
        self.received = True

    def reset(self):
        self.received = False


# Instantiate the receiver
r = Receiver(client)

# Listen for any instructions to load a table
client.bind_receive_call("table.load.votable", r.receive_call)
client.bind_receive_notification("table.load.votable", r.receive_notification)

# We now run the loop to wait for the message in a try/finally block so that if
# the program is interrupted e.g. by control-C, the client terminates
# gracefully.

print("Starting websocket...")

websocket.enableTrace(True)
ws = websocket.create_connection("ws://{}:{}/ws".format(host, port))

print("Connecting to http://{}".format(host))

webbrowser.open("http://{}:{}".format(host, port))

print("Session started")

while 1:
    # We test every 0.1s to see if the hub has sent a message
    while True:
        time.sleep(0.1)
        if r.received:
            print(r.sender)
            t = Table.read(r.params['url'])
            break
    tabresult = "T"+" ".join(t.pformat(max_lines=1, html=True))
    ws.send(tabresult)
    print("Sent")
    print("Receiving...")
    result = ws.recv()
    print("Received {}".format(result))
    r.reset()

ws.close()


client.disconnect()
