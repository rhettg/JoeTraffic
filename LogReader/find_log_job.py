from JoeAgent import job, event, timer
import db_interface
import read_job

import os, os.path
import MySQLdb, logging

log = logging.getLogger("agent.LogReader")

LOG_TIMEOUT = 60.0

class CheckForLogsEvent(event.Event): pass

class CheckLogTimer(timer.Timer):
    def __init__(self, source):
        evt = CheckForLogsEvent(source)
        timer.Timer.__init__(self, LOG_TIMEOUT, evt)

class FindLogJob(job.Job):
    """The FindLogJob continuously polls a directory for new log files.
       It keeps track of log files in a database for persistence.
       """
       
    def __init__(self, agent_obj, directory):
        job.Job.__init__(self, agent_obj)
        if not os.path.isdir(directory):
            raise Exception("Not a dir: %s" % directory)

        self._dir = directory            # Directory to check for files
        self._db = db_interface.getDB()  # Handle to Database
        self._watch_files = []            # List of logs currently being read
        self._num_files = 0

    def getDirectory(self):
        return self._dir
    def getNumFiles(self):
        return self._num_files

    def run(self):
        evt = CheckForLogsEvent(self)
        self.getAgent().addEvent(evt)

    def notify(self, evt):
        if isinstance(evt, CheckForLogsEvent) and evt.getSource() == self:
            log.debug("Checking for new logs in %s" % self.getDirectory())
            # Get list of logs in directory
            logs = []
            for elem in os.listdir(self.getDirectory()):
                fullPath = os.path.join(self.getDirectory(), elem)
                if os.path.isfile(fullPath):
                    logs.append(fullPath)

            self._num_files = len(logs)

            # Check if we know anything about any of these logs
            check_logs = []
            for elem in logs:
                log.debug("Checking file %s" % elem)
                if elem not in self._watch_files and self._need_read(elem):
                    log.info("Found log file to be read: %s"  % elem)
                    check_logs.append(elem)

            # Create event for logs that need to be read
            for elem in check_logs:
                self._watch_files.append(elem)
                read_event = read_job.ReadLogEvent(self, elem)
                self.getAgent().addEvent(read_event)

            # Put a timer to check directory again
            self._timer = CheckLogTimer(self)
            self.getAgent().addTimer(self._timer)
        elif isinstance(evt, read_job.ReadLogCompleteEvent) and \
                evt.getSource().getFilePath() in self._watch_files:
            log.info("Should be done watching %s" 
                     % evt.getSource().getFilePath())            
            # TODO: Don't watch completed files
            #self._watch_files.remove(evt.getLog())

    def _need_read(self, logfile):
        "Check database and return True if we should be reading this log"
        return True
        cmd = "SELECT mtime, size, valid FROM log_file WHERE path = '%s'" \
               % (logfile)
        results = self._db.execute(cmd)
        if len(results) > 0:
            # We have an entry for this file, we should check whether it is
            # up to date or has been modified
            return False
        else:
            # We have never seen this file before
            return True
