#!/usr/bin/env python

# +

import sys
import numpy as np

print(sys.argv)

if np.random.random()>0.5:
  raise ValueError('RNG too high')
