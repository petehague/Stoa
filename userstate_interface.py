import grpc
import userstate_pb2
import userstate_pb2_grpc
from yml import yamler

config = yamler(open("stoa.yml", "r"))
if "UserstateHost" in config['stoa-info']:
    userstatehost = config['stoa-info']['UserstateHost'].strip()
else:
    userstatehost = "userstate"
userstateConnect = grpc.insecure_channel('{}:6999'.format(userstatehost))
userstate = userstate_pb2_grpc.UserstateStub(userstateConnect)

def get(id, key):
    global userstate
    m = userstate.get(userstate_pb2.getRequest(id=id, key=key))
    return m.value

def set(id, key, value):
    global userstate
    userstate.set(userstate_pb2.setRequest(id=id, key=key, value=value))

def check(id):
    global userstate
    m = userstate.check(userstate_pb2.checkRequest(id=id))
    return m.value

userstate.start(userstate_pb2.Empty())
