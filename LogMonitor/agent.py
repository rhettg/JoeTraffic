# JoeTraffic - Web-Log Analysis Application utilizing the JoeAgent Framework.
# Copyright (C) 2004 Rhett Garber

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import logging, string, os, os.path
from JoeAgent import simple, event, job
import find_log_job, find_reader_job

log  = logging.getLogger("agent.LogMonitor")

class LogMonitorJob(job.Job):
    """Job to coordinate checking directoriess"""
    def __init__(self, agent_obj):
        job.Job.__init__(self, agent_obj)
        self._checkers = []  # List of active directory checkers

    def getCheckerProgress(self):
        status_hash = {}
        for c in self._checkers:
            status_hash[c.getDirectory()] = c.getNumFiles()
        return status_hash

    def run(self):
        # Setup all our directory checkers
        for dir in self.getAgent().getConfig().getPaths():
            log.info("Monitoring directory %s" % dir)
            try:
                check_job = find_log_job.FindLogJob(self.getAgent(), dir)
                self._checkers.append(check_job)
                self.getAgent().addListener(check_job)
                check_job.run()
            except find_log_job.InvalidDirectoryException, e:
                log.warning("Invalid Directory: %s", str(e))

class LogMonitorConfig(simple.SubAgentConfig):
    def __init__(self):
        simple.SubAgentConfig.__init__(self)
        self.reader_paths = [] 
    def getPaths(self):
        return self.reader_paths
    def getAgentClass(self):
        return LogMonitorAgent


class LogMonitorAgent(simple.SubAgent):
    def __init__(self, config):
        self._mon_job = None
        simple.SubAgent.__init__(self, config)

    def getInitJobs(self):
        self._mon_job = LogMonitorJob(self)
        return simple.SubAgent.getInitJobs(self) + \
            [self._mon_job,
            find_reader_job.FindReaderJob(self)]

    def getInitEvents(self):
        return simple.SubAgent.getInitEvents(self) + \
               [job.RunJobEvent(self, self._mon_job)]

    def getStatusResponse(self, key):
        resp = simple.SubAgent.getStatusResponse(self, key)
        details = ""
        if self._mon_job is not None:
            for dir, files in self._mon_job.getCheckerProgress().iteritems():
                details += "Monitoring %s: %s files\n" % (dir, files)

        resp.setStatusDetails(details)  

        return resp
