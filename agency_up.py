#!/usr/bin/python
import sys, os
import logging
from xml.sax import saxutils, handler, make_parser, xmlreader
from xml.sax.expatreader import ExpatParser
from xml.sax.handler import feature_namespaces

from JoeAgent import utils, agent, simple

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

class ConfHandler(handler.ContentHandler):
    def __init__(self):
        handler.ContentHandler.__init__(self)

        self.director_conf = None
        self.in_property = None
        self.in_agent = False
        self.contents = ""

        self.agents = []

        self.cur_conf = None   # Current AgentConfig
        self.cur_cls = None    # Current class for the agent
        self.cur_log = None    # Current logfile name for the agent

    def getAgentTuples(self):
        """Return a list of tuples (AgentClass, logfile name, AgentConfig)"""
        return self.agents

    def startElement(self, name, attrs):
        if name == 'agency_conf':
            return
        elif name == 'agent':
            self.in_agent = True
            if attrs.has_key('class'):
                self.cur_cls = utils.get_class(attrs['class'])
            if issubclass(self.cur_cls, simple.SubAgent):
                if attrs.has_key('config_class'):
                    self.cur_conf = utils.get_class(attrs['config_class'])()
                else:
                    # default config class is SubAgentConfig
                    self.cur_conf = simple.SubAgentConfig()
                assert self.director != None, "Director was not specified"
                self.cur_conf.setDirectorConfig(self.director)
            else:
                self.cur_conf = agent.AgentConfig()
        elif name in ['name', 'address', 'port', 'logfile'] or \
              (self.cur_conf is not None and \
              name in self.cur_conf.__dict__.keys()):
            self.in_property = name
        else:
            raise Exception("Error parsing %s, not in config %s" 
                            % (name, str(self.cur_conf)))

    def endElement(self, name):
        assert self.in_property == name or name in ['agency_conf', 'agent'], \
               "Should be ending %s, but we are ending %s" \
                % (self.in_property, name)
        if name == 'agency_conf':
            # Done Parsing
            return
        elif name == 'agent':
            # Done getting agent params
            self.agents.append((self.cur_cls, self.cur_log, self.cur_conf))
            self.cur_cls = None
            self.cur_config = None
            self.cur_log = None
            self.in_agent = False
        elif name == 'name':
            assert self.in_agent, \
                   "Invalid property outside of a agent definition"
            self.cur_conf.setName(self.contents)
            if self.contents == 'Director':
                self.director = self.cur_conf
            self.contents = ""
            self.in_property = None
        elif name == 'address':
            assert self.in_agent, \
                   "Invalid property outside of a agent definition"
            self.cur_conf.setBindAddress(self.contents)
            self.contents = ""
            self.in_property = None
        elif name == 'port':
            assert self.in_agent, \
                   "Invalid property outside of a agent definition"
            self.cur_conf.setPort(int(self.contents))
            self.contents = ""
            self.in_property = None
        elif name == 'logfile':
            assert self.in_agent, \
                   "Invalid property outside of a agent definition"
            self.cur_log = self.contents
            self.contents = ""
            self.in_property = None
        elif self.cur_conf is not None and \
              name in self.cur_conf.__dict__.keys():
            setattr(self.cur_conf, name, self.contents) 
            self.in_property = None
            self.contents = ""
        else:
            assert 0, "Should not have been parsing %s" % name

    def characters(self, ch):
        if self.in_property is not None:
            self.contents += ch

if __name__ == '__main__':
    try:
        file = open(CONF_FILE, 'r')
    except IOError, e:
        print "Error opening file %s: %s" % (CONF_FILE, str(e))
        sys.exit(1)

    parser = make_parser()
    parser.setFeature(feature_namespaces, 0)
    conf_hndl = ConfHandler()
    parser.setContentHandler(conf_hndl)

    run_agent = None
    if len(sys.argv) > 1:
        run_agent = sys.argv[1]

    try:
        parser.parse(file)
    except Exception, e:
        print "Error parsing %s: %s" % (CONF_FILE, str(e))
        sys.exit(1)
    file.close()

    log = setup_logger("log/agency_up.log")
    log.debug("Starting agents")
    for a in conf_hndl.getAgentTuples():
        if run_agent is not None and run_agent != a[AGENT_CONF].getName():
            continue
        print "Starting %s on %s:%d (see %s)" % (a[AGENT_CONF].getName(),
                                        a[AGENT_CONF].getBindAddress(),
                                        a[AGENT_CONF].getPort(),
                                        a[AGENT_LOG])
        log.debug("Starting %s" % (a[AGENT_CONF].getName()))
        pid = os.fork()
        if pid == 0:
            try:
                # Child
                #os.close(1)
                #os.close(2)
                #os.close(3)

                log = setup_logger(a[AGENT_LOG])
                log.debug("Starting")
                try:
                    my_agent = a[AGENT_CLS](a[AGENT_CONF])
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
