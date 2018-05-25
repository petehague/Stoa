#!/usr/bin/env python

import sys
import random
import time

if sys.argv[1] == "-f":
  inp = open(sys.argv[2], "r")
  num = int(inp.read())
  inp.close()
else:
  num = int(sys.argv[1])

delay = random.randrange(0,5)
time.sleep(delay)

result = open("result.txt", "w")
result.write("{} {}".format(num,random.randrange(0,10)))
result.close()
