from JoeAgent import simple, http, job, agent, director
from http_response import HTTPResponseJob

import logging
log = logging.getLogger("agent.WebReporterAgent")

class WebReporterConfig(simple.SubAgentConfig):
    def __init__(self):
        simple.SubAgentConfig.__init__(self)
        self.webaddress = ""
        self.webport = 0
    def getWebBindAddress(self):
        return self.webaddress
    def getWebPort(self):
        return int(self.webport)
    def getAgentClass(self):
        return WebReporterAgent

class WebReporterAgent(simple.SubAgent):
    def __init__(self, config):
        assert isinstance(config, WebReporterConfig), \
              "Incorrect config class: %s" % str(config.__class__)
        simple.SubAgent.__init__(self, config)
        log.debug("Creating HTTP Server socket %s:%d" % 
                  (config.getWebBindAddress(), config.getWebPort()))
        self.addConnection(http.HTTPServerConnection(
                       agent.create_server_socket(config.getWebBindAddress(), 
                                                  config.getWebPort())))
        self.addListener(HTTPResponseJob(self))
