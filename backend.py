
import tornado.websocket
import re
import os
import sys
import glob
import pipe
import xml.etree.ElementTree as et
import userstate
import sqlite3 as sql
from astropy.time import Time
import time
from yml import yamler
from imp import load_source
from fnmatch import fnmatch
from astropy.table import Table
import numpy as np

from worktable import Worktable, getnetwork, prune

import userstate_interface as userstate
import action_interface as action

profiles = []

started = False

targetFolder = ""
currentFolder = {}
userspace = {}
session = {}
runStatus = "Nothing"

pathslist = ["pathname", "foldername", "image"] #TODO this needs to be done via metadata!

tasklist = {}

siteroot = "http://127.0.0.1:8888"
scriptPath = os.path.realpath(__file__)
webPath = os.path.split(scriptPath)[0] + "/"

config = yamler(open("stoa.yml", "r"))
projectname = config['stoa-info']['project-name']

handlerpath = config['stoa-info']['filehandler']['script']
handlerpattern = config['stoa-info']['filehandler']['pattern']
handler_name, fext = os.path.splitext(os.path.split(handlerpath)[-1])
filehandler = load_source(handler_name,handlerpath)

reftables = {}
if 'reftable' in config['stoa-info']:
    reftables[config['stoa-info']['reftable']['name']]=config['stoa-info']['reftable']['coords']

obsfile = "" #TODO: Link this value to config file

stopCommand = "<a href=\"javascript:getPath('r')\">Click here to stop batch</a>"

consoleSize = 20

def htmlify(tab, collist=[]):
    result = "<table><tr>"
    colmask = []
    for column in tab.colnames:
        if column in collist or len(collist)==0:
            result += "<th>{}</th>".format(column)
            colmask.append(1)
        else:
            colmask.append(0)
    result += "</tr>"
    for row in tab:
        result += "<tr>"
        colindex = 0
        for datum in row:
            if colmask[colindex]==1:
                if type(datum) is bytes:
                   datum = datum.decode('utf-8')
                result += "<td>{}</td>".format(datum)
            colindex += 1
        result += "</tr>"
    result += "</table>"
    return result

# TODO see if this can be removed
def startBackend():
    """
    Initialises the web database (distinct from the pipeline one) and
    loads in user table

    :return: None
    """
    global started
    if started:
        return
    started = True
    print("Backend started")

def svgbar(filename, n, arrow=False):
    lw = 6
    height = 120
    mid = height/2
    os.system("cp ui/smallheader.svg "+filename) 

    cols = ["red", "green", "blue", "orange"]
    cols = ["#777777"]*10    
    svg = open(filename, "a")
    if arrow:
        svg.write('<polygon points="10,{1} 25,{2} 10,{3}" style="fill:{0}; stroke:{0}" />'.format(cols[n],mid-lw,mid,mid+lw))
        svg.write('<rect x="0" y="{1}" width="10" height="{2}" style="fill:{0}; stroke:{0}" />'.format(cols[n],mid-lw/2, lw))
    else:
        svg.write('<rect x="0" y="{1}" width="25" height="{2}" style="fill:{0}; stroke:{0}" />'.format(cols[n],mid-lw/2, lw))
    svg.write('</svg>')
    svg.close()

def svgline(filename, n, lmap):
    width,height = 75,120
    lw = 6
    os.system("cp ui/header.svg "+filename)

    yoffset = n*height
    svg = open(filename, "a")
    cols = ["red", "green", "blue", "orange"]
    cols = ["#777777"]*10    
    svg = open(filename, "a")
    for start in range(len(lmap)):
        for finish in lmap[start]:
            svg.write('<polygon points="')
            a = (height-lw)/2+start*height
            b = (height-lw)/2+finish*height
            if a==b:
                thiccor = 0
            else:
                angle = np.fabs(np.arctan2(b,a))
                thiccor = lw*np.sin(angle)
            if b>a:
              svg.write('0,{2} {0},{2} {6},{3} {6},{4} {1},{4} 0,{5}'.format(thiccor,
                                                                             width-thiccor,
                                                                             a-yoffset, 
                                                                             b-yoffset, 
                                                                             lw+b-yoffset, 
                                                                             lw+a-yoffset,
                                                                             width))
            else:
              svg.write('0,{2} {1},{3} {6},{3} {6},{4} {0},{5} 0,{5}'.format(thiccor,
                                                                             width-thiccor,
                                                                             a-yoffset, 
                                                                             b-yoffset, 
                                                                             lw+b-yoffset, 
                                                                             lw+a-yoffset,
                                                                             width))
            svg.write('" style="fill:{0}; stroke:{0}" />'.format(cols[start]))
  
    svg.write("</svg>")
    svg.close()


def projectInfo(userFolder):
    """
    Produces the main page containing information about the current project

    :return: HTML output
    """
    outstring = '<h2>{}</h2>'.format(projectname)

    if userFolder=="user_admin":
        outstring += '<h3>Users:</h3><p class="data">'
        usernames = re.split(",", userstate.list())
        for uname in usernames:
            outstring += '&nbsp;-&nbsp;{}<br />'.format(uname)
        outstring += '</p>'
        outstring += '<p><a href="javascript:getPath(\'N\')">Create New User</a></p>'
        return outstring

    outstring += '<p><a href="javascript:getPath(\'C\')">Create new worktable</a><br />'
    outstring += '<a href="javascript:getPath(\'S\')">Create new service</a><br />'
    outstring += '<a href="javascript:getPath(\'U\')">Browse user files</a></p>'

    wtmap, parents, children = getnetwork(glob.glob(os.path.join(targetFolder, userFolder, "*.wtx")))
    for servfile in glob.glob(os.path.join(targetFolder, userFolder, "*.service")):
        servfilename = os.path.split(servfile)[1]
        children[servfilename] = []
        with open(servfile, "r") as s:
            ssource = s.readline().strip()
        parents[servfilename] = [ssource]
        children[ssource].append(servfilename)
        for i,column in enumerate(wtmap):
            if ssource in column:
                if i==len(wtmap)-1:
                    wtmap.append([])
                wtmap[i+1].append(servfilename)
    fixwidth = len(wtmap)*130 + (len(wtmap)-1)*125
    outstring += '<p><table class="wttab" width="{0}px"><tbody style="width: {0}px !important; display: table;">'.format(fixwidth)

    nrows = 0
    irn = np.random.randint(9999)
    for n in range(len(wtmap)):
        nrows = max(len(wtmap[n]), nrows)
    for r in range(nrows):
        cells = ""
        for c in range(len(wtmap)):
            if len(wtmap[c])>r:
                if c>0:
                   for i in range(len(wtmap[c-1])):
                       if wtmap[c-1][i] in parents[wtmap[c][r]]:
                          break
                   arrowfile_list = glob.glob(os.path.join(targetFolder, userFolder,"log/linkarrow_{}_{}*.svg".format(c,i)))
                   if not arrowfile_list:
                     arrowfile = os.path.join(targetFolder,userFolder,"log/linkarrow_{}_{}_{}.svg".format(c,i,irn))                
                     svgbar(arrowfile, i, arrow=True)
                   else:
                     arrowfile = arrowfile_list[0]
                   linkbar = '<img width="25" src="/file/{}" />'.format(arrowfile)
                   cells += '<td class="spacecell">{}</td>'.format(linkbar)
                wtfile = wtmap[c][r]
                wtpath = os.path.join(targetFolder, userFolder, wtfile)
                cells += '<td class="wtcell">'
                command = 't' if '.wtx' in wtpath else 's'
                cells += '<a href="javascript:getPath(\'{}{}\')">'.format(command, wtpath)
                if ".service" in wtfile:
                    icon = "service"
                    wtfile = wtfile[:-8]
                else:
                    icon = "page"
                    wtfile = wtfile[:-4]
                cells += '<img class="wtimage" width="50px" height="50px" src="static/{}.svg" />'.format(icon)
                cells += '<p class="wttext">{}</p>'.format(wtfile)
                cells += '</a></td>'        
            else:
                if c>0:
                    cells += '<td class="spacecell">&nbsp;</td>'
                cells += '<td class="wtcell">&nbsp;</td>'
            if c<(len(wtmap)-1):
                barfile_list = glob.glob(os.path.join(targetFolder,userFolder,"log/linkbar_{}_{}*.svg".format(c,r)))
                if not barfile_list:
                  barfile = os.path.join(targetFolder,userFolder,"log/linkbar_{}_{}_{}.svg".format(c,r,irn))
                  svgbar(barfile, r)
                else:
                  barfile = barfile_list[0]
                linkbar = '<img class="lineel" src="/file/{}" />'.format(barfile)
                if len(wtmap[c])>r:
                    if len(children[wtmap[c][r]])==0:
                        linkbar = '&nbsp;'
                cells += '<td class="spacecell">{}</td>'.format(linkbar if len(wtmap[c])>r else '')
                svgfilename_list = glob.glob(os.path.join(targetFolder,userFolder,"log/line_{}_{}*.svg".format(c,r)))
                if not svgfilename_list: 
                  svgfilename = os.path.join(targetFolder,userFolder,"log/line_{}_{}_{}.svg".format(c,r,irn))
                  lmap = []
                  for parent in wtmap[c]:
                    lmaplist = []
                    index = 0
                    for child in wtmap[c+1]:
                      if child in children[parent]:
                        lmaplist.append(index) 
                      index += 1
                    lmap.append(lmaplist)
                  svgline(svgfilename, r, lmap)
                else:
                  svgfilename = svgfilename_list[0]
                linkline = '<img class="lineel" src="/file/{}" />'.format(svgfilename)
                cells += '<td class="linecell">{}</td>'.format(linkline)
        outstring += '<tr style="width: {}px !important;">'.format(fixwidth)+cells+'</tr>'
        #print(cells+"\n\n")
    outstring += '</tbody></table></p>'
    return outstring

def setTarget(t):
    """
    Sets the target folder

    :param t: The name of the new target folder
    :return: None
    """
    global targetFolder
    if t[-1] != '/':
        t += '/'
    targetFolder = t
    pipe.setProctabPath(t)


def current(userip):
    """
    Get the current folder being viewed by a user

    :param userip: The IP address of the user (currently used as ID)
    :return: The name of the folder
    """
    return userspace[session[userip]].folder


def setCurrent(userip, foldername):
    """
    Sets the current folder being viewed by a user

    :param userip: The IP address of the user (currently used as ID)
    :param foldername: The name of the folder
    :return: None
    """
    userspace[session[userip]].folder = foldername

def userlogin(userip, username):
    session[userip] = username


def usernamecheck(user):
    return userstate.check(user)

def usercheck(userip):
    """
    Check if the user is valid

    :param userip: The IP address of the user (currently used as ID)
    :return: A session ID, or "False" if there is no such user
    """
    if userip in session:
        return userstate.check(session[userip])
    else:
        return False


def getwsroot(userip):
    """
    Get the address this user has to send ws connections to

    :param userip: The IP address of the user (currently used as ID)
    :return: A URL
    """
    if userip in session:
        return userstate.get(session[userip], "wsroot")
    else:
        return False

def makeFlagList():
    """
    Calls the pipeline to get a list of the flagged paths

    :return: List of paths
    """
    return pipe.doRun("none")
    # Add a caching system later


def xmlListing(path):
    """
    Parses XML files stored in target folders

    :param path: The path name of the folder containing the .xml file
    :return: List of subpaths (i.e. observations) defined in the file
    """
    tree = et.parse(path+"product.xml")
    nodes = tree.getroot()
    listing = []
    for node in nodes[0]:
        listing.append(path+node.attrib['key'])
    return listing

class ConeSearchHandler(tornado.web.RequestHandler):
    def get(self, *args):
        servicepath = re.split("/",args[0]) 
        getargs = self.request.arguments
        if all (k in getargs for k in ("RA","DEC","SR")):
            ra,dec,sr = float(getargs["RA"][0].decode()), float(getargs["DEC"][0].decode()), float(getargs["SR"][0].decode())
        else:
            self.write("Couldn't retrieve conesearch parameters")
            return
        if not userstate.check(servicepath[0]):
            self.write("No such user")
            return
        print("Conesearch request for {} at {},{} r={}".format(servicepath, ra, dec, sr))
        userFolder = "user_"+servicepath[0]
        csfile = servicepath[1]+".service"
        with open(os.path.join(targetFolder, userFolder, csfile), "r") as sfile:
            wtfile = sfile.readline().strip()
            rafield = sfile.readline().strip()
            decfield = sfile.readline().strip()
        wt = Worktable(os.path.join(targetFolder, userFolder, wtfile))
        self.write(wt.conesearch(rafield, decfield, ra, dec, sr, siteroot))
                       

class FitsHandler(tornado.web.RequestHandler):
    def get(self, *args):
        servicepath = re.split("/",args[0])
        if not userstate.check(servicepath[0]):
            self.write("No such user")
            return
        userFolder = "user_"+servicepath[0]
        csfile = servicepath[1]+".service"
        with open(os.path.join(targetFolder, userFolder, csfile), "r") as sfile:
            wtfile = sfile.readline().strip()
        wt = Worktable(os.path.join(targetFolder, userFolder, wtfile))
        self.write(wt.fitsout())


class SocketHandler(tornado.websocket.WebSocketHandler):
    """
    Handler for WebSocket connections
    """
    users = set()
    # reqorigin = ""
    userip = ""

    def check_origin(self, origin):
        """
        To be implemented for security checks

        :param origin: Page originating WS request
        :return: Always "True" at the moment
        """
        return True

    def open(self):
        """
        Opens WebSocket

        :return: None
        """
        print("WebSocket opened")
        SocketHandler.users.add(self)

    def on_message(self, message):
        """
        Responds to WS messages. Action is determined by first character
        of message

        * H: Home
        * F: Flag target
        * U: Unflag target
        * A/a: Get action list
        * P: Run a worktable
        * p: Run one row of a worktable
        * R/f: Run the specified action
        * r: Terminate an action
        * D: Display a file
        * C: Create new worktable
        * z: Clear contents of a worktable
        * k: Delete a worktable
        * t: Display a worktable
        * &: Append to a worktable
        * s: Display a service
        * X: Logout

        :param message: WS message string
        :return: None
        """
        global currentFolder, userspace, pathslist

        userip = self.request.remote_ip

        tokens = re.split(",", message[1:])
        user = self.get_secure_cookie("stoa-user").decode('utf8')
        session[userip] = user
        tasklist[session[userip]] = []
        if not userstate.check(user):
            self.clear_cookie("stoa-user")
            print("Bad user cookie")
            return

        if userip in session:
            user = session[userip]
            currentFolder = userstate.get(user, "folder")
            userstate.set(user, "ip", userip)
        else:
            self.write_message('<script  type="text/javascript">window.location="/login"</script>')
            return

        sys.stdout.flush()

        userFolder = "user_"+user
        if not os.path.exists(os.path.join(targetFolder,userFolder)):
            os.system("mkdir {}".format(os.path.join(targetFolder,userFolder)))

        if message[0] == '.':
            if message[1] == '1':
                return
            if message[1] == '2':
                taskreport = ""
                update = userstate.pop(session[userip])
                if update!="":
                    print("UD "+update)
                    for item in tasklist[session[userip]]:
                        if item[1] in update:
                            item[2] = " ".join(re.split(" ", update)[1:])
                        taskreport += "{}: {}   {}<br />".format(item[0], item[1], item[2])
                    self.write_message(":"+taskreport)
                    self.write_message("t10")
                return

        print(time.strftime('[%x %X]')+" "+user+"("+userip+"): "+message)

        if message[0] == 'H':
            self.write_message(projectInfo(userFolder))

        #Display the action list
        if message[0] == 'A' or message[0] == 'a':
            if message[0] == 'a':
                flagToggle = "<p><a href=\"javascript:getPath('A')\">Run all</a><br />Run flagged</p>"
                runtype = 'f'
            else:
                flagToggle = "<p>Run all<br /><a href=\"javascript:getPath('a')\">Run flagged</a></p>"
                runtype = 'R'
            commandtext = ""
            commandlist = pipe.doActlist("")
            #if not action.isFree(session[userip]):
            #    commandtext += "<p>There is currently an action in progress<br />"+stopCommand+"</p>"
            monitor = "<div id=monitor></div>"
            for command in commandlist:
                commandtext += '<a href="javascript:getPath(\'{0}{1}\')">\
                                {1}</a><br />'.format(runtype,command.strip())
            self.write_message("#"+monitor+flagToggle+commandtext)
            self.write_message("+<div id='conback'><p class='console'></p></div>")

        if message[0] == 'P':
            wtfile = message[1:].strip()
            wt = Worktable(wtfile)
            wt.clearall() #TODO: Slightly less nuclear solution to this problem
            wt.save(wtfile)
            lastbindex = -1
            for row in wt:
                if row[0] != lastbindex:
                    rowfolder = row[1]
                    action.push(session[userip],wtfile,str(rowfolder),row[0])
                lastbindex = row[0]

        if message[0] == 'p':
            content = message[1:].strip()
            tokens = re.split(":",content)
            command = tokens[0]
            path = tokens[1]
            bindex = tokens[2]
            print(command, path)
            action.push(session[userip],command,path,int(bindex))

        #Run an action
        if message[0] == 'R' or message[0] == 'f':
            #monitor = "<div id=monitor></div>"
            #self.write_message("#"+monitor+"Processing command "+message[1:]+"...<br />"+stopCommand)
            command = message[1:].strip()
            tasklist[session[userip]] = []
            for path in pipe.commandgen(command, targetFolder, noproc=True):
                action.push(session[userip],command, path)
                tasklist[session[userip]].append([command, path, '<span class="yellow">Working</span>'])

        #Terminate an action
        if message[0] == 'r':
            # userspace[user].proc.terminate()
            self.write_message("#Action terminated<br />"+stopCommand)

        #Display a fits image
        if message[0] == 'D':
            fileReq = message[1:]
            if fnmatch(fileReq,handlerpattern):
                self.write_message("+Loading image...")
                self.write_message(filehandler.stoa(targetFolder+fileReq))

        if message[0] == 'C':
            makescreen = '<h2 style="width: 500px;">Create New Worktable</h2>'
            if len(message)>1:
                tokens = re.split(":", message[1:])
                wtname = os.path.split(tokens[0])[1] 
                wtname = re.split(".cwl", wtname)[0] + ".wtx"
                newwt = Worktable()
                newwt.lastfilename = wtname # TODO: Better workaround
                newwt.addfile(tokens[0]) # CWL file
                newwt.addfile(tokens[1]) # YML file
                newwt.genfields(path=False) 
                if len(tokens)>2:
                    oldwt = Worktable(tokens[2])
                    newwt.keyoff(oldwt, tokens[3:])
                newwt.save(os.path.join(targetFolder, userFolder, wtname))
                os.system("rm -f "+os.path.join(targetFolder, userFolder,"log","*.svg"))
                self.write_message("rt"+os.path.join(targetFolder, userFolder, os.path.join(targetFolder, userFolder, wtname)))
            else:
                makescreen += '<div width="1000px">&nbsp;</div><form class="mainform" action="javascript:newWorktable()">'
                makescreen += 'CWL File<input class="absinp" list="cwlglob" id="cwlfile" /><br /><br />'
                makescreen += '<datalist id="cwlglob">'
                for filename in glob.glob(os.path.join(targetFolder,userFolder,"*.cwl")):
                    makescreen += '<option value="{}" />'.format(filename)
                makescreen += '</datalist>'
                makescreen += 'YML File<input class="absinp" list="ymlglob" id="ymlfile" /><br /><br />' 
                makescreen += '<datalist id="ymlglob">'
                for filename in glob.glob(os.path.join(targetFolder,userFolder,"*.yml")):
                    makescreen += '<option value="{}" />'.format(filename)
                makescreen += '</datalist>'
                makescreen += '<input type="checkbox" id="keyoff" value="Keyoff" onclick="toggleOptionArea()" />Key from other table<br /><br />'
                makescreen += '<input type="submit" value="Create" /></p>'

                makescreen += '<div id="optionarea" style="visibility: hidden;">Parent table<input class="absinp" list="wtxglob" id="wtxfile" onchange="getFieldList()"/><br /><br />'
                makescreen += '<datalist id="wtxglob">'
                for filename in glob.glob(os.path.join(targetFolder,userFolder,"*.wtx")):
                    makescreen += '<option value="{}" />'.format(filename)
                makescreen += '</datalist>'
                makescreen += 'Field names: <div id="fieldfield"></div><br />'
                makescreen += 'Key fields <input class="absinp" type="text" id="keyfields" /><br /><br />(seperate with :)'
                makescreen += '</div></form>'
            self.write_message(makescreen)

        if message[0] == 'F':
            wt = Worktable(message[1:])
            flist = ""
            for field in wt.fieldnames[1:]:
                flist += '<a href="javascript:setField(\'{0}\')">{0}</a>&nbsp;'.format(field)
            self.write_message("f"+flist)

        if message[0] == 'S':
            makescreen = '<h2 style="width: 500px;">Create New Service</h2>'
            if len(message)>1:
                tokens = re.split(":", message[1:])
                name = tokens[0]
                wtname = os.path.split(tokens[1])[1]
                rafield = tokens[2]
                decfield = tokens[3]
                with open(os.path.join(targetFolder, userFolder, name+".service"),"w") as servicefile:
                    servicefile.write(wtname+"\n")
                    servicefile.write(rafield+"\n")
                    servicefile.write(decfield+"\n")
                self.write_message("rs"+os.path.join(targetFolder, userFolder, name+".service"))
                os.system("rm -f "+os.path.join(targetFolder, userFolder,"log","*.svg"))
                return
            else:
                makescreen += '<p><form class="mainform" action="javascript:newService()">'
                makescreen += 'Name<input class="absinp" type="text" id="servicename" /><br /><br />'
                makescreen += 'Worktable<input class="absinp" list="wtxglob" id="wtxfile" onchange="getFieldList()"/><br /><br />'
                makescreen += '<datalist id="wtxglob">'
                for filename in glob.glob(os.path.join(targetFolder,userFolder,"*.wtx")):
                    makescreen += '<option value="{}" />'.format(filename)
                makescreen += '</datalist>'
                makescreen += 'Field names: <div id="fieldfield"></div><br />'
                makescreen += 'RA:Dec fields <input class="absinp" type="text" id="keyfields" /><br /><br />'
                makescreen += '<input type="submit" value="Create" /></form></p>'
            self.write_message(makescreen)

        if message[0] == 'U':
            filelist = '<h2 style="width: 500px">Files in {}</h2><br />'.format(userFolder)
            for item in glob.glob(os.path.join(targetFolder, userFolder, "*")):
                filelist += '<a href="file/{0}/{1}">{1}</a><br />'.format(userFolder, os.path.split(item)[1])
            filelist += '<div style="position:fixed;top: 150px;left:800px"><form class="mainform">'
            filelist += '<h3>Upload a File</h3><br /><input type="file">'
            filelist += '</form></div>'
            self.write_message(filelist)
        

        if message[0] == 'z':
            wt = Worktable(message[1:])
            wt.clearall()
            wt.save(message[1:])
  
        if message[0] == 'k':
            os.system("rm -f "+os.path.join(targetFolder, userFolder,"log","*.svg"))
            if ".service" in message:
                os.remove(message[1:])
                self.write_message("rH")
                return
            wt = Worktable(message[1:])
            parents = wt.parenttables
            children = wt.childtables
            for p in parents:
                pwt = Worktable(os.path.join(targetFolder,p))
                if p in wt.childtables:
                    wt.childtables.remove(message[1:])
                pwt.save(os.path.join(targetFolder,p))
            for c in children:
                cwt = Worktable(os.path.join(targetFolder,c))
                if c in wt.parenttables:
                    wt.parenttables.remove(message[1:])
                cwt.save(os.path.join(targetFolder,c))
            os.remove(message[1:])     
            self.write_message('rH')

        #Display a results table
        if message[0] == 't':
            wtname = message[1:]
            try: # TODO Deal with the file lock - transfer to database when live
                wt = Worktable(wtname)
            except: 
                return
            monitor = "<div id='monitor' style='visibility: hidden'>"+wtname+"</div>"
            tab = '<p><h2>Worktable: {0}</h2><br /><a href="javascript:getPath(\'P{1}\')">Run Entire Table</a><br /><br /><a href="javascript:getPath(\'z{1}\')">Clear output</a><br /><a href="javascript:getPath(\'k{1}\')">Delete Table</a></p><p><table id = "Worktable"><tr><th></th>'.format(os.path.split(wtname)[1], wtname)
            for fname in wt.fieldnames[1:]:
                tab += "<th>{}</th>".format(fname)
            tab += "</tr><tr><th></th>"
            for ftype in wt.fieldtypes[1:]:
                tab += "<th>{}</th>".format(ftype)
            tab += "</tr><tr><th>UCD</th>"
            for i, fucd in enumerate(wt.fielducd[1:]):
                print(i,fucd)
                sys.stdout.flush()
                tab += '<th><input type="text" class="ucdrow" id="newucd{}" /></th>'.format(i)
            tab += '</tr><tr><td colspan="{}"></td></tr>'.format(len(wt.fieldtypes))
            alternator = 0
            lastbindex = -1
            for row in wt:
                bindex = row[0]
                rowfolder = row[1]
                if bindex==lastbindex:
                    tab += '<tr class="row{}"><th>&nbsp;</th>'.format(alternator)
                else:
                    tab +='<tr class="row{}"><th><a href="javascript:getPath(\'p{}:{}:{}\')">run</a></th>'.format(alternator, wtname, rowfolder, bindex)
                alternator = 1-alternator
                colid = 1
                for col in row[1:]:
                    coltext = str(col)
                    ishtml = False
                    if ".txt" in coltext:
                        coltext = '<a href="javascript:getPath(\'Y{0}\')">{0}</a>'.format(coltext)
                        ishtml = True
                    if ".png" in coltext:
                        coltext = '<img height="150px" src="/file/{}" />'.format(os.path.relpath(coltext, targetFolder))
                        ishtml = True
                    if bindex==lastbindex and "I_" in wt.fieldtypes[colid]:
                        tab += "<td>&nbsp;</td>"
                    else:
                        fulltext = coltext #TODO add a nice Javascript tooltip
                        if not ishtml and len(coltext)>50:
                            coltext = coltext[0:13]+"...."+coltext[-33:]
                        tab+="<td>{}</td>".format(coltext)
                    colid += 1
                tab += "</tr>"
                lastbindex = bindex
            tab+='<tr><td><a href="javascript:addRow(\'{}\')">+</a></td>'.format(wtname)
            index = 1
            for ftype in wt.fieldtypes[1:]:
                if "I" in ftype:
                    tab += '<td><input type="text" class="newrow" id="{}" /></td>'.format("new"+wt.fieldnames[index])
                else:
                    tab += '<td>&nbsp;</td>'
                index += 1
            tab += "</table></p>"
            self.write_message(monitor+tab)

        if message[0] == "&":
            tokens = re.split(":",message[1:])
            wt = Worktable(tokens[0])
            wt.addrow(tokens[1:])
            wt.save(tokens[0])
            self.write_message('<script  type="text/javascript">getPath(\'t{}\')</script>'.format(tokens[0]))

        #Display information for a service
        if message[0] == 's':
            servpath = message[1:]
            with open(servpath, "r") as sfile:
                tablename = sfile.readline()
                rafield = sfile.readline()
                decfield = sfile.readline()
            servname = re.split("\.",os.path.split(servpath)[1])[0]
            result = "<h2>{}</h2>".format(servname)
            result += '<a href="javascript:getPath(\'k{}\')">Delete Service</a><br />'.format(servpath)
            result += "<p>Uses worktable {}, with RA={} and Dec={}</p>".format(tablename, rafield, decfield)
            result += '<p>FITS file download: <a href="{0}/fits/{1}/{2}">{0}/fits/{1}/{2}</a></p>'.format(siteroot,re.split("_",userFolder)[1],servname)
            result += '<p>Conesearch link: {0}/conesearch/{1}/{2}</p>'.format(siteroot,re.split("_",userFolder)[1],servname)
            self.write_message(result)

        #Add a new user
        if message[0] == "N":
            if user!="admin":
                return
            if len(message)>1:
                userstate.newuser(message[1:])
                self.write_message("<p>Created user: {}</p>".format(message[1:]))
            else:
                userform = '<form action="javascript:newUser()">'
                userform += '<input type="text" id="newuser"/><br />'
                userform += '<input type="submit" value="Create"/></form>'
                self.write_message(userform)

        #Logout
        if message[0] == 'X':
            del session[userip]

    def on_close(self):
        """
        Closes WebSocket

        :return: None
        """
        print("WebSocket closed")
        SocketHandler.users.remove(self)
