#!/usr/bin/env python

import sys
import random
import time

inp = open(sys.argv[1], "r")
try: 
  num = int(inp.read())
except:
  num = -1
inp.close()

delay = random.randrange(0,5)
time.sleep(delay)

result = open("result.txt", "w")
result.write("{} {}".format(num,random.randrange(0,10)))
result.close()

print(num)
