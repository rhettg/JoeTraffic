from JoeAgent import job, event

import db_interface

import os, os.path
import logging
import log_parser

LINEINCR = 30 

log = logging.getLogger("agent.LogReader")

class ReadLogEvent(event.Event):
    """Event to indicate that we should read the file specified"""
    def __init__(self, source, logfile):
        event.Event.__init__(self, source)
        self._logfile = logfile

    def getLog(self):
        return self._logfile

class ReadLogCompleteEvent(event.Event):
    """Event to indicate the file is completely read. This event will
       be caught by the FindLogJob that is watching it. The file will
       continue to be checked for modifications"""
    pass

class ReadLogContinueEvent(event.Event):
    """Event to indicate we should continue reading the file. Log file
       processing will be done in chunks so as not to block the agent for
       too long."""
    pass

class ReadLogJob(job.Job):
    def __init__(self, agent_obj, logfile):
        job.Job.__init__(self, agent_obj)
        assert os.path.isfile(logfile), "Not a file: %s" % str(logfile)
        self._log_size = os.stat(logfile).st_size
        log.debug("Log size is %d" % self._log_size)

        self._logfile_path = logfile
        self._logfile_hndl = open(logfile, 'r')

        self._progress = 0  # Data read from file
        self._db = db_interface.getDB()

    def getFilePath(self):
        return self._logfile_path

    def getBytesRead(self):
        return self._progress
    def getBytesTotal(self):
        return self._log_size

    def run(self):
        evt = ReadLogContinueEvent(self)
        self.getAgent().addEvent(evt)

    def notify(self, evt):
        job.Job.notify(self, evt)
        if isinstance(evt, ReadLogContinueEvent) and evt.getSource() == self:
            log.debug("Continuing read of file")
            # Continue to read the log
            try:
                self._progress += log_parser.read_log(
                                      self._logfile_hndl, self._db, LINEINCR)
                log.debug("Read %d %% of file (%d / %d)" % (self.getProgress(),
                                                            self._progress,
                                                            self._log_size))

            except log_parser.EndOfLogException, e:

                self._progress = self._log_size

                # Log file is complete, updated the db entry
                self._mark_complete()

                # Add an event to notify that the file is complete
                self._logfile_hndl.close()
                new_evt = ReadLogCompleteEvent(self)
                self.getAgent().addEvent(new_evt)
            except log_parser.InvalidLogException, e:
                log.warning("Invalid log file: %s" % str(e))
                self._logfile_hndl.close()
                new_evt = ReadLogCompleteEvent(self)
                self.getAgent().addEvent(new_evt)

            else:
                # Add an event to continue reading
                new_evt = ReadLogContinueEvent(self)
                self.getAgent().addEvent(new_evt)

    def _update_db(self):
        """Update the entry in the database for this logfile"""
        log.debug("Updating file %s" % self._logfile_path)
        pass

    def _mark_invalid(self):
        """Update the database to indicate that this is not a valid log file"""
        log.debug("Marking file %s invalid" % self._logfile_path)
        pass

    def _mark_complete(self):
        log.debug("Marking file %s complete" % self._logfile_path)
        pass

    def getProgress(self):
        """Return a percentage complete value"""
        if self._log_size == 0:
            return 0
        return int((float(self._progress) / self._log_size) * 100)
