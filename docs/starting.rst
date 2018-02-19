Introduction
============

Stoa is designed to operate complex processing pipelines across heterogenous
data sets. It does this mainly through 'action scripts' - python programs run
repeatedly in multiple locations, with different parameters and different
environments. Any python program can be an action script, however additional
control information can be included in the script to improve its interaction
with Stoa

Getting Started
---------------

Download the code from https://bitbucket.org/PeterHague/stoa and type::

  ./webhost.py .. 9000 local

in the installation directory. Then open a web browser at the address::

  http://127.0.0.1:9000

General Usage
-------------

The web server must be pointed to the folder where the data are located.
The usual command format is::

  webhost.py <target folder> <port number>

If a port number is not supplied, it will default to 9000. If you wish to
access Stoa on the same machine the server runs, the 'local' parameter
must be added to the end

The interface is generally used thus:

1) Run a script on all matching paths

2) Query the results to find any that are unsatisfactory

3) Use the query to launch another run on that subset

4) Repeat until all results are satisfactory

The stopping criterion is to be determined by the user