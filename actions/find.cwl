#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: find

stdout: list.txt

arguments:
  - position: 1
    valueFrom: '-name'

inputs:
  STOA_targetfolder:
    type: string
    inputBinding:
      position: 0
  foldername:
    type: string
    inputBinding:
      position: 2

outputs:
  pathname:
    type: stdout


