from JoeAgent import job, event, timer

import os, os.path
import logging
#import db_interface

log = logging.getLogger("agent.LogMonitor")

LOG_TIMEOUT = 10.0

class CheckForLogsEvent(event.Event): pass

class LogNeedsReadEvent(event.Event): 
    def __init__(self, source, log_path):
        event.Event.__init__(self, source)
        self.log_path = log_path
    def getLogPath(self):
        return self.log_path

class LogReadCompleteEvent(event.Event):
    def __init__(self, source, log_path):
        event.Event.__init__(self, source)
        self.log_path = log_path
    def getLogPath(self):
        return self.log_path

class InvalidDirectoryException(Exception): pass

class CheckLogTimer(timer.Timer):
    """This is a timer for polling our directory for new or changed files.
    Each time this timer pops, the FindLogJob will check its directory"""
    def __init__(self, source):
        evt = CheckForLogsEvent(source)
        timer.Timer.__init__(self, LOG_TIMEOUT, evt)

class FindLogJob(job.Job):
    """The FindLogJob continuously polls a directory for new log files.
       TODO: It keeps track of log files in a database for persistence.

       Each FindLogJob will watch one directory.
       As new files are found (or files are updated), a LogNeedsReadEvent 
       will be generated. It is expected that a FindReaderJob will take
       care of the file from then on.

       When the FindLogJob receives a FileReadCompleteEvent, it will update
       the files status and then continue to watch the file for updates.
       """
       
    def __init__(self, agent_obj, directory):
        job.Job.__init__(self, agent_obj)
        if not os.path.isdir(directory):
            raise InvalidDirectoryException(directory)

        self._dir = directory            # Directory to check for files
        #self._db = db_interface.getDB()  # Handle to Database

        self._reading = [] # List of files being read (or waiting read)
        self._known_files = {}    # Hash of filename to size that we have
                                  # already processed

        self._num_files = 0

    def getDirectory(self):
        return self._dir
    def getNumFiles(self):
        return self._num_files

    def run(self):
        evt = CheckForLogsEvent(self)
        self.getAgent().addEvent(evt)

    def _should_read(self, log_path):
        """Returns true if the file should be read.
        This means we are not currently reading the file and we don't 
        already have it in the queue for a reader."""
        if not self._known_files.has_key(log_path):
            log.debug("Found new file: %s" % log_path)
            return True
        #TODO: Handle updated files case
        #elif self._known_files[log_path] 
        return False

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
            for elem in logs:
                log.debug("Checking file %s" % elem)
                if self._should_read(elem):
                    self.getAgent().addEvent(LogNeedsReadEvent(self, elem))
                    self._known_files[elem] = 0
                    self._reading.append(elem)

            # Put a timer to check directory again
            self._timer = CheckLogTimer(self)
            self.getAgent().addTimer(self._timer)
        elif isinstance(evt, LogReadCompleteEvent):
            if evt.getLogPath() in self._reading:
                log.debug("File %s marked read completed" % elem)
                self._reading.remove(evt.getLogPath())

    # TODO: Finish
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
