# JoeTraffic - Web-Log Analysis Application utilizing the JoeAgent Framework.
# Copyright (C) 2004 Rhett Garber

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

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
