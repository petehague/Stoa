#!/usr/bin/env python

import cwltool.factory
from yml import yamler, writeyaml
import re
import os
import sys
import time
import glob
from cwltool.errors import WorkflowException

from worktable import Worktable

from concurrent import futures
import grpc
import action_pb2
import action_pb2_grpc

import userstate_interface as userstate

config = yamler(open("stoa.yml", "r"))
targetFolder = config['stoa-info']['workspace']

scriptPath = os.path.realpath(__file__)
coreFolder = os.path.split(scriptPath)[0]
scriptFolder = coreFolder+os.sep+"actions"

os.environ['PATH'] += ":"+scriptFolder

lockStack = 0 

procStack = {}
#for name in userstate.getList():
#    procstack[name] = []

def ymlvars(ymlfile, output, pathname):
    f1 = open(ymlfile,"r")
    f2 = open(output,"w")
    for line in f1:
        result = line.replace("<path>", pathname)
        f2.write(result)
    f1.close()
    f2.close()

def cwlinvoke(pathname, taskfile, params):
    fallback = os.getcwd()
    os.chdir(pathname) # This is probably a bug in cwltool, that it can only use cwd as basedir
    taskfac = cwltool.factory.Factory()
    t = taskfac.make(taskfile)
    params["outdir"] = "/home/prh44/Stoa/"+pathname
    result = t(**params)
    os.chdir(fallback)
    return result

def parsecwloutput(pathname, result):
    outlist = []
    for output in result:
        if result[output]['class']=='File':
            outlist.append(pathname+"/"+result[output]['basename'])
    return outlist

def ExecCWL(cmdFile, pathname):
    result = {}
    success = 0
    if ".wtx" in cmdFile:
       wt = Worktable(cmdFile)
       wtFile = cmdFile
       cmdFile = "workflow.cwl"
       wt.unpack(pathname)
    else:
       wt = False
       cmdFile = scriptFolder + "/" + cmdFile
    try:
        result = cwlinvoke(pathname, cmdFile,
                           yamler(open(pathname+"/run.yml", "r"), convert=True))
        writeyaml(result, pathname+"/.pipelog.txt")
    except WorkflowException as werr:
        success = 1
        log = open(pathname+"/.pipelog.txt","a")
        log.write("Workflow Exception: {}\n".format(werr.args))
        log.close()
    if wt:
        index = wt.byref(pathname)
        wt.update(index,parsecwloutput(pathname, result))
        wt.save(wtFile)
                
    return success

def makeyml(pathname, command):
    """
    Generates a yml file to guide execution, based on the specific->general hierarchy
    Run specific parameters override batch specific parameters override global parameters

    :param pathname: The path of the project of interest
    """

    if ".wtx" in command:
        wt = Worktable(command)
        cmdDict = wt.template
    else:
        cmdyml = (re.split(".cwl", command)[0]).strip() + ".yml"
        cmdDict = yamler(open(scriptFolder+"/"+cmdyml, "r"))
    globalDict = yamler(open(coreFolder+"/stoa.yml","r"))
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

    writeyaml(globalDict, pathname+"/runraw.yml")
    ymlvars(pathname+"/runraw.yml", pathname+"/run.yml", coreFolder+"/"+pathname)

def clearStack():
    global procStack
    lockStack = 1
    for usertoken in procStack:
        if len(procStack[usertoken])>0:
            command = procStack[usertoken][0][0]
            pathname = procStack[usertoken][0][1]
            procStack[usertoken].pop(0)
            print(">> "+usertoken+" : "+command+" : "+pathname)
            #userstate.append(usertoken, pathname)
            makeyml(pathname, command)
            result = ExecCWL(command, pathname)
            print("   Result: {}".format(result))
            if result>0:
               userstate.append(usertoken, '{}  <span class="bold"><span class="red">FAILED</span></span>'.format(pathname))
            else:
               userstate.append(usertoken, '{}  <span class="bold"><span class="green">OK</span></span>'.format(pathname))
    lockStack = 0

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
        while lockStack>0:
          time.sleep(0.1)
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
            time.sleep(1)
            sys.stdout.flush()
    except KeyboardInterrupt:
        serverinst.stop(0)
