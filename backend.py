
import tornado.websocket
import re
import os
import glob
import pipe
import xml.etree.ElementTree as et
import userstate
import sqlite3 as sql
from astropy.time import Time
from multiprocessing import Process
import time
from yml import yamler
from imp import load_source
from fnmatch import fnmatch
from astropy.coordinates import SkyCoord
from astroquery.vo_conesearch import ConeSearch
from astroquery.vo_conesearch.exceptions import VOSError
from astropy.table import Table


profiles = []

started = False

targetFolder = ""
currentFolder = {}
userspace = {}
session = {}
runStatus = "Nothing"

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


def startBackend():
    """
    Initialises the web database (distinct from the pipeline one) and
    loads in user table

    :return: None
    """
    global started
    if started:
        return
    dbcon = sql.connect('contents.db')
    # pipe.opts["ActionPath"] = "/".join(re.split("/", scriptPath)[:-1])+"/"
    with dbcon:
        c = dbcon.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS tblUsers(\
                   UID INT,\
                   Username VARCHAR(100))")
        c.execute("SELECT * FROM tblUsers")
        users = c.fetchall()
        for u in users:
            userspace[u[1]] = userstate.userState()
        if len(users)==0:
            c.execute("INSERT INTO tblUsers (UID, Username) VALUES (0,'admin')")
            userspace['admin'] = userstate.userState()
    started = True
    print("Backend started")


def projectInfo():
    """
    Produces the main page containing information about the current project

    :return: HTML output
    """
    # TODO Generalise this, move these links into some kind of task file
    outstring = '<h2>{}</h2>'.format(projectname)
    outstring += '<p><a href="javascript:getPath(\'V\')">\
                  Browse all folders</a></p>'
    outstring += '<p><a href="javascript:getPath(\'C\')">\
                  Create new results table</a></p>'

    #outstring += '<p><a href="javascript:getPath(\'ta\')">External list</a></p>'
    for ref in reftables:
        outstring += '<p><a href="javascript:getPath(\'tf{0}\')">{0}</a></p>'.format(ref)

    outstring += '<p>'
    outstring += '<a href="javascript:getPath(\'TTestTable?0\')">Example Table</a><br />'
    for filename in glob.glob(webPath+"usercache/*results*"):
        outstring += '<a href="javascript:getPath(\'T{0}\')">{0}</a><br />'.format(filename)
    outstring += '</p>'
    return outstring


def target():
    """
    Reports the target folder

    :return: The name of the current target folder
    """
    return targetFolder


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


def usercheck(userip):
    """
    Check if the user is valid

    :param userip: The IP address of the user (currently used as ID)
    :return: A session ID, or "False" if there is no such user
    """
    if userip in session:
        return session[userip] in userspace
    else:
        return False


def getwsroot(userip):
    """
    Get the address this user has to send ws connections to

    :param userip: The IP address of the user (currently used as ID)
    :return: A URL
    """
    if userip in session:
        return userspace[session[userip]].wsroot
    else:
        return False


def getResource(filename):
    """
    Read in specified file as single string

    :param filename: The name of the file to be read
    :return: A string
    """
    f = open(filename, "r")
    content = ""
    for line in f:
        content += line
    return content


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

#Quite slow
def trimPath(pathname):
    folders = re.split("/", pathname)
    pathstring = ""
    trimmedpath = ""
    for node in folders:
        filelist = glob.glob(targetFolder+pathstring+"/*")
        pathstring += "/"+node
        if len(filelist)>1:
            trimmedpath += "/"+node
        else:
            trimmedpath += "/..."
    return trimmedpath


def folderList(path, direction, userip):
    """
    Generate an HTML listing of a folder

    :param path: The path of the folder
    :param direction: Direction of browsing (1 for going down, -1 for up)
    :param userip:  The IP address of the user (currently used as ID)
    :return: HTML string
    """
    global userspace
    user = session[userip]
    currentFolder = userspace[user].folder

    flaglist = makeFlagList()
    filelist = glob.glob(path+"*")
    filelist.sort()
    if len(filelist) == 1 and os.path.isdir(filelist[0]):
        if direction < 0:
            clip = len(re.split("/", currentFolder)[-2])+1
            currentFolder = currentFolder[:-clip]
        else:
            currentFolder += "/"+re.split("/", filelist[0])[-1] + "/"
        userspace[user].folder = currentFolder
        return folderList(targetFolder+currentFolder, direction, userip)
    if path+"product.xml" in filelist:
        filelist = xmlListing(path) #Switch over to yml and generalise
    output = '<ul class="filelist">'
    for filename in filelist:
        shortfile = re.split("/", filename)[-1]
        if os.path.isdir(filename):
            output += '\n<li class="filename"><div class="filetext">\
                       <a href="javascript:getPath(\'V{0}\')">\
                       {1}</a></div></li>'.format(filename, shortfile)
        else:
            template = '\n<li class="filename" id="{1}"><div class="filetext">\
            <a href="javascript:view(\'{1}\')">{0}</a></div><a class="off"\
            href="javascript:flag(\'{1}\',1)" style="visibility: {4}"\
            id="{1}">{2}</a><a class="on" href="javascript:flag(\'{1}\',0)"\
            style="visibility: {5}" id="{1}">{3}</a></li>'
            star = getResource(webPath+"ui/star.svg")
            fstar = getResource(webPath+"ui/fillstar.svg")
            if filename in flaglist:
                output += template.format(shortfile,
                                          filename.replace(targetFolder,"./"),
                                          star,
                                          fstar,
                                          "hidden",
                                          "visible")
            else:
                output += template.format(shortfile,
                                          filename.replace(targetFolder,"./"),
                                          star,
                                          fstar,
                                          "visible",
                                          "hidden")
    output += "</ul>"
    userspace[user].folder = currentFolder
    return output


def prettify(constring):
    """
    Convert terminal colour codes to HTML

    :param constring: Terminal output string
    :return: HTML formatted string
    """
    targets = {'\n': '<br />',
               '\033[1m': '<span class="bold">',
               '\033[0m': '</span>',
               '\033[91m': '<span class="red">',
               '\033[92m': '<span class="green">'}
    for t in targets:
        constring = constring.replace(t, targets[t])
    return constring


def procMonitor(command, targetFolder, user, runtype):
    """
    Manages the action as a child process.

    :param command: The name of the command to run
    :param targetFolder: The location to run it
    :param user: The user index
    :return: None
    """
    global userspace
    if runtype=='f':
        command = 'run '+command
    for report in pipe.commandgen(command, targetFolder):
        repstring = "{}".format(prettify(report))
        userspace[user].q.put(repstring)


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
        # Code for checking page originating WS request
        # print(urllib.parse.urlparse(origin))
        # self.reqorigin = urllib.parse.urlparse(origin).netloc
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

        * L: Login
        * H: Home
        * B: Back
        * V: View folder
        * F: Flag target
        * U: Unflag target
        * A: Get action list
        * R: Run the specified action
        * D: Display a file
        * C: Concatenate results
        * Q: Query the process table
        * X: Logout

        :param message: WS message string
        :return: None
        """
        global currentFolder, userspace

        userip = self.request.remote_ip

        if message[0] == 'L':
            tokens = re.split(",", message[1:])
            session[userip] = tokens[0]
            user = tokens[0]
            if user in userspace:
                userspace[user].wsroot = tokens[1]

        if userip in session:
            user = session[userip]
            currentFolder = userspace[user].folder
            userspace[user].ip = userip
        else:
            self.write_message('<script  type="text/javascript">window.location="/login"</script>')
            return

        # Always attempt to finanlise any process running
        userspace[user].finalise()

        if message[0] == '.':
            if message[1] == '1':
                return
            if message[1] == '2':
                if len(userspace[user].procreport) > 0:
                    self.write_message("#"+userspace[user].procreport)
                    userspace[user].procreport="" #This needs changing really
                    self.write_message("t1000")
                else:
                    userspace[user].appendQueue()
                    self.write_message("+<div id='conback'><p class='console'>"+"".join(userspace[user].buff[-consoleSize:])+"</p></div>")
                    self.write_message("t10")
                return

        print(time.strftime('[%x %X]')+" "+user+"("+userip+"): "+message)

        if message[0] == 'H':
            self.write_message(projectInfo())

        if message[0] == 'T':
            tokens = re.split("\?",message[1:])
            tableName = tokens[0]
            if len(tokens>1):
                tableRow = tokens[1]
            else:
                tableRow = 0
            bottomSlice = "<table>"
            for index in range(tableRow-1,tableRow+1):
                bottomSlice += "<tr>" + (["<td></td>"]*5).join() + "</tr>"
            bottomSlice += "</table>"
            self.write_message( "*<p>{}</p>{}<br />".format(tableName,bottomSlice))



        #Go back up a level in the file system
        if message[0] == 'B':
            if len(re.findall("/", currentFolder)) > 0:
                clip = len(re.split("/", currentFolder)[-2])+1
                currentFolder = currentFolder[:-clip]
                userspace[user].folder = currentFolder
                self.write_message(folderList(targetFolder+currentFolder,
                                              -1, userip))

        #View a specified subfolder of the current folder
        if message[0] == 'V':
            currentFolder += re.split("/", message)[-1]+"/"
            if len(message) == 1:
                currentFolder = ""
            print(currentFolder)
            userspace[user].folder = currentFolder
            self.write_message(folderList(targetFolder+currentFolder,
                                          1, userip))

        #View a specified folder
        if message[0] == 'W':
            currentFolder = message[1:]+"/"
            print(currentFolder)
            userspace[user].folder = currentFolder
            self.write_message(folderList(targetFolder+currentFolder,
                                          1, userip))

        #Flag a target
        if message[0] == 'F':
            pipe.doFlag(message[1:])

        #Unflag a target
        if message[0] == 'U':
            pipe.doUnflag(message[1:])

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
            if userspace[user].proc is not None:
                commandtext += "<p>There is currently an action in progress<br />"+stopCommand+"</p>"
            monitor = "<div id=monitor></div>"
            for command in commandlist:
                commandtext += '<a href="javascript:getPath(\'{0}{1}\')">\
                                {1}</a><br />'.format(runtype,command.strip())
            self.write_message("#"+monitor+flagToggle+commandtext)

        #Run an action
        if message[0] == 'R' or message[0] == 'f':
            monitor = "<div id=monitor></div>"
            self.write_message("#"+monitor+"Processing command "+message[1:]+"...<br />"+stopCommand)
            if (userspace[user].proc is None):
                userspace[user].proc = Process(target=procMonitor,
                                               args=(message[1:].strip(),
                                                     targetFolder,
                                                     user,
                                                     message[0]))
                userspace[user].proc.start()
            else:
                self.write_message("#"+monitor+"Action already in progress<br />"+stopCommand)

        #Terminate an action
        if message[0] == 'r':
            userspace[user].proc.terminate()
            self.write_message("#Action terminated<br />"+stopCommand)


        #Display a fits image
        if message[0] == 'D':
            fileReq = message[1:]
            if fnmatch(fileReq,handlerpattern):
                self.write_message("+Loading image...")
                self.write_message(filehandler.stoa(targetFolder+fileReq))

        #Edit a control file
        if message[0] == 'Y':
            editor = "<p><a href=\"javascript:getPath('{}')\">Reset</a><br />".format(message)
            editor += "<a href=\"javascript:commitFile('{}')\">Commit</a></p>".format(message)
            editor += '<textarea rows="10" columns="80" style="width: 600px; height: 1000px;">'
            ymlfile = open(message[1:],"r")
            for line in ymlfile:
                editor += line
            editor += '</textarea>'
            self.write_message(editor)

        #Concatenate data from runs
        if message[0] == 'C':
            '''os.chdir(targetFolder)
            # This needs to be taken out of the code and generalised!
            os.system(pipe.scriptFolder+"/concat.py "+siteroot)
            t = Time(Time.now())
            t.format = 'isot'
            timestamp = t.value
            os.system("cp a_results.fits {}/usercache/a_results_{}.fits".format(webPath, timestamp))
            os.system("rm -rf a_results.fits")
            os.system("cp s_results.fits {}/usercache/s_results_{}.fits".format(webPath, timestamp))
            os.system("rm -rf s_results.fits")'''
            self.write_message(projectInfo())

        #Query the run log
        if message[0] == 'Q':
            result = "<p>"
            #pathlist = pipe.doQuery(message[1:])
            pathlist = pipe.doRun("")
            for pathname in pathlist:
                if len(pathname)>2:
                    result += '<a href="javascript:getPath(\'W{0}\')">{1}</a><br/>'.format(pathname[2:], trimPath(pathname[2:]))
            self.write_message(result+"</p>")

        #Display a results table
        if message[0] == 't':
            if message[1]=="f":
                coords = open(reftables[message[2:]],"r")
                for line in coords:
                    pos = SkyCoord(line, unit=("deg", "deg"))
                    try:
                        sources = ConeSearch.query_region(pos, '0.1 deg')
                        sources = sources.to_table() #Its shocking I have to do this!
                    except VOSError:
                        sources = Table(names=['objID', 'ra', 'dec'])
                    self.write_message(htmlify(sources,collist=['objID', 'ra' ,'dec']))
            if message[1]!="p":
                toggle = '<a href="javascript:getPath(\'tp\')">Reprocess</a><br />'
            else:
                toggle = ""

        #Control file editing console
        if message[0] == 'S':
            result = "<a href=\"javascript:getPath('Ystoa.yml')\">Edit master file</a><br />"
            commandlist = pipe.doActlist("")
            for command in commandlist:
                if 'cwl' in command:
                    rootname = pipe.opts["ActionPath"]+(re.split(".cwl", command)[0]).strip() + ".yml"
                    if not os.path.exists(rootname):
                        open(rootname,"a").close()
                    result+="<a href=\"javascript:getPath('Y{}')\">Edit {} default file</a><br />".format(rootname, command)
            self.write_message(result)

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
