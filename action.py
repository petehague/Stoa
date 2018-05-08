#!/usr/bin/env python

import cwltool.factory
from yml import yamler, writeyaml
import re
import os
import sys
import glob
from cwltool.errors import WorkflowException

from concurrent import futures
import grpc
import action_pb2
import action_pb2_grpc

import userstate_interface as userstate

config = yamler(open("stoa.yml", "r"))
targetFolder = config['stoa-info']['workspace']

scriptPath = os.path.realpath(__file__)
scriptFolder = "/".join(re.split("/", scriptPath)[:-1]) + "/actions/"


procStack = {}
#for name in userstate.getList():
#    procstack[name] = []


def cwlinvoke(taskfile, params):
    taskfac = cwltool.factory.Factory()
    t = taskfac.make(taskfile)
    result = t(**params)
    return result


def manager(taskfile, paramfile, outfile):
    result = cwlinvoke(taskfile,yamler(open(paramfile,"r")))
    writeyaml(result, outfile)

def ExecCWL(cmdFile, pathname):
    result = {}
    success = 0
    cmdFile = scriptFolder + "/" + cmdFile
    try:
        result = manager(cmdFile, pathname+"/run.yml", pathname+"/.pipelog.txt")
    except WorkflowException as werr:
        success = 1
        log = open(pathname+"/.pipelog.txt","w")
        log.write("Workflow Exception: {}\n".format(werr.args))
        log.close()
    writeyaml(result, pathname+"/stoa_out.yml")
    return success

def makeyml(pathname, command):
    """
    Generates a yml file to guide execution, based on the specific->general hierarchy
    Run specific parameters override batch specific parameters override global parameters

    :param pathname: The path of the project of interest
    """

    cmdyml = (re.split(".cwl", command)[0]).strip() + ".yml"
    cmdDict = yamler(open(scriptFolder+"/"+cmdyml, "r"))
    globalDict = yamler(open(scriptFolder+"/stoa.yml","r"))
    if not os.path.exists("stoa.yml"):
        open("stoa.yml","a").close()
    batchDict = yamler(open("stoa.yml","r"))
    if not os.path.exists(pathname+"/stoa.yml"):
        open(pathname+"/stoa.yml","a").close()
    specDict = yamler(open(pathname+"/stoa.yml","r"))

    for key in cmdDict:
        globalDict[key] = cmdDict[key]
    for key in batchDict:
        globalDict[key] = batchDict[key]
    for key in specDict:
        globalDict[key] = specDict[key]

    writeyaml(globalDict, pathname+"/run.yml")

def clearStack():
    global procStack
    for usertoken in procStack:
        command = procStack[usertoken][0][0]
        pathname = procStack[usertoken][0][1]
        procStack[usertoken].pop(0)
        print(">> "+usertoken+" : "+command+" : "+pathname)
        makeyml(pathname, command)
        print("   Result: "+ExecCWL(command, pathname))

def myGlob(pathname):
    return glob.glob(pathname)

'''
    gRPC class: serves up functions to the clients
'''
class actionServer(action_pb2_grpc.ActionServicer):
    def makeyml(self, request, context):
        makeyml(request.pathname, request.command)
        return action_pb2.makeymlReply(mess="OK")

    def ExecCWL(self, request, context):
        print(request.cmdFile)
        return action_pb2.ExecCWLReply(result=ExecCWL(request.cmdFile, request.pathname))

    def push(self, request, context):
        if request.usertoken not in procStack:
            procStack[request.usertoken] = []
        procStack[request.usertoken].append([request.cmdFile, request.pathname])
        return action_pb2.pushReply(mess="OK")

    def isFree(self, request, context):
        if request.usertoken not in procStack:
            procStack[request.usertoken] = []
        if procStack[request.usertoken]==[]:
            return action_pb2.isFreeReply(result=True)
        else:
            return action_pb2.isFreeReply(result=False)

    def glob(self, request, context):
        print(request.pathname)
        list = myGlob(request.pathname)
        for filename in list:
            yield action_pb2.globReply(filename=filename)

if __name__ == "__main__":
    serverinst = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    action_pb2_grpc.add_ActionServicer_to_server(actionServer(), serverinst)
    portnum = serverinst.add_insecure_port('[::]:7000')
    serverinst.start()
    print("Action server started on port {}".format(portnum))
    try:
        while True:
            clearStack()
            sys.stdout.flush()
    except KeyboardInterrupt:
        serverinst.stop(0)
