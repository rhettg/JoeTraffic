from JoeAgent import simple, http, job, agent, director, timer, event, message

import logging
log = logging.getLogger("agent.WebReporterAgent")

STATUS_TIMEOUT = 5.0

class StatusTimeoutEvent(event.Event): pass

class StatusTimer(timer.Timer):
    def __init__(self, source):
        evt = StatusTimeoutEvent(source)
        timer.Timer.__init__(self, STATUS_TIMEOUT, evt)

class AgentElement:
    """Container for the various information we need to get status information
    from an agent"""
    def __init__(self, info):
        self.info = info        # AgentInfo instance (from Step 2)
        self.connection = None  # Connection object (from Step 4)
        self.key = None         # Request key (from Step 5)
        self.response = None    # StatusResponse (from Step 6)

class HTTPStatusResponseJob(job.Job):
    """This job will handle collecting all the status information for all the
       agents return by the director. This status information will be compiled
       and returned to the client in the selected format
       
       So this job consists of several steps:
           1. Request agent info objects from our Director
           2. Receive agent info objects
           3. Connect to each agent
           4. Complete connection to each agent 
           5. Send StatusRequests to each agent
           6. Retrieve StatusRequests from each agent
           7. Form HTTP response for client
           
       All this is going to have to happen within STATUS_TIMEOUT or a timer
       will pop and respond to the client. (skip to step 7)"""

    def __init__(self, agent_obj):
        job.Job.__init__(self, agent_obj)
        self.client = None     # The HTTP client we are responding to
        self.key = None        # The key for our director request

        self._status_reqs = {} # A hash table of our responses from agents
                               #   from AgentInfo (name)
                               #   to AgentElement

    def getClientConnection(self):
        return self.client
    def setClientConnection(self, client):
        self.client = client

    def run(self):
        """This job starts by sending a StatusRequest to the director. If the
           director isn't there, we respond with an error response"""

        log.debug("Running Status job")
        # STEP 1

        msg = simple.StatusRequest()
        self.key = msg.getKey()
        assert self.client != None, "Connection should not be None"
        dir_conn = None
        for c in self.getAgent().getConnections():
            if isinstance(c, agent.AgentConnection) and \
                c.getAgentInfo() is not None and \
                c.getAgentInfo().getName() == "Director":
                dir_conn = c
                break

        # Set a timer so we know to eventully give up on an agent
        # that doesn't respond to us
        self._status_timer = StatusTimer(self)
        self.getAgent().addTimer(self._status_timer)

        if dir_conn is not None:
            log.debug("Sending status request")
            evt = agent.MessageSendEvent(self, msg, dir_conn)
            self.getAgent().addEvent(evt)
        else:
            log.debug("Director info not found")
            err = self.get_error(204)
            resp_evt = http.HTTPResponseEvent(self, err)
            self.getAgent().addEvent(resp_evt)

    def notify(self, evt):

        # Error condition: StatusTimeout
        if isinstance(evt, StatusTimeoutEvent) and evt.getSource() == self:
            log.info("Timed out waiting for status responses")
            self._respond_to_client()
            self.getAgent().dropListener(self)

        elif isinstance(evt, agent.MessageReceivedEvent):
            # Step 2: Response from Director
            if isinstance(evt.getMessage(), director.DirectorStatusResponse) \
              and self.key == evt.getMessage().getRequestKey():
                log.debug(
                      "Received response from director, connecting to agents")
                # We have received our list of agents, now we have to get
                # a more detailed status from each one
                agnts = evt.getMessage().getAgentInfoList()

                for info in agnts: # + [evt.getSource().getAgentInfo()]:
                    # Step 3

                    if info == evt.getSource().getAgentInfo():
                        # Don't request status from Director again
                        continue

                    # Create elements in status hash
                    element = AgentElement(info)
                    self._status_reqs[info.getName()] = element

                    if info == self.getAgent().getInfo():
                        # This info object is for ourself
                        element.response = \
                                  self.getAgent().getStatusResponse(None)
                    else:
                        # send status requests
                        msg = simple.StatusRequest()
                        element.key = msg.getKey()
                        msg_evt = agent.MessageSendEvent(self, msg, info)
                                                     
                        self.getAgent().addEvent(msg_evt)

            # Step 6: Response from an Agent
            elif isinstance(evt.getMessage(), message.Response) and \
                  self._status_reqs.has_key(
                                    evt.getSource().getAgentInfo().getName()):

                log.debug("Received a resonse from an agent we are waiting on")
                element = self._status_reqs[
                                   evt.getSource().getAgentInfo().getName()]
                if isinstance(evt.getMessage(), simple.StatusResponse) and \
                   evt.getMessage().getRequestKey() == element.key:
                    # This is the reply from one of the agents we are looking
                    # for. 
                    assert element.response is None,\
                           "This status has already been set: %s" % \
                            str(evt.getMessage())
                    log.info("Received status response for %s" 
                             % element.info.getName())

                    element.response = evt.getMessage()

                elif evt.getMessage().getRequestKey() == element.key:
                    # This is not the response we were expecting
                    log.info(
                       "Agent unexpectedly responded to status request with %s" 
                        % str(evt.getMessage()))
                    del self._status_reqs[element.info.getName()]

                # Go through our list to see if we are stil waiting for any
                # more status responses
                still_waiting = False
                for e in self._status_reqs.values():
                    if e.response is None:
                        still_waiting = True
                
                if not still_waiting:
                    log.debug("Done waiting for status responses")
                    self._status_timer.stop()
                    self._respond_to_client()
                    self.getAgent().dropListener(self)
                else:
                    log.debug("Still looking for status responses")


    def _respond_to_client(self):
        rows = ""
        for element in self._status_reqs.values():
            dict = {}
            dict['name'] = element.info.getName()
            dict['address'] = element.info.getHost()
            dict['port'] = int(element.info.getPort())
            if element.response is not None:
                dict['state'] = element.response.getState().getName()
                dict['details'] = element.response.getStatusDetails()
            else:
                dict['state'] = 'Unreachable'
                dict['details'] = ''

            row = """
<tr>
 <td>
   <b>%(name)s</b>
 </td>
 <td>
   %(address)s:%(port)d
 </td>
 <td>
    %(state)s
 </td>
</tr>
<tr>
  <td colspan="3">
  <pre>
%(details)s
  </pre>
  </td>
</tr>
            """ % dict 
            rows += row

        tmplt = """
<html>
<h3>Agent Status</h3>
<center>
    <table border = "1">
        %s
    </table>
</center>
</html>
        """ % rows

        response = http.HTTPResponse(200, 
                 [http.Header('Content-type', 'text/html')], tmplt)

        resp_evt = http.HTTPResponseEvent(self, response, self.client)
        self.getAgent().addEvent(resp_evt)
