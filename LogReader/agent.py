import logging, string, os, os.path
from JoeAgent import simple, event, job, message
import read_job
from JoeAgent.agent import RunningState, MessageSendEvent, MessageReceivedEvent

log  = logging.getLogger("agent.LogReader")

class ReadingState(RunningState): 
    def getName(self):
        return "Reading State"

class ReadLogRequest(message.Request):
    def __init__(self):
        message.Request.__init__(self)
        self.log_path = ""
    def setLogPath(self, path):
        self.log_path = path
    def getLogPath(self):
        return self.log_path

class ReadLogCompleteMessage(message.Message):
    def __init__(self):
        message.Message.__init__(self)
        self.log_path = ""
    def setLogPath(self, path):
        self.log_path = path
    def getLogPath(self):
        return self.log_path

MAX_READERS = 1
class LogReaderJob(job.Job):
    """Job to spawn a job to read a log file when asked by a ReadLogMessage"""
    def __init__(self, agent_obj):
        job.Job.__init__(self, agent_obj)
        self._reader = None

    def getReaderProgress(self):
        status_hash = {}
        if self._reader is not None:
            status_hash[self._reader.getFilePath()] = self._reader.getProgress()
        return status_hash

    def notify(self, evt):                        
        job.Job.notify(self, evt)

        # This job is going to listen for ReadLogEvents and spawn ReadLogJobs
        if isinstance(evt, MessageReceivedEvent) and \
           isinstance(evt.getMessage(), ReadLogRequest):
            if self._reader is None:
                assert not isinstance(self.getAgent().getState(), ReadingState)

                log.debug("Creating job to read logfile %s" 
                          % evt.getMessage.getLogPath())
                reading_job = read_job.ReadLogJob(self.getAgent(), 
                                                evt.getMessage().getLogPath())
                self.getAgent().addListener(reading_job)
                self.getAgent().addEvent(job.RunJobEvent(reading_job))

                self._reader = reading_job
                self.getAgent().setState(ReadingState())

                msg = OkResponse()
                self.getAgent().addEvent(
                       MessageSendEvent(self, msg, evt.getSource()))
            else:
                # We are already reading
                msg = DeniedResponse()
                self.getAgent().addEvent(
                       MessageSendEvent(self, msg, evt.getSource()))

        elif isinstance(evt, read_job.ReadLogCompleteEvent):
            log.debug("Completed reading %s, removing from active list" %
                       evt.getSource().getFilePath())
            assert isinstance(self.getAgent().getState(), ReadingState)
            assert self._reader == evt.getSource()

            self.getAgent().dropListener(self._reader)
            self._reader = None
            self.getAgent().setState(RunningState())

class LogReaderConfig(simple.SubAgentConfig):
    def getAgentClass(self):
        return LogReaderAgent

class LogReaderAgent(simple.SubAgent):
    def __init__(self, config):
        self._reader = None
        simple.SubAgent.__init__(self, config)

    def getInitJobs(self):
        self._reader = LogReaderJob(self)
        return simple.SubAgent.getInitJobs(self) + \
            [self._reader]

    def getStatusResponse(self, key):
        resp = simple.SubAgent.getStatusResponse(self, key)
        details = ""
        for logfile, progress in self._reader.getReaderProgress().iteritems():
            details += "Reading %s: %s%%\n" % (logfile, progress)

        resp.setStatusDetails(details)  
        return resp
