#!/usr/bin/python
import sys, os
import logging
from xml.sax import saxutils, handler, make_parser, xmlreader
from xml.sax.expatreader import ExpatParser
from xml.sax.handler import feature_namespaces

import JoeAgent
from JoeAgent import utils, agent, simple, xobject
import director

CONF_FILE = "agency_up_conf.xml"

AGENT_CLS = 0
AGENT_LOG = 1
AGENT_CONF = 2

_file_hndl = None
def setup_logger(filename, logname = None):
    global _file_hndl

    if logname is None:
        log = logging.getLogger()
    else:
        log = logging.getLogger(logname)

    if _file_hndl is not None:
        # This handler has been setup before, probably in our parent 
        # process, we only want one file handle per log
        log.removeHandler(_file_hndl)

    _file_hndl = logging.FileHandler(filename)

    fmt = logging.Formatter(logging.BASIC_FORMAT)
    _file_hndl.setFormatter(fmt)

    log.addHandler(_file_hndl)


    log.setLevel(logging.DEBUG)
    return log

if __name__ == '__main__':

    log = setup_logger("log/agency_up.log", 'agency_up')

    try:
        file = open(CONF_FILE, 'r')
    except IOError, e:
        print "Error opening file %s: %s" % (CONF_FILE, str(e))
        sys.exit(1)
    
    config = xobject.load_object_from_file(file)
    file.close()


    director_info = None
    for a in config.getAgents():
        if a.getAgentClass() == director.JoeDirector:
            director_info = agent.AgentInfo()
            director_info.setName(a.getName())
            director_info.setHost(a.getBindAddress())
            director_info.setPort(a.getPort())
    if director_info is None:
        print "Director not specified"
        sys.exit(1)

    run_agent = None
    if len(sys.argv) > 1:
        run_agent = sys.argv[1]

    log.debug("Starting agents")
    for a in config.getAgents():
        if run_agent is not None and run_agent != a.getName():
            continue

        if isinstance(a, simple.SubAgentConfig):
            a.setDirectorInfo(director_info)

        print "Starting %s on %s:%d (see %s)" % (a.getName(),
                                        a.getBindAddress(),
                                        a.getPort(),
                                        a.getLoggingPath())
        log.debug("Starting %s" % (a.getName()))

        pid = os.fork()
        if pid == 0:
            try:
                # Child
                #os.close(1)
                #os.close(2)
                #os.close(3)

                log = setup_logger(a.getLoggingPath())
                log.debug("Starting %s" % str(a.getAgentClass()))
                try:
                    my_agent = a.getAgentClass()(a)
                    my_agent.run()
                except Exception, e:
                    log.exception("Exception caught while starting agent")
                    sys.exit(1)
                log.debug("Agent exiting")
                sys.exit(0)
            except SystemExit, e:
                log.info("Agent exiting")
            except:
                log.exception("Big Error")

            # This should exit
            break
