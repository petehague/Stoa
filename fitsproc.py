import numpy as np
from astropy.io import fits
from astropy.table import Table
import os
import re
import matplotlib.pyplot as plt
from astropy.coordinates import SkyCoord
from astropy import units as u

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

imageid = 0
tableid = 0

CROP_PROCESS = -1
CROP_NOPROC = -2
CROP_BEAM = -3

veronpath = os.path.split(os.path.realpath(__file__))[0] + "/"
if "ALMA" not in veronpath:
    veronpath += "ALMA/"
targetlist = fits.open(veronpath+"veron2010_vizier.fits")[1].data
targetcoords = SkyCoord(targetlist['RAJ2000'], targetlist['DEJ2000'],unit=(u.degree, u.degree), frame='icrs')

def mk_ned_url(RA, DEC, radius=0.1, debug=False, verbose=False):
    """
    RA in degrees
    Dec in dregrees
    radius in arc mins

    Code provided by R McMahon
    """
    link = "<A HREF=http://ned.ipac.caltech.edu/cgi-bin/objsearch?" \
           + "search_type=Near+Position+Search&in_csys=Equatorial&" \
           + "in_equinox=J2000.0&lon=" + str("%.5f" % RA) \
           + "d&lat=" + str("%.5f" % DEC) + "d&radius=" \
           + str(radius) + ">NED Link</A>"

    if debug or verbose:
        print(link)

    return link

def addCross(image, x, y, chan):
    """
    Adds a cross to a bitmap image

    :param image: numpy ndarray representing image
    :param x: x position of centre
    :param y: y position of centre
    :param chan: channel to draw to
    :return: None
    """
    a = 15
    mx, my, n = image.shape
    if x>mx-1 or y>my-1 or x<0 or y<0:
        return
    y0 = int(np.floor(y-a))
    y1 = int(np.ceil(y+a))
    x0 = int(np.floor(x-a))
    x1 = int(np.ceil(x+a))
    x0 = 0 if x0 < 0 else x0
    x1 = mx-1 if x1 > mx-1 else x1
    y0 = 0 if y0 < 0 else y0
    y1 = my-1 if y1 > my-1 else y1
    for v in range(y0, y1):
        if abs(v-y)>4:
            image[x, v, chan] = 1
            image[x-1, v, chan] = 1
            image[x+1, v, chan] = 1
    for u in range(x0, x1):
        if abs(u-x)>4:
            image[u, y, chan] = 1
            image[u, y-1, chan] = 1
            image[u, y+1, chan] = 1


def addEllipse(image, x, y, a, b, theta, chan):
    """
    Adds an ellipse to a bitmap image

    :param image: numpy ndarray representing image
    :param x: x position of centre
    :param y: y position of centre
    :param a: major axis
    :param b: minor axis
    :param theta: angle of major axis
    :param chan: channel to draw to
    :return: None
    """
    a = np.abs(a)
    b = np.abs(b)
    mx, my, n = image.shape
    y0 = int(np.floor(y-a))
    y1 = int(np.ceil(y+a))
    x0 = int(np.floor(x-a))
    x1 = int(np.ceil(x+a))
    x0 = 0 if x0 < 0 else x0
    x1 = mx-1 if x1 > mx-1 else x1
    y0 = 0 if y0 < 0 else y0
    y1 = my-1 if y1 > my-1 else y1
    for v in range(y0, y1):
        for u in range(x0, x1):
            i = (u-x)*np.cos(theta) + (v-y)*np.sin(theta)
            j = (v-y)*np.cos(theta) - (u-x)*np.sin(theta)
            if ((abs(i)/a)**2 + (abs(j)/b)**2 < 1):
                image[u, v, chan] = 1


def imagemeta(imagename):
    """
    Converts metadata in .fits file header into HTML formatted text

    :param imagename: Name of .fits file to open
    :return: HTML text
    """
    imagefile = fits.open(imagename)
    headertext = "<p>"
    head = imagefile[0].header
    headertext += "Pixel size: {} x {}<br />".format(head['NAXIS1'],
                                                     head['NAXIS2'])
    xsize = np.round(abs(head['CDELT1'])*head['NAXIS1']*3600, decimals=1)
    ysize = np.round(abs(head['CDELT2'])*head['NAXIS2']*3600, decimals=1)
    headertext += "Sky size: {}'' x {}''<br />".format(xsize, ysize)
    headertext += "</p>"
    return(headertext)

def matchquasars(ra, dec, radius):
    p = SkyCoord(ra,dec,unit=(u.degree, u.degree), frame='icrs')
    # n, m, d2d, d3d = p.search_around_sky(targetcoords, radius*u.degree)
    sep = p.separation(targetcoords)
    radius = radius*u.degree
    dxlist = np.where(sep<radius)[0]
    for index in dxlist:
        yield {'ra': targetlist[index]['RAJ2000'],
               'dec': targetlist[index]['DEJ2000']}

def smartcropper(rawmap, ax, bx, ay, by):
    result = np.ndarray(shape=(bx-ax, by-ay, 4))
    mx,my,n = rawmap.shape
    print(rawmap[10,10,:])
    for y in range(ay,by):
        for x in range(ax,bx):
           if y<0 or x<0 or y>=my or x>=mx:
             result[x-ax,y-ay,:] = [0, 0, 0, 1]
           else:
             result[x-ax,y-ay,:] = rawmap[x,y,:]
    return result

def processimage(imagename, regionfile, marker, crop, x=-1, y=-1):
    """
    Generates a PNG image from a fits file, and adds source information

    :param imagename: Name of .fits file to work on
    :param regionfile: Name of .reg file containing ellipse data
    :param marker: Index of which ellipse to highlight (-1 for none)
    :return: HTML formatted string pointing to the saved image
    """
    global rgbArray, mx, my, x0, dx, px, y0, dy, py, beamsize
    imagefolder = "/".join(re.split("/",imagename)[:-1])

    if not os.path.exists(imagename):
        return ""

    imagefile = fits.open(imagename)
    if marker == -1 or (marker == 0 and crop>-1):
        x0 = imagefile[0].header['CRVAL1']
        dx = imagefile[0].header['CDELT1']
        px = imagefile[0].header['CRPIX1']
        y0 = imagefile[0].header['CRVAL2']
        dy = imagefile[0].header['CDELT2']
        py = imagefile[0].header['CRPIX2']
        beamsize = imagefile[0].header['BMAJ']
        imageArray = imagefile[0].data[0, 0]
        mx, my = imageArray.shape
        rgbArray = np.ndarray(shape=(mx, my, 4))
        norm = 0
        scalemin = 0
        for i in range(mx):
            for j in range(my):
                v = imageArray[i, j]
                if np.isnan(v):
                    rgbArray[i, j, :] = [0, 0, 0, 0]
                else:
                    if v > norm:
                        norm = v
                    if v < scalemin:
                        scalemin = v
                    rgbArray[i, j, :] = [v, v, v, 1]
        norm -= scalemin
        rgbArray[:, :, 0: 3] -= scalemin
        rgbArray[:, :, 0: 3] /= norm

    colArray = np.copy(rgbArray)
    markindex = 0
    sourcepoints = []
    if len(regionfile) > 0:
        regions = open(regionfile, "r")
        for reg in regions:
            tokens = re.split(" ", reg)
            if "ellipse" in tokens[0]:
                if "red" in tokens[7]:
                    chan = 0
                else:
                    chan = 1
                if markindex == marker:
                    chan = 2
                markindex += 1
                sx = px+(float(tokens[1])-x0)/dx
                sy = py+(float(tokens[2])-y0)/dy
                a = max(float(tokens[3])/dx, float(tokens[4])/dy)
                sourcepoints.append([sy, sx, a])
                if crop==-1:
                    addEllipse(colArray,
                               sy,
                               sx,
                               float(tokens[3])/dx, float(tokens[4])/dy,
                               np.pi/2. + float(tokens[5])*np.pi/180.,
                               chan)

    for quasar in matchquasars(imagefile[0].header['OBSRA'], imagefile[0].header['OBSDEC'], np.abs(dx*mx)):
        qx = int(px + (quasar['ra']-x0)/dx)
        qy = int(py + (quasar['dec']-y0)/dy)
        addCross(colArray, qx, qy, 2)

    if crop>-1 or x>-1 or y>-1:
        fileroot = "crop_"
        sz = (5 / 3600) / abs(dx)
        if crop==CROP_BEAM+CROP_PROCESS:
            sz = (beamsize/abs(dx))*10
        if crop>-1:
            croptarget = sourcepoints[crop]
            x = croptarget[1]
            y = croptarget[0]
            sz = max(croptarget[2],sz)
        fileroot += "{}_{}_".format(int(x), int(y))
        if crop==CROP_BEAM+CROP_PROCESS:
            fileroot += "B_"
        ax = max(int(x-sz),0)
        ay = max(int(y-sz),0)
        bx = min(int(x+sz),mx-1)
        by = min(int(y+sz),my-1)
        print("Image: "+fileroot)
        print("px={}  py={}".format(x,y))
        print("x=({},{})  y=({},{})".format(ax,bx,ay,by))
        print("size={}  dx={}  dy={}".format(sz,dx,dy))
        #colArray = colArray[ay:by, ax:bx, :]
        colArray = smartcropper(colArray,int(x-sz),int(x+sz),int(y-sz),int(y+sz))
        if colArray.size<4:
            colArray = np.zeros((20,20,4))
    else:
        fileroot = "plot_"
    
    plt.imsave(arr=colArray,
               cmap="gray",
               fname=imagefolder+"/"+fileroot+"{}.png".format(marker+1))
 

def htmlimage(imagename, regionfile, marker, crop, x=-1, y=-1):
    global imageid
    if crop>-1 or x>-1 or y>-1:
        fileroot="crop_"
        imsize = "150px"
        imclass = "croppedimage"
        if x>-1 or y>-1:
            fileroot += "{}_{}_".format(int(x),int(y))
    else:
        fileroot="plot_"
        imsize = "300px"
        imclass = "fitsimage"
    if crop==CROP_BEAM+CROP_NOPROC or crop==CROP_PROCESS+CROP_BEAM:
        fileroot+="B_"

    imagefolder = "/".join(re.split("/",imagename)[:-1])
    if crop==CROP_PROCESS or crop==CROP_PROCESS+CROP_BEAM:
        # Note this may cause problems, but for now its the best fix
        # if not os.path.exists(imagefolder+"/"+fileroot+"{}.png".format(marker+1)):
        processimage(imagename, regionfile, marker, crop, x, y)
    imageid += 1
    #os.link(imagefolder+"/plot_{}.png".format(marker+1),webPath+"usercache/image{}_{}.png".format(imageid,marker))
    return "<img class='"+imclass+"' height="+imsize+" width="+imsize+" src=\'\
           /file/"+imagefolder+"/"+fileroot+"{}.png?instance={}\' />".format(marker+1, np.random.randint(1000000))


def parseRegions(regionfile, user, fileReq, siteroot, userfolder, webPath):
    """
    Extract information about sources in an image

    :param regionfile: The .reg file specifying the ellipse of each source
    :param user: The ID of the requesting user
    :param fileReq: URL to locate image file
    :return: HTML formatted table of sources, number of sources
    """
    global tableid
    regions = open(regionfile, "r")
    path = "/".join(re.split("/", regionfile)[:-1]) + "/"

    if os.path.exists(path+"s_sources.fits"):
        sextractor = fits.open(path+"s_sources.fits")
        sflux = sextractor[1].data['FLUX_AUTO']
        sfluxerr = sextractor[1].data['FLUXERR_AUTO']
    else:
        sflux = []
        sfluxerr = []
    if os.path.exists(path+"results_comp.fits"):
        aegean = fits.open(path+"results_comp.fits")
        aflux = aegean[1].data['int_flux']
        afluxerr = aegean[1].data['err_int_flux']
    else:
        aflux = []
        afluxerr = []
    scounter, acounter, totalcount = 0, 0, 0

    sampParams = {}
    sampParams['name'] = "Web Table"
    sampParams['url'] = siteroot+"/stage/table.xml"
    sampTable = Table(names=("Type",
                             "RA",
                             "Dec",
                             "A",
                             "B",
                             "Theta",
                             "Flux",
                             "Flux_err"),
                      dtype=('S1', 'f8', 'f8', 'f8',
                             'f8', 'f8', 'f8', 'f8'))

    outstring = ("<table><tr><th>Type</th><th>RA</th><th>Dec</th><th>A</th>"
                 "<th>B</th><th>Theta</th><th>Flux (Jy)</th><th>Flux Err</th>"
                 "</tr>")
    for reg in regions:
        tokens = re.split(" ", reg)
        if "ellipse" in tokens[0]:
            if "red" in tokens[7]:
                flux = sflux[scounter]
                flux_err = sfluxerr[scounter]
                stype = "S"
                scounter += 1
            else:
                flux = aflux[acounter]
                flux_err = afluxerr[acounter]
                stype = "A"
                acounter += 1
            ra = np.round(float(tokens[1]), 5)
            dec = np.round(float(tokens[2]), 5)
            A = np.round(float(tokens[3])*3600, 3)
            B = np.round(float(tokens[4])*3600, 3)
            Theta = np.round(float(tokens[5]), 2)
            outstring += ("<tr><td><a href='javascript:switchto({})'>{}</a>"
                          "</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
                          "<td>{}</td><td>{:5.5f}</td><td>{:5.5f}</td>"
                          "</tr>").format(totalcount,
                                          stype,
                                          ra,
                                          dec,
                                          A,
                                          B,
                                          Theta,
                                          flux,
                                          flux_err)
            sampTable.add_row([stype, ra, dec, A, B, Theta, flux, flux_err])
            totalcount += 1
    obstarget = fits.open(path+"input.fits")
    for item in obstarget[0].header:
        if 'HISTORY' not in item and len(item) > 0 and 'COMMENT' not in item:
            value = obstarget[0].header[item]
            if type(value) == str:
                col = np.empty(totalcount, dtype=np.dtype('S32'))
            else:
                col = np.empty(totalcount)
            col.fill(value)
            sampTable[item] = col
    linkurl = siteroot+"?"+urlencode({'loc': userfolder,
                                      'action': fileReq})
    outstring += "</table><div id='tabcontrols'><a href='javascript:sendTable(\""+siteroot+"/stage/table{}.xml\")'>\
                 Send via SAMP</a><br /><a href='{}'>Send as link</a>\
                 </div><div id='nregs'\style='visibility: hidden'>\
                 {}</div>\n".format(tableid, linkurl, totalcount+1)
    os.system("rm -f "+webPath+"usercache/table{}.xml".format(tableid))
    sampTable.write(webPath+"usercache/table{}.xml".format(tableid),
                    format="votable")
    tableid += 1
    return outstring, totalcount


def resultsTable(filename, siteroot, targetFolder):
    shortfilename = re.split("/",filename)[-1]
    outstring = '<h2>{}</h2>'.format(shortfilename)
    outstring += "<p><table><tr><th>Project</th><th>RA</th><th>Dec</th><th>Link</th><th>Output</th><th>Image</th></tr>"
    tabledata = fits.open(filename)
    tbltype = 'ra' in tabledata[1].header.values()
    outstring += '<p>FITS Download: <a href="'+siteroot+'/stage/{0}">{0}</a><br /></p>'.format(filename)
    imid = 0
    lastfile = ""
    for row in tabledata[1].data:
        if lastfile==row['FILE']:
            imid += 1
        else:
            imid = 0
        lastfile = row['FILE']
        projectname = re.split("/",row['FILE'])[1]
        if tbltype:
            ra = row['RA']
            dec = row['Dec']
        else:
            ra = row['ALPHA_J2000']
            dec = row['DELTA_J2000']
        link = row['FILE']+"input.fits"
        console = row['FILE']
        outstring += "<tr><td>{}</td><td>{}</td><td>{}</td>".format(projectname,ra,dec)
        outstring += "<td><a href=\"javascript:view('{}')\">Image</a></td>".format(link)
        outstring += "<td><a href=\"javascript:getPath('E{}')\">Console</a></td>".format(console)
        outstring += "<td>" + htmlimage(targetFolder+link,
                                        targetFolder+re.split("input.fits", link)[0]+"detections.reg", 
                                        imid, imid) + "</td></tr>"
    outstring += "</table></p>"
    return outstring


def targetTable(obsfile, targetFolder, reproc):
    outstring = '<h2>Veron Catalogue</h2>'
    outstring += "<p><table><tr><th>Object</th><th>RA</th><th>Dec</th><th>Link</th>"
    outstring += "<th>NED</th><th>Image (10 arcsec)</th><th>Image (20 beam)</tr>"

    obs = Table.read(obsfile, format="fits")

    if reproc=='p':
        reproc = CROP_PROCESS
    else:
        reproc = CROP_NOPROC

    lastname=""
    #if reproc==CROP_PROCESS:
    #    obs=obs[0:4]
    for row in obs:
        ra = row['RA']
        dec = row['Dec']
        link = row['Image']
        px = row['X']
        py = row['Y']
        name = row['Name']
        nedlink = mk_ned_url(float(ra), float(dec))
        if name==lastname:
            lastname = name
            name = ""
            ra = ""
            dec = ""
        else:
            lastname = name
        outstring += "<tr><td>{}</td><td>{}</td><td>{}</td>".format(name,ra,dec)
        outstring += "<td><a href=\"javascript:view('{}')\">Image</a></td>".format(link)
        outstring += "<td>"+nedlink+"</td>"
        outstring += "<td>" + htmlimage(targetFolder+link,
                                        targetFolder+re.split("input.fits", link)[0]+"detections.reg",
                                        -1, reproc, px, py) + "</td>"
        outstring += "<td>" + htmlimage(targetFolder+link,
                                        targetFolder+re.split("input.fits", link)[0]+"detections.reg",
                                        -1, CROP_BEAM+reproc, px, py) + "</td></tr>"
    outstring += "</table></p>"
    return outstring
