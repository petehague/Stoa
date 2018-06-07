#!/usr/bin/env python

import random

if len(sys.argv)>1:
    ranmax = sys.argv[1]
else:
    ranmax = 100

value = random.randrange(0,ranmax)

print(value)
