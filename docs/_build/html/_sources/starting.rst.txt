Introduction
============

Stoa is a workflow management system that keeps your code and data on a server and allows you and your collaborators to control them remotely through a web interface. It organises your data into worktables, into which your code is embedded through CWL (Common Workflow Language). Worktables are linked together into a higher level execution graph. STOA is able to take the output of any worktable and present it online as a service to others. At present, the services supported are fits format download, and VO cone search.

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

Stoa is designed to operate complex processing pipelines across heterogenous
data sets. It does this mainly through Worktables - objects combining a workflow
object (written in CWL) with a data table. Any program can be inlcuded in a 
Worktable.

Getting Started
---------------

STOA requires Python 3 and some Python libraries, all available through ``pip`` - we recommend that you use a virtual environment when trying this out. 
When you have one set up, install ``numpy``, ``astropy``, ``wltool``, ``grpcio-tools`` and ``tornado`` and you should be good to go

In order to prepare STOA to run, type::

  ./ready.sh

this only need be done once per STOA install. Then type::

  ./start.sh $PWD/example 9000

to run the demo. Go to your browser and visit "localhost:9000" to try it out

First Use
---------

Login as admin (no password is required) and use ``Create New User`` to add yourself as a user. Logout with the X icon on the left and then log back in with your username. No passwords are required at present; the current version is not designed to be visible outside private networks. 

.. image:: newtable.png

Now create a worktable to implement the ``find`` command. Click on the ``Create New Worktable`` link and choose the workflow and yml file (which stores default values) then click ``Create``. The STOA install provides find.cwl and find.yml for testing purposes. Once the worktable is created, the screen should look like Figure 2. In order to run the worktable, it needs input for the workflow. Recall that each execution instance of a workflow is a row in the table, so in order to provide input for a workflow, we need to add a row. The dialogue box next to the ‘+’ sign can be used to type in a value for this workflow’s solitary input. Then click on + to add a row.

Once this table is present, go into it and add a new row with ``product`` as its input, and then run that row.

.. image:: worktableview.png

At this point, there will be two pathnames from the example folder. This information will be passed on to the next worktable. Create this worktable from the file ``getobject.cwl``. No .yml file is needed. Choose 'Key from other table' and then choose ``find.cwl`` and click on PATHNAME. Once you have done this, the screen should look like this:

.. image:: keytable.png

Now create the table. You will now see its Pathname field is populated by the output of the previous table. Run this table either using the Run All option, or by individually running each row.


Creating Worktables
-------------------

In order to create your own worktables in STOA, it is first necessary to create CWL wrappers for all the code you need. This is not typically difficult, and some wrappers for simple functions are included already for your convenience. There is a user guide for CWL at https://www.commonwl.org/user_guide/ which will teach you the basics of the language and quickly get you writing wrappers for your own scripts. In brief, CWL describes the tools you use in terms of their inputs and outputs, and then lets you combine them into workflows with linked inputs and outputs.

Any command line tool whose operation is driven by its command line parameters, and can be modified to store all its output in a file named ``cwl.output.json``, will have a very simple wrapper. Future versions of STOA will include a way to automatically generate such wrappers. 

