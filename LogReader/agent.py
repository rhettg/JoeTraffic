import logging, string, os, os.path
from JoeAgent import simple, event, job
import read_job, find_log_job

log  = logging.getLogger("agent.LogReader")

MAX_READERS = 1
class LogReaderJob(job.Job):
    """Job to coordinate checking directories and reading of logs"""
    def __init__(self, agent_obj):
        job.Job.__init__(self, agent_obj)
        self._wait_readers = []     # List of waiting log readers
        self._active_readers = []   # List of active log readers
        self._checkers = []  # List of active directory checkers

    def getReaderProgress(self):
        status_hash = {}
        for j in self._active_readers:
            status_hash[j.getFilePath()] = j.getProgress()
        for j in self._wait_readers:
            status_hash[j.getFilePath()] = j.getProgress()
        return status_hash

    def getCheckerProgress(self):
        status_hash = {}
        for c in self._checkers:
            status_hash[c.getDirectory()] = c.getNumFiles()
        return status_hash

    def run(self):
        # Setup all our directory checkers
        for dir in string.split(self.getAgent().getConfig().getPath(), ';'):
            if os.path.isdir(dir):
                log.info("Monitoring directory %s" % dir)
                check_job = find_log_job.FindLogJob(self.getAgent(), dir)
                self._checkers.append(check_job)
                self.getAgent().addListener(check_job)
                check_job.run()
            else:
                log.warning("Path %s is not valid" % dir)
    def notify(self, evt):                        
        job.Job.notify(self, evt)

        # This job is going to listen for ReadLogEvents and spawn ReadLogJobs
        if isinstance(evt, read_job.ReadLogEvent):
            log.debug("Creating job to read logfile %s" % evt.getLog())
            reading_job = read_job.ReadLogJob(self.getAgent(), evt.getLog())
            if len(self._active_readers) >= MAX_READERS:
                self._wait_readers.append(reading_job)
            else:
                self._active_readers.append(reading_job)
                self.getAgent().addListener(reading_job)
                reading_job.run()
        elif isinstance(evt, read_job.ReadLogCompleteEvent):
            # Reading of log is complete, remove the file from the list
            # and pick a new one to run if available
            log.debug("Completed reading %s, removing from active list" %
                       evt.getSource().getFilePath())
            self._active_readers.remove(evt.getSource())
            if len(self._wait_readers) > 0:
                reader = self._wait_readers.pop()
                self._active_readers.append(reader)
                self.getAgent().addListener(reader)
                reader.run()

class LogReaderConfig(simple.SubAgentConfig):
    def __init__(self):
        simple.SubAgentConfig.__init__(self)
        self.reader_path = ""
    def getPath(self):
        return self.reader_path

class LogReaderAgent(simple.SubAgent):
    def __init__(self, config):
        self._reader = None
        simple.SubAgent.__init__(self, config)

    def getInitJobs(self):
        self._reader = LogReaderJob(self)
        return simple.SubAgent.getInitJobs(self) + \
            [self._reader]

    def getInitEvents(self):
        return simple.SubAgent.getInitEvents(self) + \
               [job.RunJobEvent(self, self._reader)]

    def getStatusResponse(self, key):
        resp = simple.SubAgent.getStatusResponse(self, key)
        details = ""
        for logfile, progress in self._reader.getReaderProgress().iteritems():
            details += "Reading %s: %s%%\n" % (logfile, progress)
        for dir, files in self._reader.getCheckerProgress().iteritems():
            details += "Monitoring %s: %s files\n" % (dir, files)

        resp.setStatusDetails(details)  

        return resp
