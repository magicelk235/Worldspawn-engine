from data.default import events,timer
import pygame,data.core
class Runnable(timer.Timer,events.EventManager):
    eventRegister = events.EventRegister
    
    def __init__(self,core):
        timer.Timer.__init__(self,core)
        events.EventManager.__init__(self)
        self.core = core
        self.updateable = True
        self.id = None
        self.idGroups:dict[str,function] = {}
    
    def updateIdGroups(self):
        if self.core.eventHappened(self.eventRegister.getID("objectCreated")):
            for event in self.core.getEventList(self.eventRegister.getID("objectCreated")):
                for name in list(self.idGroups.keys()):
                    if self.idGroups[name](event.id):
                        getattr(self,name).add(event.id)
        if self.core.eventHappened(self.eventRegister.getID("objectRemoved")):
            for event in self.core.getEventList(self.eventRegister.getID("objectRemoved")):
                for name in list(self.idGroups.keys()):
                    if self.idGroups[name](event.id):
                        getattr(self,name).add(event.id)
    def addIdGroup(self,name,checkFunc):
        self.idGroups[name] = checkFunc

    def addEvent(self,event):
        super().addEvent(event)
        self.core.addEvent(event)

    @ property
    def id(self):
        return self.id

    @ id.setter
    def id(self,id:str):
        self.id = id
    
    def main(self):
        if self.updateable:
            return self.update()

    def get(self,value:str|any):
        if isinstance(value,str):
            if value.startswith("@"):
                return getattr(self,value[1:])
        return value

    def update(self):
        self.updateIdGroups()