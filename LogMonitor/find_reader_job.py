import JoeAgent
from JoeAgent import job, event, timer, simple
from JoeAgent.agent import MessageSendEvent, MessageReceivedEvent
import LogReader

import os, os.path
import logging

log = logging.getLogger("agent.LogMonitor")

FIND_READER_TIMEOUT = 10.0

class CheckForReadersEvent(event.Event): pass

class CheckForReaderTimer(timer.Timer):
    """This is a timer for finding a LogReader to read our file"""
    def __init__(self, source):
        evt = CheckForReadersEvent(source)
        timer.Timer.__init__(self, FIND_READER_TIMEOUT, evt)

class FindReaderJob(job.Job):
    """The FindLogJob continuously polls a directory for new log files.
       """
       
    def __init__(self, agent_obj):
        job.Job.__init__(self, agent_obj)
        if not os.path.isdir(directory):
            raise InvalidDirectoryException(directory)

        self._needs_reading = []  # List of files that need reading
        self._reading_files = []  # List of logs currently being read

        self._dir_key = None

    def notify(self, evt):
        if isinstance(evt, find_log_files.LogNeedsReadEvent):
            if len(self._needs_reading) == 0:
                self.getAgent().addEvent(CheckForReadersEvent(self))
            self._reading_files.append(evt.getLogPath())
        elif isinstance(evt, CheckForReadersEvent):
            log.debug("Checking for readers")
            msg = simple.StatusRequest()

            assert self._dir_key == None
            self._dir_key = msg.getKey()

            conn = self.getAgent().getConnection("Director")
            if conn is None:
                log.error("Connection to Director not found")
                return
            self.getAgent().addEvent(MessageSendEvent(self, msg, conn))
        elif isinstance(evt, MessageReceivedEvent) and \
             self._dir_key == evt.getMessage().getRequestKey():
            log.debug("Recieved response from director")
            self._dir_key = None
            readers = []
            for info in evt.getMessage().getAgentInfoList():
                if info.getClassName() == str(LogReader.agent.LogReaderAgent):
                    log.debug("Found LogReader %s" % info.getName())
                    readers.append(info)
            for r in readers:
                msg = simple.StatusRequest()
                self._reader_requests[msg.getKey()] = r
                self.getAgent().addEvent(MessageSendEvent(self, msg, r))
        elif isinstance(evt, MessageReceivedEvent) and \
            self._reader_requests.has_key(evt.getRequestKey()):
                reader = self._reader_requests[evt.getRequestKey()]
                del self._reader_requests[evt.getRequestKey()]

                log.debug("Received status response from %s" % reader.getName())
                if isinstance(evt.getMessage().getState(), LogReader.agent.ReadingState):
                    log.debug("Reader %s is already reading" % reader.getName())
                else:
                    log.debug("Reader %s is free for reading a logfile" 
                               % reader.getName())
                    # TODO: Do something about it
