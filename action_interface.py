import grpc
import action_pb2
import action_pb2_grpc
from yml import yamler

acthost = "localhost"
actConnect = grpc.insecure_channel('{}:7000'.format(acthost))
actions = action_pb2_grpc.ActionStub(actConnect)

def push(usertoken, command, path, bindex):
    m = actions.push(action_pb2.pushReq(cmdFile=command,
                                        pathname=path,
                                        usertoken=usertoken,
                                        bindex=bindex))
    return m.mess


def glob(pathname):
    filelist = []
    for item in actions.glob(action_pb2.globReq(pathname=pathname)):
        filelist.append(item.filename)
        print(item.filename)
    return filelist


def isProc(usertoken, bindex):
    m = actions.isProc(action_pb2.isProcReq(usertoken=usertoken, bindex=bindex))
    return m.result

def isFree(usertoken):
    m = actions.isFree(action_pb2.isFreeReq(usertoken=usertoken))
    return m.result
