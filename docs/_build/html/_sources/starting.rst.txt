Introduction
============

Stoa is designed to operate complex processing pipelines across heterogenous
data sets. It does this mainly through Worktables - objects combining a workflow
object (written in CWL) with a data table. Any program can be inlcuded in a 
Worktable.

Getting Started
---------------

Download the code from https://github.com/petehague/stoa and type::

  ./demo.sh

in the installation directory. Then open a web browser at the address::

  http://127.0.0.1:9000

General Usage
-------------

The central data structure in Stoa is the Worktable. Worktables encapsulate 
workflows, written in CWL (Common Workflow Language), which define the inputs and
outputs of either a single command, or a workflow composed of multiple commands 
with their inputs and outputs linked. A Worktable is also a table - whose columns
are defined by the inputs and outputs of the workflow. Once the user has written
a CWL workflow, a Worktable can be automatically generated from it.

The columns corresponding to the workflow outputs are read only, the columns corresponding
to the workflow input can be written to, and writing to them changes the status of a row
to indicate that the outputs no longer correspond to the inputs and the row needs to be 
rerun. Stoa can handle this automatically. 

Worktables are linked in a relational manner, so the output from one Worktable can be used
to populate the rows of another. For a trivial example, a simple worktable can encapsulate the Bash
command 'find' to locate all the folders in a large directory structure where a process
should be run. The output of this, one pathname per row, could be used to populate the input
columns of the Worktable encapsulating another process
