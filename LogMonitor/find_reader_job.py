import JoeAgent
from JoeAgent import job, event, timer, simple, message
from JoeAgent.agent import MessageSendEvent, MessageReceivedEvent, \
                           OkResponse, DeniedResponse
import LogReader
import find_log_job

import os, os.path
import logging

log = logging.getLogger("agent.LogMonitor")

FIND_READER_TIMEOUT = 8.0

class CheckForReadersEvent(event.Event): pass

class CheckForReaderTimer(timer.Timer):
    """This is a timer for finding a LogReader to read our file"""
    def __init__(self, source):
        evt = CheckForReadersEvent(source)
        timer.Timer.__init__(self, FIND_READER_TIMEOUT, evt)

class FindReaderJob(job.Job):
    """The FindReaderJob finds LogReader agents to read files that have
    been updated.
       """
       
    def __init__(self, agent_obj):
        job.Job.__init__(self, agent_obj)

        self._needs_reading = []  # List of files that need reading

        self._reader_requests = {} # Hash of readers who are being contacted
                                   # to see if they are availabel to read.
                                   # the key is a message key.

        self._reading_files = {}  # Hash of files that are being read.
                                  #   the key is the agent name who is reading

        self._dir_key = None
        self._timer = None

    def setNeedsReader(self):
        if self._timer is None:
            self._timer = CheckForReaderTimer(self)
            self.getAgent().addTimer(self._timer)

    def setNoNeedsReader(self):
        "Stop timer if it exists"
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def notify(self, evt):
        # Process to find a reader:

        #  Step 1 - We recieve a LogNeedsReadEvent
        #   this indicates a log file needs to be read. We start up the
        #   poll for availabale readers process by generating a 
        #   CheckForReadersEvent. 

        #  Step 2 - We handle a CheckForReadersEvent
        #   This event starts the sequence of events necessary to find an
        #   available LogReader agent. We will need to get a list of all the
        #   agents in the network (by asking the director). So we send
        #   a StatusRequest to the director. Also we set a timer to check
        #   again for readers.
        
        #  Step 3 - Handle response from Director
        #   The message key for our status request to the director is stored
        #   in self._dir_key. We match to get our response and then go through
        #   our list of agents to find any LogReader agents. We will send
        #   StatusRequest messages to each of the LogReader agents, and store
        #   the key in a hash self._reader_requests

        #  Step 4 - Handle response from LogReader agent
        #   LogReader StatusResponse key should be stored in 
        #   self._read_requests hash. If the response has a state that is not
        #   ReadingState, we will pop off a file that needs reading and send
        #   a ReadLogRequest to the LogReader. We will record who is reading
        #   the file in a hash keyed on LogReader name.

        #  Step 5 - Handle response from ReadLogRequest
        #   We will receive either a OkResponse or a DeniedResponse. If Denied,
        #   we need to put the file back on the needs_reading list and make
        #   sure the timer is still going. If OkResponse, we dont' have to
        #   do anything.

        #  Step 6 - Handle a ReadLogCompleteMessage from the LogReader agent.
        #   Match the agent up to teh file it was supposed to be reading.
        #   Remove the log file from the list of logs we are reading.
        #   Generate a LogReadCompleteEvent to inform the monitor we are done.

        if isinstance(evt, find_log_job.LogNeedsReadEvent):
            #  Step 1 - We recieve a LogNeedsReadEvent
            if len(self._needs_reading) == 0:
                self.getAgent().addEvent(CheckForReadersEvent(self))
            self._needs_reading.append(evt.getLogPath())
        elif isinstance(evt, CheckForReadersEvent):
            #  Step 2 - We handle a CheckForReadersEvent
            log.debug("Checking for readers")
            msg = simple.StatusRequest()

            assert self._dir_key == None
            self._dir_key = msg.getKey()

            # We may have a latent CheckForReaderTimer events even after all
            # the logs have been handled. We will just do nothing in that case
            if len(self._needs_reading) > 0:
                self.setNeedsReader()

                conn = self.getAgent().getConnection("Director")
                if conn is None:
                    log.error("Connection to Director not found")
                    return
                self.getAgent().addEvent(MessageSendEvent(self, msg, conn))
            else:
                self.setNoNeedsReader()

        elif isinstance(evt, MessageReceivedEvent) and \
             isinstance(evt.getMessage(), message.Response) and \
             self._dir_key == evt.getMessage().getRequestKey():
            #  Step 3 - Handle response from Director
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
             isinstance(evt.getMessage(), message.Response) and \
            self._reader_requests.has_key(evt.getMessage().getRequestKey()):
            #  Step 4 - Handle response from LogReader agent
                reader = self._reader_requests[evt.getMessage().getRequestKey()]
                source = evt.getSource()
                del self._reader_requests[evt.getMessage().getRequestKey()]

                log.debug("Received status response from %s" % reader.getName())
                if isinstance(evt.getMessage().getState(), 
                              LogReader.agent.ReadingState):
                    log.debug("Reader %s is already reading" % reader.getName())
                else:
                    log.debug("Reader %s is free for reading a logfile" 
                               % reader.getName())
                    req = LogReader.agent.ReadLogRequest()
                    req.setLogPath(self._needs_reading.pop())
                    evt = MessageSendEvent(self, req, source)
                    self.getAgent().addEvent(evt)
                    self._reading_files[source.getAgentInfo().getName()] = \
                           req.getLogPath()

        elif isinstance(evt, MessageReceivedEvent) and \
             isinstance(evt.getMessage(), message.Response) and \
             self._reading_files.has_key(
                            evt.getSource().getAgentInfo().getName()):
            #  Step 5 - Handle response from ReadLogRequest
            reader_name = evt.getSource().getAgentInfo().getName()
            if isinstance(evt.getMessage(), OkResponse):
                # We are good to go
                log.debug("Reader %s is responded ok for reading %s" % 
                            (reader_name, self._reading_files[reader_name]))
            elif isinstance(evt.getMessage(), DeniedResponse):
                log.error("Reading %s denied request to read %s" % 
                          (reader_name, self._reading_files[reader_name]))
                file_name = self._reading_files[reader_name]
                del self._reading_files[reader_name]
                self._needs_reading.append(file_name)
                self.setNeedsReader()
            else:
                raise Exception("Unknown response for reader")

        elif isinstance(evt, MessageReceivedEvent) and \
             isinstance(evt.getMessage(), 
                        LogReader.agent.ReadLogCompleteMessage):
            #  Step 6 - Handle a ReadLogCompleteMessage from the 
            #           LogReader agent.
            reader_name = evt.getSource().getAgentInfo().getName()
            reader_file = self._reading_files[reader_name]
            log.debug("Reader %s finished reading %s" % 
                      (reader_name, reader_file))

            del self._reading_files[reader_name]

            evt = find_log_job.LogReadCompleteEvent(self, reader_file)
            self.getAgent().addEvent(evt)

