#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: touch.py

inputs: 
  touchparam:
    type:
      - type: record
        name: touchcode
        fields: 
          touchcode:
            type: string 
            inputBinding:
              position: 1
      - type: record
        name: touchfile
        fields:
          touchfile:
            type: File
            inputBinding:
              prefix: -f    

outputs:
  results:
    type: File
    outputBinding:
      glob: result.txt
