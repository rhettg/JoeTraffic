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

from JoeAgent import http, job
from http_status_response import HTTPStatusResponseJob

import logging
log = logging.getLogger("agent.WebReporterAgent")

class HTTPResponseJob(job.Job):
    ERROR_TEMPLATE = """
    <html>
      <head>
        <title>ERROR</title>
      </head>
      <h1>%(error_code)d Error</h1>
      <p>%(explain)s
    </html>
    """

    def notify(self, evt):
        job.Job.notify(self, evt)
        if isinstance(evt, http.HTTPRequestEvent):
            command = evt.getRequest().getCommand()
            path = evt.getRequest().getPath()

            log.debug("Recieved a %s request for %s (Version %s)" % 
                       (command, path,
                        evt.getRequest().getVersion()))

            response = None
            if command != "GET":
                log.debug("Unknown Command %s" % command)
                response = self.getError(405)
            else:
                if path == "/":
                    response = http.HTTPResponse(200, 
                             [http.Header('Content-type', 'text/html')], 
                             self.doRoot())
                elif path == "/status":
                    resp_job = HTTPStatusResponseJob(self.getAgent())
                    resp_job.setClientConnection(evt.getSource())
                    self.getAgent().addListener(resp_job)
                    resp_job.run()
                else:
                    log.debug("Unknown Path %s" % path)
                    response = self.getError(404)

            if response is not None:
                resp_evt = http.HTTPResponseEvent(self, response, 
                                                  evt.getSource())
                self.getAgent().addEvent(resp_evt)

    def doRoot(self):
        log.debug("Responding to Root HTTP request")
        return """
<html>
<h3>Welcome to StatusAgent</h3>
</html>
    """

    def getError(self, code):
        hash = {'error_code': code,
                'explain': http.HTTPResponse.MESSAGES[code]}
        return http.HTTPResponse(code, 
                                 [http.Header('Content-type', 'text/html')],
                                 self.ERROR_TEMPLATE % hash)

