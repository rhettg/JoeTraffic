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

