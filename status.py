#!/usr/bin/python
import socket, sys, logging
from JoeAgent import simple, agent, event, job
from JoeAgent.event import Event
from JoeAgent.job import Job, RunJobEvent

log = logging.getLogger("agent.status")

class StatusJob(Job):
    def __init__(self, agent_obj):
        Job.__init__(self, agent_obj)
        self.conn = None
        self.key = None

    def run(self):
        log.debug("Running Status job") 
        # Send Shutdown Request
        msg = simple.StatusRequest()
        self.key = msg.getKey()
        assert self.conn != None, "Connection should not be None"
        evt = agent.MessageSendEvent(self, msg, self.conn)
        self.getAgent().addEvent(evt)

    def notify(self, evt):
        Job.notify(self, evt)
        if isinstance(evt, simple.ConnectCompleteEvent):
            self.conn = evt.getConnection()
            self.run()
        elif isinstance(evt, agent.MessageReceivedEvent):
            if isinstance(evt.getMessage(), simple.StatusResponse) and \
               self.key == evt.getMessage().getRequestKey():
                print "Status Acknowledged"
                print str(evt.getMessage())
                self.getAgent().setState(agent.STOPPING)
            if isinstance(evt.getMessage(), agent.DeniedResponse) and \
               self.key == evt.getMessage().getRequestKey():
                print "Status Denied"
                self.getAgent().setState(agent.STOPPING)
        

def setup_logger(logname, filename):
    if logname != "":
        log = logging.getLogger(logname)
    else:
        log = logging.getLogger()
    hdler = logging.FileHandler(filename)
    fmt = logging.Formatter(logging.BASIC_FORMAT)
    hdler.setFormatter(fmt)
    log.addHandler(hdler)
    log.setLevel(logging.DEBUG)
    return log

if __name__ == "__main__":
    log = setup_logger("", "log/status.log")
    bind_addr = sys.argv[1]
    port = sys.argv[2]

    # Our simple configuration.
    # Note we are not setting address or port because we do not want to be a
    # server.
    config = agent.AgentConfig()
    config.setName("Status Command")

    # Configuration for the remote agent
    remote_config = agent.AgentConfig()
    remote_config.setBindAddress(bind_addr)
    remote_config.setPort(int(port))
    remote_config.setName("Remote Agent")

    # Create the agent
    command_agent = agent.Agent(config)

    # Create the jobs
    status_job = StatusJob(command_agent)
    connect_job = simple.ConnectJob(command_agent, remote_config)

    # Create an event that will start the job we want at run-time
    run_evt = RunJobEvent(command_agent, connect_job)
    command_agent.addEvent(run_evt)

    # Don't forget to add the jobs as listeners
    command_agent.addListener(status_job)
    command_agent.addListener(connect_job)
    command_agent.addListener(simple.HandlePingJob(command_agent))

    print "Running status"
    command_agent.run()

