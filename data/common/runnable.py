from data.system import events
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
        # a content class usually sets name itself, which shadows this; the
        # class name is the fallback for the ones that do not bother
        return self.__class__.__name__
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
        if not self.idGroups:
            return
        if self.core.eventHappened(self.eventRegister.getID("objectCreated")):
            for event in self.core.getEventList(self.eventRegister.getID("objectCreated")):
                for name in list(self.idGroups.keys()):
                    group = getattr(self,name,None)
                    if group != None and self.idGroups[name](event.id):
                        group.add(event.id)
        if self.core.eventHappened(self.eventRegister.getID("objectRemoved")):
            for event in self.core.getEventList(self.eventRegister.getID("objectRemoved")):
                # both event lists cover the same cycle and nothing records
                # which came first, so an id that was dropped and handed
                # straight to something else is still in the world and the
                # create pass above has already had its say about it
                if self.core.getObject(event.id) != None:
                    continue
                for name in list(self.idGroups.keys()):
                    # the object is gone, so its membership can no longer be
                    # tested - drop the id from every group
                    group = getattr(self,name,None)
                    if group != None:
                        group.discard(event.id)

    def addIdGroup(self,name,checkFunc):
        """Keep self.<name> as the ids the world holds that match checkFunc.

        Seeded straight away, because the group is otherwise fed only by the
        objectCreated event: everything that was already standing there when
        this object appeared would never be tested, and a sprite restored
        from a save appears into a world that is already full.
        """
        self.idGroups[name] = checkFunc
        group = getattr(self,name,None)
        if group == None:
            return
        for id in list(self.core.sprites.keys()):
            if id != self.id and checkFunc(id):
                group.add(id)

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
        # "@name" points at one of this object's attributes, and image data
        # writes dotted paths like "@directionX.value", so the lookup has to
        # walk the path the same way getAttr does
        if isinstance(value,str):
            if value.startswith("@"):
                return self.getAttr(value[1:])
        return value

    def update(self):
        self.updateIdGroups()