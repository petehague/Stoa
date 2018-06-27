#!/usr/bin/env python

import os
import sys
import re

params = {"port": 9000,
          "target": "./example"}

if len(sys.argv)>1:
  for arg in sys.argv:
    tokens = re.split("=",arg.strip())
    if len(tokens)>1:
      var = tokens[0]
      value = tokens[1]
      params[var] = value

#TODO: make this a more pythonic way of controlling the threads
os.system("python userstate.py &")
os.system("python action.py &")
os.system("python webhost.py {} {}".format(params["target"], params["port"]))
