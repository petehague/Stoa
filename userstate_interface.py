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

def get(uid, key):
    global userstate
    m = userstate.get(userstate_pb2.getRequest(id=uid, key=key))
    return m.value

def set(uid, key, value):
    global userstate
    userstate.set(userstate_pb2.setRequest(id=uid, key=key, value=value))

def check(uid):
    global userstate
    m = userstate.check(userstate_pb2.checkRequest(id=uid))
    return m.value

def append(uid, report):
    global userstate
    userstate.append(userstate_pb2.appendRequest(id=uid, report=report))

def pop(uid):
    global userstate
    m = userstate.pop(userstate_pb2.checkRequest(id=uid))
    return m.value

def tail(uid, n):
    global userstate
    m = userstate.tail(userstate_pb2.tailRequest(id=uid, n=n))
    return m.buff

def list():
    global userstate
    m = userstate.list(userstate_pb2.Empty())
    return m.userlist

def newuser(uname):
    global userstate
    m = userstate.newuser(userstate_pb2.newuserRequest(uname=uname))
    return m.status

userstate.start(userstate_pb2.Empty())
