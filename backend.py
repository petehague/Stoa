
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
import fitsproc
from astropy.io import fits
from astroquery.ned import Ned
from astropy import coordinates
import astropy.units as units


profiles = []

started = False

targetFolder = ""
currentFolder = {}
userspace = {}
session = {}
runStatus = "Nothing"

siteroot = "http://127.0.0.1:8888"
scriptPath = os.path.realpath(__file__)
#webPath = "/".join(re.split("/", scriptPath)[:-1]) + "/"
webPath = os.path.split(scriptPath)[0] + "/"

obsfile = "/home/prh44/stoa/ALMA/observations.fits"

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
        c.execute("SELECT * FROM tblUsers")
        users = c.fetchall()
        for u in users:
            userspace[u[1]] = userstate.userState()
    started = True
    print("Backend started")

def projectInfo():
    """
    Produces the main page containing information about the current project

    :return: HTML output
    """
    # TODO Generalise this, move these links into some kind of task file
    outstring = '<h2>ALMA Archive</h2>'
    outstring += '<p><a href="javascript:getPath(\'V\')">\
                  Browse all folders</a></p>'
    outstring += '<p><a href="javascript:getPath(\'C\')">\
                  Create new results table</a></p>'

    outstring += '<p><a href="javascript:getPath(\'ta\')">Veron list</a></p>'

    outstring += '<p>'
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
    if len(filelist) == 1:
        if direction < 0:
            clip = len(re.split("/", currentFolder)[-2])+1
            currentFolder = currentFolder[:-clip]
        else:
            currentFolder += "/"+re.split("/", filelist[0])[-1] + "/"
        userspace[user].folder = currentFolder
        return folderList(targetFolder+currentFolder, direction, userip)
    if path+"product.xml" in filelist:
        filelist = xmlListing(path)
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
            '''userspace[user].folder = currentFolder = ""
            self.write_message(folderList(targetFolder+currentFolder,
                                          1, userip))'''

        if message[0] == 'T':
            self.write_message(fitsproc.resultsTable(message[1:], siteroot, targetFolder))

        if message[0] == 'B':
            if len(re.findall("/", currentFolder)) > 0:
                clip = len(re.split("/", currentFolder)[-2])+1
                currentFolder = currentFolder[:-clip]
                userspace[user].folder = currentFolder
                self.write_message(folderList(targetFolder+currentFolder,
                                              -1, userip))

        if message[0] == 'V':
            currentFolder += re.split("/", message)[-1]+"/"
            if len(message) == 1:
                currentFolder = ""
            print(currentFolder)
            userspace[user].folder = currentFolder
            self.write_message(folderList(targetFolder+currentFolder,
                                          1, userip))

        if message[0] == 'W':
            currentFolder = message[1:]+"/"
            print(currentFolder)
            userspace[user].folder = currentFolder
            self.write_message(folderList(targetFolder+currentFolder,
                                          1, userip))

        if message[0] == 'F':
            pipe.doFlag(message[1:])

        if message[0] == 'U':
            pipe.doUnflag(message[1:])

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

        if message[0] == 'r':
            userspace[user].proc.terminate()
            self.write_message("#Action terminated<br />"+stopCommand)


        if message[0] == 'D':
            fileReq = message[1:]
            if (len(re.findall(".fits", fileReq)) > 0):
                self.write_message("+Loading image...")
                currentFolder = '/'.join(re.split("/", fileReq)[:-1])+"/"
                parentFolder = '/'.join(re.split("/", currentFolder)[:-2])
                parentFolder = '/'.join(re.split("//", parentFolder))
                rfilename = targetFolder+currentFolder+"detections.reg"
                print(rfilename)
                if os.path.exists(rfilename):
                    regs, nregs = fitsproc.parseRegions(rfilename, user, fileReq, siteroot, userspace[user].folder, webPath)
                else:
                    rfilename, regs, nregs = "", "", 0
                imageblock = ""
                for i in range(-1, nregs):
                    visword = "visible" if i == -1 else "hidden"
                    image = fitsproc.htmlimage(targetFolder+fileReq, rfilename, i, -1)
                    imageblock += "<div id='img_{}' \
                    style='visibility:{}'>{}</div>\n".format(i+1,
                                                             visword,
                                                             image)
                fitsimage = fits.open(targetFolder+fileReq)
                position = coordinates.SkyCoord(ra=fitsimage[0].header['OBSRA'], dec=fitsimage[0].header['OBSDEC'],
                                                unit=(units.deg, units.deg), frame='fk5')
                searchradius = (abs(fitsimage[0].header['CDELT1'])*fitsimage[0].header['NAXIS1'])/2.0
                regs += "<p>NED Objects within {:3.3f} arcseconds of observation direction</p>".format(searchradius*3600)
                nedresults = Ned.query_region(position, radius = searchradius*units.deg, equinox = 'J2000.0')
                regs += htmlify(nedresults, ["Object Name", "RA(deg)", "DEC(deg)", "Type", "Redshift"])
                ymldata = "<p>"+fitsproc.mk_ned_url(fitsimage[0].header['OBSRA'],fitsimage[0].header['OBSDEC'])+"</p>"
                fitsimage.close()
                ymlname = targetFolder+"/".join(re.split("/",currentFolder)[:-2])+"/stoa.yml"
                ymldata += "<a href=\"javascript:getPath('Y{}')\">Edit control file</a><br />".format(ymlname)
                ymlfile = open(targetFolder+"/".join(re.split("/",currentFolder)[:-2])+"/stoa.yml","r")
                if pipe.isFlagged(parentFolder) == 0:
                    ymldata += "<a href=\"javascript:getPath('U{}')\">Unflag</a>".format(parentFolder)
                else:
                    ymldata += "<a href=\"javascript:getPath('F{}')\">Flag</a>".format(parentFolder)
                ymldata = "<p>{}</p>".format(fileReq) + ymldata
                self.write_message("+"+imageblock)
                self.write_message("*"+regs)
                self.write_message("#"+fitsproc.imagemeta(targetFolder+fileReq)+ymldata)

        if message[0] == 'Y':
            editor = "<p><a href=\"javascript:getPath('{}')\">Reset</a><br />".format(message)
            editor += "<a href=\"javascript:commitFile('{}')\">Commit</a></p>".format(message)
            editor += '<textarea rows="10" columns="80" style="width: 600px; height: 1000px;">'
            ymlfile = open(message[1:],"r")
            for line in ymlfile:
                editor += line
            editor += '</textarea>'
            self.write_message(editor)

        if message[0] == 'C':
            os.chdir(targetFolder)
            # This needs to be taken out of the code and generalised!
            os.system(pipe.scriptFolder+"/concat.py "+siteroot)
            t = Time(Time.now())
            t.format = 'isot'
            timestamp = t.value
            os.system("cp a_results.fits {}/usercache/a_results_{}.fits".format(webPath, timestamp))
            os.system("rm -rf a_results.fits")
            os.system("cp s_results.fits {}/usercache/s_results_{}.fits".format(webPath, timestamp))
            os.system("rm -rf s_results.fits")
            self.write_message(projectInfo())

        if message[0] == 'Q':
            result = "<p>"
            #pathlist = pipe.doQuery(message[1:])
            pathlist = pipe.doRun("")
            for pathname in pathlist:
                if len(pathname)>2:
                    result += '<a href="javascript:getPath(\'W{0}\')">{1}</a><br/>'.format(pathname[2:], trimPath(pathname[2:]))
            self.write_message(result+"</p>")

        if message[0] == 'E':
            console = pipe.doReport(message[1:])
            self.write_message("+<div id='conback'><p class='console'>{}</p></div".format(console))

        if message[0] == 't':
            if message[1]!="p":
                toggle = '<a href="javascript:getPath(\'tp\')">Reprocess</a><br />'
            else:
                toggle = ""
            if os.path.exists(obsfile):
                self.write_message(toggle+fitsproc.targetTable(obsfile, targetFolder, message[1]))
            else:
                self.write_message("<p>No observation file found</p>")

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
        if message[0] == 'X':
            del session[userip]

    def on_close(self):
        """
        Closes WebSocket

        :return: None
        """
        print("WebSocket closed")
        SocketHandler.users.remove(self)
