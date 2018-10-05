#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: find

stdout: list.txt

arguments:
  - position: 0
    valueFrom: '/home/prh44/rds/ALMA/block2'
  - position: 1
    valueFrom: '-name'

inputs:
  foldername:
    type: string
    inputBinding:
      position: 2

outputs:
  pathname:
    type: stdout


