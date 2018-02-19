#!/usr/bin/env python
'''CWL
#!/usr/env/bin cwl-runner

cwlVersion: 1.0
class: CommandLineTool
baseCommand: touch.py
'''

# +

import sys

print(sys.argv)
