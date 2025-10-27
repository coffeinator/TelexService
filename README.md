# TelexService

A service server for the i-telex network.

## schema
txservice.py starts a server listening on port (given by config-file or command line argument).
When it's accepting a connection, it starts a subprocess (method in given module) which will handle the connection.
The given module is derived from txServiceProvider_base, which at first will start a new thread which will handle the i-telex-protocol-connection to the calling teletype.
After this it will call the handler of the derived provider, where the main behaviour of the service provider will happen.

## config file
```ini
[server]
# TCP port where the server listens
port=20260
# maximum concurrent connections
maxConcurrent=10

[provider]
# python module of the service provider
module=txServiceProvider_example
# WRU ID of this service
WRU=12345 txss d

[logging]
level='INFO'
```

## command line arguments
- -h/--help: shows help text
- -c/--config: specifies a config file
- -p/--port: TCP port where the server listens
- --conn: Maximum concurrent connections
- --wru: Give an artificial WRU id to the service
- -m/--module: Specifies the python-module with the service provider for this server instance
- -l/--loglevel

Command line arguments overrides the config file. So if there is a port given by the config-file and also by command line argument, the resulting port will be the one from the command line.

## multiple services
If you want to run different services on one machine,
you can simply specify in the config file which module has to be used.
In the .service-file you can then add the argument -c followed by the config file.


## Write your own service
Have a look at txServiceProvider_example. It's easy!

Hint: For the main part of writing a service, you don't need to run it as a full service. Just run the txServiceProvider_….py, it will then import the _debug.py which provides the most used methods. So you can run and test the service in the console.

After this you can copy and edit the conf-file for your purpose. Also don't forget to adapt the .service-file  ;)




