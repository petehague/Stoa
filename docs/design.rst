Design
======

This is the main design document, which is primarily aimed at developers

Overview
--------

.. image:: view1.png

The web interface initiates a WebSocket connection when started in order to drive the main UI. A secondary connection over the SAMP bridge allows communication between the web interface and SAMP enabled applications (such as TOPCAT, Aladdin etc.) running locally on the client machine.

Data Model
----------

The backend database records a table of processes, containing the path where a script was run, the name of that script and its md5 hash for version tracking, and the result of running the script.  

Queries to this process table can then be fed back into the interface, and a script run on only the highlighted processes.