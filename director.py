import JoeAgent.director
from JoeAgent import director

class JoeDirectorConfig(director.DirectorConfig):
    def getAgentClass(self):
        return JoeDirector

class JoeDirector(director.Director): pass
