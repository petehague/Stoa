#!/usr/bin/env python

# +

import sys

result = open("result.txt", "w")
result.write(sys.argv[1])
result.close()
