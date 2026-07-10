from data.core import events
from data.common.attributeAccessor import AttributeAccessor
from data.managers.timeManager import TimeManager

class Runnable(TimeManager,events.EventManager,AttributeAccessor):
    eventRegister = events.EventRegister

    def getModel(self,start=0,end:int=None):
        path = self.__class__.__module__.split(".")
        path = path[start:end]
        return "/".join(path)

    @ property
    def name(self):
        return str(self.__class__.name)
    @ property
    def domain(self):
        return self.getModel(2,3)
    @ property
    def prefab(self):
        return self.getModel(3,4)
    @ property
    def module(self):
        return self.domain + self.prefab + self.name

    @ property
    def prefabPath(self):
        return f"{self.prefab}.{self.getModel(4,5)}"

    def __init__(self,core):
        TimeManager.__init__(self,core)
        events.EventManager.__init__(self)
        self.core = core
        self.updatable = True
        self.id = None
        self.idGroups:dict[str,callable] = {}

    @ property
    def updatable(self):
        return self._updatable
    @ updatable.setter
    def updatable(self,value):
        self._updatable = value



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
                        getattr(self,name).discard(event.id)
    def addIdGroup(self,name,checkFunc):
        self.idGroups[name] = checkFunc

    def addEvent(self,event):
        super().addEvent(event)
        self.core.addEvent(event)

    @ property
    def id(self):
        return self._id

    @ id.setter
    def id(self,id:str):
        self._id = id
    
    def main(self):
        if self.updatable:
            return self.update()

    def get(self,value):
        if isinstance(value,str):
            if value.startswith("@"):
                return getattr(self,value[1:])
        return value

    def update(self):
        self.updateIdGroups()