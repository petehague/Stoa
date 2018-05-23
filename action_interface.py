import grpc
import action_pb2
import action_pb2_grpc
from yml import yamler

config = yamler(open("stoa.yml", "r"))

# Connection to action server and userstate server
if "ActionHost" in config['stoa-info']:
    acthost = config['stoa-info']["ActionHost"].strip()
else:
    acthost = "action"
actConnect = grpc.insecure_channel('{}:7000'.format(acthost))
actions = action_pb2_grpc.ActionStub(actConnect)

def push(usertoken, command, path):
    m = actions.push(action_pb2.pushReq(cmdFile=command,
                                        pathname=path,
                                        usertoken=usertoken))
    return m.mess


def glob(pathname):
    filelist = []
    for item in actions.glob(action_pb2.globReq(pathname=pathname)):
        filelist.append(item.filename)
        print(item.filename)
    return filelist


def isFree(usertoken):
    m = actions.isFree(action_pb2.isFreeReq(usertoken=usertoken))
    return m.result
