from pygame import event,USEREVENT

class RegisteredEvent():
    def __init__(self,id,createFunction):
        self.id = id
        self.createFunction = createFunction

    @property
    def id(self):
        return self._id
    @id.setter
    def id(self,id):
        self._id = id

    def create(self):
        return self.createFunction

class EventRegister:
    nextID = USEREVENT
    registeredEvents = {}

    @classmethod
    def register(cls, name,createFunction):
        id = EventRegister.nextID
        EventRegister.nextID += 1
        EventRegister.registeredEvents[name] = RegisteredEvent(id,createFunction)
        return id

    @classmethod
    def getEvent(cls,name):
        return cls.registeredEvents[name]

    @classmethod
    def getID(cls, name):
        return cls.getEvent(name).id

    @classmethod
    def create(cls,name):
        return cls.getEvent(name).create() 

class EventManager:
    def __init__(self):
        self.nextEvents = {}
        self.currentEvents = {}

    @ staticmethod
    def getID(id:int|str) -> int:
        if isinstance(id,int):
            return id
        else:
            return EventRegister.getID(id)

    def addEvent(self,event:event.Event) -> None:
        eventID = event.type
        eventList = self.nextEvents.get(eventID,[])
        eventList.append(event)
        self.nextEvents[eventID] = eventList
    
    def eventHappened(self,eventID:int|str=-1) -> bool:
        eventID = self.getID(eventID)
        return eventID in self.currentEvents if eventID != -1 else len(self.currentEvents) > 0
        
    def eventWillHappen(self,eventID:int|str=-1):
        eventID = self.getID(eventID)
        return eventID in self.nextEvents if eventID != -1 else len(self.nextEvents) > 0

    def clearEvents(self) -> None:
        self.currentEvents,self.nextEvents = self.nextEvents,{}
        
    def getEventList(self,eventID:int|str) -> list[event.Event]:
        eventID = self.getID(eventID)
        return self.currentEvents.get(eventID,[])

    def convertEventList(self,events) -> None:
        for event in events:
            self.addEvent(event)
    
    def addBlankEvent(self):
        self.nextEvents[""] = []