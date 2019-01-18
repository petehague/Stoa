'''
   Stoa Client

   A library to allow python users to interact with STOA
'''

import urllib.request
import re
import io
import os
from astropy.table import Table
import tempfile

def services(url):
    '''
      services(url)

      Returns a list of STOA services available at <url>
    '''
    result = urllib.request.urlopen(url+"/ls").read()
    if result[0:1]=='LS':
        services = re.split("\n", result[3:])
        return services
    else:
        raise RunTimeError("Bad response from "+url)

def getTable(service):
    '''
      getTable(service)

      Returns a table from the specified STOA service
    '''
    result = urllib.request.urlopen(service).read()
    targetDir = tempfile.mkdtemp()
    with open(os.path.join(targetDir,"service.fits"), "wb") as bfile:
        bfile.write(result)
    
    tab = Table.read(os.path.join(targetDir, "service.fits"),format="fits")
    return(tab)
