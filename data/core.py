
import pygame,enum
pygame.init()
from data.system.api import Api
from data.system import events, errors, network
from data.managers.emittersManager import EmittersManager
from data.common.runnable import Runnable
from data.managers import idManager,inputManager
from data.sprites import aliveObject



class Core(idManager.IDManager,Api,events.EventManager,errors.ErrorManager):
    cycles = 0
    @staticmethod
    def objectCreatedEventTemplate(id:str,objectType:str):
        return pygame.event.Event(events.EventRegister.getID("objectCreated"),locals())

    @staticmethod
    def objectRemovedEventTemplate(id:str,objectType:str):
        return pygame.event.Event(events.EventRegister.getID("objectRemoved"),locals())

    @ staticmethod
    def cycleEndedEventTemplate(cycles:int):
        return pygame.event.Event(events.EventRegister.getID("cycleEnded"),locals())

    @staticmethod
    def clientConnectedEventTemplate(clientID:str):
        return pygame.event.Event(events.EventRegister.getID("clientConnected"),locals())

    @staticmethod
    def clientDisconnectedEventTemplate(clientID:str):
        return pygame.event.Event(events.EventRegister.getID("clientDisconnected"),locals())

    objectCreatedEvent = events.EventRegister.register("objectCreated",objectCreatedEventTemplate)

    objectRemovedEvent = events.EventRegister.register("objectRemoved",objectRemovedEventTemplate)

    cyclesEndedEvent = events.EventRegister.register("cycleEnded",cycleEndedEventTemplate)

    clientConnectedEvent = events.EventRegister.register("clientConnected",clientConnectedEventTemplate)

    clientDisconnectedEvent = events.EventRegister.register("clientDisconnected",clientDisconnectedEventTemplate)

    class Mode(enum.Enum):
        start = 0
        join = 1
        host = 2

    def __init__(self):
        self.sprites = {}
        self.emittersManager = EmittersManager(self)
        
        events.EventManager.__init__(self)
        idManager.IDManager.__init__(self,self.sprites)
        self.inputMangers = {}
        self.running = True
        self.userID = "main"
        self.mode = self.Mode.start
        self.network = None
        self.addInputManager(self.userID)
        # pygame.display.set_caption(f"WorldSpawn Code:{self.ip}")
        # pygame.display.set_icon(pygame.image.load(default.resource_path("assets/gui/world_icon.png")))
        Api.__init__(self)
        self.setStartMode()
        

    def updateInput(self):
        pass


    def endCycle(self):
        self.addEvent(self.cycleEndedEventTemplate(self.cycles))
        self.cycles += 1

    def addInputManager(self,id):
        self.inputMangers[id] = inputManager.InputManager()

    def setRawInput(self,id,rawEvents,rawKeys,mousePos):
        self.inputMangers[id].setRawInput(rawEvents,rawKeys, mousePos)

    def setInput(self,id,events,keys,mousePos):
        self.inputMangers[id].setInput(events,keys, mousePos)

    def getInputManager(self,id) -> inputManager.InputManager:
        return self.inputMangers[id]

    def getInput(self):
        rawEvents = pygame.event.get()
        self.convertEventList(rawEvents)
        rawKeys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pos()
        local = self.inputMangers.get(self.userID)
        if local != None:
            local.setRawInput(rawEvents,rawKeys,mouse)
    
    def setStartMode(self):
        pygame.display.set_caption(f"WorldSpawn")
        self.mode = self.Mode.start

    def clientUpdate(self):
        for package in self.packages.values():
            package.core.clientUpdate(self)
    def serverUpdate(self):
        for package in self.packages.values():
            package.core.serverUpdate(self)

    def update(self):
        for object in list(self.sprites.values()):
            if object.main():
                self.removeObject(object)
        
    def clearEvents(self):
        super().clearEvents()
        for object in list(self.sprites.values()):
            object.clearEvents()
        for inp in self.inputMangers.values():
            inp.clearEvents()

    def getObjectByPrefabPath(self,prefabPath:str):
        prefab,name = prefabPath.split(".")
        return self.getters[prefab].get(name)

    def addObjectByID(self, object:Runnable, id):
        domainName = object.domain
        prefabName = object.prefab
        domain = self.getDomain(domainName)
        addFunction = domain.settings["add-function"]
        exec(addFunction,globals(),locals())
        self.addObjectToGroupById(object,id,domainName)
        self.addObjectToGroupById(object,id,prefabName)
        self.addEvent(self.objectCreatedEventTemplate(id,object.module))
        

    def addObjectToGroupById(self,object:Runnable,id:str,groupName:str):
        try:
            groupDict = getattr(self,groupName)
            groupDict[id] = object
        except:
            pass
    def removeObjectToGroupById(self,id:str,groupName:str):
        try:
            groupDict:dict = getattr(self,groupName)
            object = groupDict.pop(id)
        except:
            pass
        
    
    def removeObjectByID(self, id):
        object = self.getObject(id)
        domainName = object.domain
        prefabName = object.prefab
        domain = self.getDomain(domainName)
        removeFunction = domain.settings["remove-function"]

        exec(removeFunction, globals(),locals())
        self.removeObjectToGroupById(id,domainName)
        self.removeObjectToGroupById(id,prefabName)
        self.emittersManager.removeObject(object)
        self.addEvent(self.objectRemovedEventTemplate(id,object.module))

    def getAliveObjects(self):
        aliveObjects = {}
        for type in self.GroupsByBases.keys():
            if issubclass(type,aliveObject.AliveObject):
                aliveObjects = aliveObjects | self.GroupsByBases[type]
        return aliveObjects

    def main(self):
        while self.running:
            self.getInput()
            if self.eventWillHappen("timer"):
                if self.eventHappened(pygame.QUIT):
                    self.running = False
                if self.mode == self.Mode.join:
                    self.clientNetworkUpdate()
                else:
                    self.update()
                    if self.mode == self.Mode.host:
                        self.hostUpdate()
                player = self.getObject(self.userID)
                if player != None:
                    self.emittersManager.update(player,True)
                self.clearEvents()
                self.endCycle()
            pygame.time.wait(1)
    
    def encryptIp(self,ip):
        cryptedIp = ""
        for char in ip:
            cryptedIp += self.ipCryptKey[char]
        return cryptedIp

    def decryptIp(self,cryptedIp):
        ip = ""
        for char in cryptedIp:
            ip += self.ipCryptKey[char]
        return ip
    
    def host(self,port:int):
        self.network = network.HostNetwork(port)
        self.mode = self.Mode.host
        pygame.display.set_caption("WorldSpawn - hosting")

    def join(self,ip:str,port:int) -> bool:
        try:
            self.network = network.ClientNetwork(ip,port)
        except OSError as e:
            self.raiseError("connectionFailed",str(e))
            return False
        self.mode = self.Mode.join
        pygame.display.set_caption("WorldSpawn - client")
        return True

    def buildSnapshot(self) -> dict:
        sprites = {}
        for id,object in list(self.sprites.items()):
            sprites[id] = {"prefabPath":object.prefabPath,"data":object.toData()}
        return {"type":"snapshot","sprites":sprites}

    def applySnapshot(self,snapshot:dict) -> None:
        seen = snapshot["sprites"]
        for id in list(self.sprites.keys()):
            if id not in seen:
                self.removeObjectByID(id)
        for id,entry in seen.items():
            object = self.sprites.get(id)
            if object == None:
                cls = self.getObjectByPrefabPath(entry["prefabPath"])
                if cls == None:
                    continue
                rect = entry["data"]["rect"]
                object = cls(self,(rect["x"],rect["y"],rect["dimension"]))
                self.addObjectByID(object,id)
            data = dict(entry["data"])
            currentAnimation = data.pop("currentAnimation",None)
            rect = data["rect"]
            object.fromDict(data)
            object.pos = (rect["x"],rect["y"],rect["dimension"])
            if currentAnimation != None:
                object.loadAnimation(currentAnimation)

    def hostUpdate(self):
        while not self.network.messages.empty():
            clientID,message = self.network.messages.get()
            if message["type"] == "connected":
                self.addInputManager(clientID)
                self.network.sendTo(clientID,{"type":"welcome","clientID":clientID})
                self.addEvent(self.clientConnectedEventTemplate(clientID))
            elif message["type"] == "disconnected":
                self.inputMangers.pop(clientID,None)
                self.addEvent(self.clientDisconnectedEventTemplate(clientID))
            elif message["type"] == "input":
                self.setInput(clientID,[],message["keys"],message["mouse"])
        self.serverUpdate()
        self.network.broadcast(self.buildSnapshot())

    def clientNetworkUpdate(self):
        if not self.network.connected:
            self.raiseError("disconnected","lost connection to host")
            self.network = None
            self.setStartMode()
            return
        localInput = self.inputMangers.get(self.userID)
        if localInput != None:
            self.network.send({"type":"input","keys":list(localInput.keys),"mouse":list(localInput.mousePos)})
        snapshot = None
        while not self.network.messages.empty():
            message = self.network.messages.get()
            if message["type"] == "welcome":
                oldManager = self.inputMangers.pop(self.userID,None)
                self.userID = message["clientID"]
                self.inputMangers[self.userID] = oldManager if oldManager != None else inputManager.InputManager()
            elif message["type"] == "snapshot":
                snapshot = message
        if snapshot != None:
            self.applySnapshot(snapshot)
        self.clientUpdate()