from JoeAgent import xobject

class AgencyConfig(xobject.XMLObject):
    def __init__(self, agents = None):
        self.agents = []
        if agents is not None:
            self.agents = agents
    def getAgents(self):
        return self.agents

