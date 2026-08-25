
import pygame,enum,uuid,json,os
import yaml
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

    @staticmethod
    def networkMessageEventTemplate(clientID:str,data):
        return pygame.event.Event(events.EventRegister.getID("networkMessage"),locals())

    objectCreatedEvent = events.EventRegister.register("objectCreated",objectCreatedEventTemplate)

    objectRemovedEvent = events.EventRegister.register("objectRemoved",objectRemovedEventTemplate)

    cyclesEndedEvent = events.EventRegister.register("cycleEnded",cycleEndedEventTemplate)

    clientConnectedEvent = events.EventRegister.register("clientConnected",clientConnectedEventTemplate)

    clientDisconnectedEvent = events.EventRegister.register("clientDisconnected",clientDisconnectedEventTemplate)

    networkMessageEvent = events.EventRegister.register("networkMessage",networkMessageEventTemplate)

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
        self.bannedPlayers = set()
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

    def spawnFromEntry(self,id:str,prefabPath:str,data:dict):
        """Create a sprite from serialized form (network delta or saved world)."""
        rect = data.get("rect")
        if prefabPath == None or rect == None:
            return None
        try:
            cls = self.getObjectByPrefabPath(prefabPath)
        except (ValueError,KeyError):
            cls = None
        if cls == None:
            return None
        object = cls(self,(rect["x"],rect["y"],rect["dimension"]))
        self.addObjectByID(object,id)
        self.patchObject(object,data)
        return object

    def patchObject(self,object,data:dict) -> None:
        data = dict(data)
        currentAnimation = data.pop("currentAnimation",None)
        rect = data.get("rect")
        object.fromDict(data)
        if rect != None:
            object.pos = (rect["x"],rect["y"],rect["dimension"])
        if currentAnimation != None:
            object.loadAnimation(currentAnimation)

    @staticmethod
    def getWorldPath(name:str) -> str:
        return f"save/{name}"

    def saveWorld(self,name:str) -> None:
        folder = self.getWorldPath(name)
        os.makedirs(folder,exist_ok=True)
        sprites = {}
        for id,object in list(self.sprites.items()):
            sprites[id] = {"prefabPath":object.prefabPath,"data":object.toSaveData()}
        custom = {}
        for packageName,package in self.packages.items():
            saveState = getattr(package.core,"saveState",None)
            if saveState != None:
                custom[packageName] = saveState(self)
        settings = {"name":name,"bannedPlayers":sorted(self.bannedPlayers),"custom":custom}
        with open(f"{folder}/settings.yaml","w") as f:
            yaml.safe_dump(settings,f)
        with open(f"{folder}/sprites.json","w") as f:
            json.dump(sprites,f)

    def loadWorld(self,name:str) -> bool:
        folder = self.getWorldPath(name)
        try:
            with open(f"{folder}/settings.yaml") as f:
                settings = yaml.safe_load(f)
            with open(f"{folder}/sprites.json") as f:
                sprites = json.load(f)
        except (OSError,ValueError,yaml.YAMLError):
            self.raiseError("worldNotFound",f"no saved world named {name}")
            return False
        for id in list(self.sprites.keys()):
            self.removeObjectByID(id)
        for id,entry in sprites.items():
            self.spawnFromEntry(id,entry.get("prefabPath"),dict(entry["data"]))
        self.bannedPlayers = set(settings.get("bannedPlayers",[]))
        custom = settings.get("custom",{})
        for packageName,package in self.packages.items():
            loadState = getattr(package.core,"loadState",None)
            if loadState != None and packageName in custom:
                loadState(self,custom[packageName])
        return True

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
        if self.network != None:
            self.network.close()
    
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
    
    def host(self,port:int,password:str=None,sendRate:int=1):
        self.network = network.HostNetwork(port)
        self.clientIdentities = {}   # transport id -> stable client id
        self.clientTransports = {}   # stable client id -> transport id
        self.clientMirrors = {}      # stable client id -> last data sent per sprite
        self.hostPassword = password
        self.sendRate = max(1,sendRate)
        self.mode = self.Mode.host
        pygame.display.set_caption("WorldSpawn - hosting")

    def join(self,ip:str,port:int,identity:str=None,password:str=None) -> bool:
        try:
            self.network = network.ClientNetwork(ip,port)
        except OSError as e:
            self.raiseError("connectionFailed",str(e))
            return False
        self.identity = identity if identity != None else uuid.uuid4().hex
        self.network.send({"type":"hello","identity":self.identity,"password":password})
        self.mode = self.Mode.join
        pygame.display.set_caption("WorldSpawn - client")
        return True

    def rejectClient(self,transportID:str,reason:str) -> None:
        self.network.sendTo(transportID,{"type":"rejected","reason":reason})
        self.network.dropClient(transportID)

    def kick(self,clientID:str) -> None:
        transportID = self.clientTransports.get(clientID)
        if transportID != None:
            self.network.sendTo(transportID,{"type":"rejected","reason":"kicked"})
            self.network.dropClient(transportID)
            self.detachClient(transportID)

    def ban(self,clientID:str) -> None:
        self.bannedPlayers.add(clientID)
        self.kick(clientID)

    def send(self,data,clientID:str=None) -> None:
        """Send a package-defined message. Client -> host, or host -> one/all clients."""
        message = {"type":"custom","data":data}
        if self.mode == self.Mode.join:
            self.network.send(message)
        elif self.mode == self.Mode.host:
            if clientID == None:
                self.network.broadcast(message)
            else:
                transportID = self.clientTransports.get(clientID)
                if transportID != None:
                    self.network.sendTo(transportID,message)

    def filterVisible(self,clientID:str,sprites:dict) -> dict:
        """Which sprites a client may see. Packages override via createFunction."""
        return sprites

    def attachClient(self,transportID:str,clientID:str) -> None:
        oldTransport = self.clientTransports.get(clientID)
        if oldTransport != None and oldTransport != transportID:
            self.clientIdentities.pop(oldTransport,None)
            self.network.dropClient(oldTransport)
        self.clientIdentities[transportID] = clientID
        self.clientTransports[clientID] = transportID
        self.clientMirrors[clientID] = {}
        self.addInputManager(clientID)
        self.network.sendTo(transportID,{"type":"welcome","clientID":clientID})
        self.addEvent(self.clientConnectedEventTemplate(clientID))

    def detachClient(self,transportID:str) -> None:
        clientID = self.clientIdentities.pop(transportID,None)
        if clientID == None or self.clientTransports.get(clientID) != transportID:
            return
        self.clientTransports.pop(clientID,None)
        self.clientMirrors.pop(clientID,None)
        self.inputMangers.pop(clientID,None)
        self.addEvent(self.clientDisconnectedEventTemplate(clientID))

    def syncClients(self) -> None:
        if not self.clientTransports:
            return
        current = {}
        for id,object in list(self.sprites.items()):
            current[id] = {"prefabPath":object.prefabPath,"data":object.toData()}
        for clientID,transportID in list(self.clientTransports.items()):
            visible = self.filterVisible(clientID,self.sprites)
            mirror = self.clientMirrors[clientID]
            changed = {}
            for id in visible:
                entry = current.get(id)
                if entry == None:
                    continue
                known = mirror.get(id)
                if known == None:
                    changed[id] = entry
                else:
                    diff = {key:value for key,value in entry["data"].items() if known.get(key) != value}
                    if diff:
                        changed[id] = {"data":diff}
            removed = [id for id in mirror if id not in visible or id not in current]
            if changed or removed:
                self.network.sendTo(transportID,{"type":"delta","changed":changed,"removed":removed})
            for id in removed:
                mirror.pop(id,None)
            for id,entry in changed.items():
                known = mirror.get(id)
                if known == None:
                    mirror[id] = dict(entry["data"])
                else:
                    known.update(entry["data"])

    def applyDelta(self,message:dict) -> None:
        for id in message["removed"]:
            if self.getObject(id) != None:
                self.removeObjectByID(id)
        for id,entry in message["changed"].items():
            object = self.getObject(id)
            if object == None:
                self.spawnFromEntry(id,entry.get("prefabPath"),entry["data"])
            else:
                self.patchObject(object,entry["data"])

    def hostUpdate(self):
        while not self.network.messages.empty():
            transportID,message = self.network.messages.get()
            messageType = message.get("type")
            if messageType == "hello":
                identity = message.get("identity")
                clientID = str(identity) if identity != None else transportID
                if clientID in self.bannedPlayers:
                    self.rejectClient(transportID,"banned")
                elif self.hostPassword != None and message.get("password") != self.hostPassword:
                    self.rejectClient(transportID,"wrong password")
                else:
                    self.attachClient(transportID,clientID)
            elif messageType == "disconnected":
                self.detachClient(transportID)
            elif messageType == "input":
                clientID = self.clientIdentities.get(transportID)
                if clientID != None:
                    events = inputManager.deserializeEvents(message.get("events",[]))
                    self.setInput(clientID,events,message["keys"],message["mouse"])
            elif messageType == "custom":
                clientID = self.clientIdentities.get(transportID)
                if clientID != None:
                    self.addEvent(self.networkMessageEventTemplate(clientID,message["data"]))
        self.serverUpdate()
        if self.cycles % self.sendRate == 0:
            self.syncClients()

    def clientNetworkUpdate(self):
        if not self.network.connected:
            self.raiseError("disconnected","lost connection to host")
            self.network = None
            self.setStartMode()
            return
        while not self.network.messages.empty():
            message = self.network.messages.get()
            messageType = message.get("type")
            if messageType == "welcome":
                oldManager = self.inputMangers.pop(self.userID,None)
                self.userID = message["clientID"]
                self.inputMangers[self.userID] = oldManager if oldManager != None else inputManager.InputManager()
            elif messageType == "delta":
                self.applyDelta(message)
            elif messageType == "custom":
                self.addEvent(self.networkMessageEventTemplate(None,message["data"]))
            elif messageType == "rejected":
                self.raiseError("joinRejected",message.get("reason","rejected"))
                self.network.close()
                self.network = None
                self.setStartMode()
                return
        localInput = self.inputMangers.get(self.userID)
        if localInput != None:
            self.network.send({"type":"input",
                               "keys":list(localInput.keys),
                               "mouse":list(localInput.mousePos),
                               "events":inputManager.serializeEvents(localInput.pendingEvents())})
        self.clientUpdate()