# import aliveObject,default,displayType,events,hitbox,idManager,image,inventory,modifiers,multiMedia,rect,runnable,sound,sprite,timer,uiObject
import pygame,yaml,socket,pickle,enum,struct,types

from data import events
from data.media import mediaManager
pygame.init()
from data.managers import idManager,inputManager,fileManager
from data.sprites import aliveObject

class Api:
    
    class Package:

        def __init__(self,settings,core:"Core"):
            self.settings = settings
            core.packages[self.getName()] = self
            self.path = f"data/packages/{self.getName()}"
            self.enabled = False
            self.packageCoreClass = None
            if self.settings["alwaysEnabled"]:
                core.loadPackageData(self.getName())


        def getName(self) -> str:
            return self.settings["name"]

        def loadData(self,core:"Api") -> None:
            if self.enabled:
                raise ValueError(f"{self.getName()} is already enabled")
            if not self.enabled:
                self.enabled = True
                self.packageCoreClass = fileManager.getModule(self.path,"core")
                for folder in fileManager.getFolders(f"{self.path}/static",True):
                    core.createGetter(folder)
                for folder in fileManager.getFolders(f"{self.path}/dynamic",True):
                    core.AddType(folder)
                core.addToBase(self.packageCoreClass)
                

    def addToBase(self,newClass):
        self.__class__.__bases__ = self.__class__.__bases__+(newClass,)
        newClass.__init__(self)

    def __init__(self):
        self.packages:dict[str:self.Package] = {}
        self.loadedPackages:set["Api.Package"] = set()

    def getPackage(self,name:str) -> "Api.Package":
        try: 
            return self.packages[name]
        except:
            raise ValueError(f"No Package Named {name}")

    def loadPackage(self,path:str) -> None:
        try:
            with open(f"{path}/settings.yaml") as f:
                settings = yaml.safe_load(f)
        except FileNotFoundError:
            raise ValueError(f"The Package In {path} Has a Problem With The File settings.yaml")
        self.Package(settings,self)
        
        

    def loadPackages(self) -> None:
        for path in fileManager.getFolders("data/packages",True):
            self.loadPackage(path)

    def loadPackageData(self,name):
        try:
            self.packages[name].loadData(self)
            self.loadedPackages.add(self.getPackage(name))
        except Exception as e:
            raise ValueError(f"No Package Named {name}")
        

    def loadPackagesData(self,names):
        for name in names:
            self.loadPackageData(name)

    def newWorld(self):
        for package in self.loadedPackages:
            package.packageCoreClass.newWorld(self)


class Core(Api,events.EventManager,idManager.IDManager):
    @staticmethod
    def objectCreatedEventTemplate(id:str,objType:str):
        return pygame.event.Event(events.EventRegister.getID("objectCreated"),locals())

    @staticmethod
    def objectRemovedEventTemplate(id:str,objType:str):
        return pygame.event.Event(events.EventRegister.getID("objectRemoved"),locals())

    objectCreatedEvent = events.EventRegister.register("objectCreated",objectCreatedEventTemplate)

    objectRemovedEvent = events.EventRegister.register("objectRemoved",objectRemovedEventTemplate)

    class Mode(enum.Enum):
        start = 0
        join = 1
        host = 2

    def __init__(self):
        self.sprites = {}
        self.multiMedia = mediaManager.MultiMedia(self)
        # importlib.reload(imageLoader)
        
        events.EventManager.__init__(self)
        idManager.IDManager.__init__(self,self.sprites)
        self.typeManager = {}
        self.getters = {}
        self.inputMangers = {}
        self.running = True
        self.userID = "main"
        self.mode = self.Mode.start
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # pygame.display.set_caption(f"WorldSpawn Code:{self.ip}")
        # pygame.display.set_icon(pygame.image.load(default.resource_path("assets/gui/world_icon.png")))
        Api.__init__(self)
        self.loadPackages()
        self.setStartMode()
        

    def updateInput(self):
        pass


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
        for inp in list(self.inputMangers.values()):
            inp.setRawInput(rawEvents,rawKeys,mouse)
    
    def setStartMode(self):
        pygame.display.set_caption(f"WorldSpawn")
        self.mode = self.Mode.start

    def clientUpdate(self):
        for package in self.loadedPackages:
            package.packageCoreClass.clientUpdate(self)
    def serverUpdate(self):
        for package in self.loadedPackages:
            package.packageCoreClass.serverUpdate(self)

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

    def getObjectByTypeAndName(self,type:str,name:str):
        return getattr(f"get{type.capitalize()}")(name)
    
    def getObjectByPath(self,path):
        type,name = path.split(".")
        return self.getObjectByTypeAndName(type,name)

    def createGetter(self,path):
        objects = {}
        
        for file in fileManager.getFiles(path,True):
            objects[file] = fileManager.getModule(path,file)
        try:
            loadedObjects = self.getters[path.split("/")[-1]]
            objects = objects | loadedObjects
        except:
            pass
        objName:str = path.split("/")[-1]
        self.getters[f"{objName}"] = objects
        def f(self,name):
            return self.getters[objName].get(name)
        
        setattr(self,f"get{objName.capitalize()}",types.MethodType(f,self))
        

    def AddType(self,path):
        self.createGetter(path)
        if not hasattr(self,path.split("/")[-1]):
            setattr(self,path.split("/")[-1],{})
            self.typeManager[fileManager.getModule(path,"base")] = getattr(self,path.split("/")[-1])
    
    @staticmethod
    def getType(object):
        return object.__module__.split(".")[-2]

    def getDictType(self,type):
        return getattr(self,type)

    def addObjectByID(self, object, id,forcedType=None):
        forcedType = forcedType if forcedType != None else self.getType(object)
        super().addObjectByID(object, id)
        dictType = self.getDictType(forcedType)
        dictType[object.id] = object
        self.addEvent(self.objectCreatedEventTemplate(object.id,forcedType))
    
    def removeObjectByID(self, id):
        self.addEvent(self.objectRemovedEventTemplate(id,self.getType(self.getObject(id))))
        
        self.multiMedia.removeObject(self.getObject(id))
        dictType = self.getDictType(self.getType(self.getObject(id)))
        del dictType[id]
        super().removeObjectByID(id)
        if id in self.inputMangers:
            self.inputMangers.remove(id)

    def getAliveObjects(self):
        aliveObjects = {}
        
        for type in self.typeManager.keys():
            if issubclass(type,aliveObject.AliveObject):
                aliveObjects = aliveObjects | self.typeManager[type]
        return aliveObjects

    def main(self):        

        while self.running:
            self.getInput()
            if self.eventWillHappen("timer"):
                if self.eventHappened(pygame.QUIT):
                    self.running = False
                self.update()
                self.multiMedia.update(self.getObject(self.userID),True)
                self.clearEvents()
    
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
    
    def receive(self):
        if self.mode != self.Mode.start:
            def recvall(sock, n):
                data = bytearray()
                while len(data) < n:
                    packet = sock.recv(n - len(data))
                    if not packet:
                        return None
                    data.extend(packet)
                return data
            
            rawDataSize = recvall(self.socket, 4)
            if not rawDataSize:
                return None
            dataSize = struct.unpack('>I', rawDataSize)[0]
            data = pickle.loads(recvall(self.socket, dataSize))
            return data

    def send(self, data):
        if self.mode != self.Mode.start:
            data = pickle.dumps(data)
            data = struct.pack('>I', len(data)) + data
            self.socket.sendall(data)