.. _example:

Sample Project
==============


This tutorial will guide you through a simple example, on how *p5control* can be used to automate the control of your experimental setups. For this, we will create a mock driver for an imagined instrument which we then can use to perform fictional measurements.

Structure
---------

Before starting with the simple tutorial, we begin by giving an overview of the structure of how *p5control* aims to control your experimental setup.

For each type of instrument in your experiment, you will need to write a *Driver*, which interfaces with the instrument. There are some expectations about the driver made by *p5control*. For some functionality, you will need to implement certain functions. Furthermore, you can add custom functionality and logic to your driver. 

The `Instrument Server` will contain the actual driver instances and makes them available to the user in a convenient way. The server part consists of a `rpyc <https://rpyc.readthedocs.io/en/latest/>`_ service. This server structure makes sure that there exists only one driver instance communicating with the device, the one of the server. Each gui or jupyter notebook can connect to the server. This allows multiple clients access to the device without competing drivers. In addition, the `Instrument Server` provides controls to acquire data from the connected devices.

When the `Instrument Server` is started, a second `Data Server` is also started. This one collects data and is basically a frontend around a `hdf5 <https://www.h5py.org/>`_ binary data file. This allows for compact storing of the obtained data. Callbacks can be registered to update a gui of newly incoming data. 

`p5control` provides some qt widgets which are tailored to this structure. With this, it is easy to create a gui application live plotting incoming data.

Chapters
--------

.. toctree::
    :maxdepth: 1

    driver
    inserv
