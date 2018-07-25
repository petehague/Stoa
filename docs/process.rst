How worktables are processed
============================

Actions are pushed to a queue, and then removed and implemented by an action server. A YAML file is created that details the specifics on the inputs, and this is used to guide the workflow.

Action queue
------------

Each item on the queue consists of a worktable name, and a key. This key indicates the row of the worktable to be indicated (it is taken from the primary key field). 

Execution
---------

If the key field is a pathname (TODO: specifiy how this is known) then the PATH variable used in execution is taken from this field. The YAML file that holds the parameters is stored at this location.

Output
------

Output bindings are processed as in CWL. However, if the stdout file is callecd 'list.txt' then it binds each line to an output.
