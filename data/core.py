
import pygame,enum,uuid,json,os,traceback
import yaml
pygame.init()
from data.system.api import Api
from data.system import events, errors, network
from data.managers.emittersManager import EmittersManager
from data.common.runnable import Runnable
from data.managers import idManager,inputManager
from data.sprites import aliveObject

def validInput(keys,mouse) -> bool:
    """Whether an input message carries what a client sends: the held keys as
    a list of names and the mouse as two numbers. Anything else is dropped
    before it reaches an InputManager, where it would fail later and inside a
    package instead."""
    if not isinstance(keys,list) or not all(isinstance(key,str) for key in keys):
        return False
    return (isinstance(mouse,list) and len(mouse) == 2
            and all(isinstance(value,(int,float)) for value in mouse))


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
        # Draw order inside a render band used to be whatever order sprites
        # happened to be created in. That is fine on one machine and wrong the
        # moment a second one is watching: a client builds its sprites in the
        # order deltas arrive, so a panel could land on top of its own
        # buttons. Every sprite takes a number from here and the number is
        # streamed, so a client draws in the host's order.
        self.drawCounter = 0
        self.emittersManager = EmittersManager(self)
        
        events.EventManager.__init__(self)
        idManager.IDManager.__init__(self,self.sprites)
        self.inputMangers = {}
        self.running = True
        self.userID = "main"
        self.mode = self.Mode.start
        self.network = None
        self.bannedPlayers = set()
        # online bookkeeping exists before hosting does, so kick and ban have
        # somewhere to look when nobody is connected, and a package folder
        # named after one of these is caught when its group is made instead of
        # being overwritten by host() or join() later
        self.clientIdentities = {}   # transport id -> stable client id
        self.clientTransports = {}   # stable client id -> transport id
        self.clientMirrors = {}      # stable client id -> last data sent per sprite
        self.hostPassword = None
        self.sendRate = 1
        self.identity = None
        self.addInputManager(self.userID)
        # pygame.display.set_caption(f"WorldSpawn Code:{self.ip}")
        # pygame.display.set_icon(pygame.image.load(default.resource_path("assets/gui/world_icon.png")))
        Api.__init__(self)
        self.setStartMode()
        
    def nextDrawIndex(self) -> int:
        self.drawCounter += 1
        return self.drawCounter


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

    # Both hooks are optional: a package that has nothing to do on one side of
    # a connection does not have to define the method for it.
    def clientUpdate(self):
        for package in self.packages.values():
            hook = getattr(package.core,"clientUpdate",None)
            if hook != None:
                hook(self)

    def serverUpdate(self):
        for package in self.packages.values():
            hook = getattr(package.core,"serverUpdate",None)
            if hook != None:
                hook(self)

    def update(self):
        for object in list(self.sprites.values()):
            # the walk is over a copy: something earlier this cycle may have
            # removed this sprite already, and its id may name a replacement
            # by now. Neither is this sprite's to update or to remove.
            if self.sprites.get(object.id) is not object:
                continue
            if object.main() and self.sprites.get(object.id) is object:
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
        previous = self.getObject(id)
        if previous != None and previous is not object:
            # an id names one sprite. The one it named before is taken out
            # properly first, or it would go on being drawn with no id left
            # to remove it by
            self.removeObjectByID(id)
        domainName = object.domain
        prefabName = object.prefab
        domain = self.getDomain(domainName)
        addFunction = domain.settings["add-function"]
        exec(addFunction,globals(),locals())
        self.addObjectToGroupById(object,id,domainName)
        self.addObjectToGroupById(object,id,prefabName)
        # drawn while it is in the world and no longer: a sprite joins the
        # draw group here rather than when it is built, so one that is made
        # and never added is neither drawn nor kept alive by the group
        if isinstance(object,pygame.sprite.Sprite):
            self.emittersManager.displayManager.add(object)
        self.addEvent(self.objectCreatedEventTemplate(id,object.module))
        

    # Groups are looked up in the registry Api keeps, never by attribute name:
    # a prefab folder called packages or network must not have sprites
    # written into the dict of the same name the core already holds.
    def addObjectToGroupById(self,object:Runnable,id:str,groupName:str):
        # only domains that asked for a dynamic getter have a group dict, so a
        # missing one is normal and not an error
        groupDict = self.GroupsByNames.get(groupName)
        if groupDict != None:
            groupDict[id] = object

    def removeObjectToGroupById(self,id:str,groupName:str):
        groupDict = self.GroupsByNames.get(groupName)
        if groupDict != None:
            groupDict.pop(id,None)

    def removeObjectByID(self, id):
        object = self.getObject(id)
        if object == None:
            # already gone: two owners dropping the same sprite in one cycle
            return
        domainName = object.domain
        prefabName = object.prefab
        domain = self.getDomain(domainName)
        removeFunction = domain.settings["remove-function"]

        exec(removeFunction, globals(),locals())
        self.removeObjectToGroupById(id,domainName)
        self.removeObjectToGroupById(id,prefabName)
        self.emittersManager.removeObject(object)
        self.addEvent(self.objectRemovedEventTemplate(id,object.module))
        if getattr(object,"uiParts",None):
            # a widget owns the sprites it built. Run this once the id is
            # already out of the world, so a teardown that reaches back for
            # its own object finds nothing instead of looping
            object.remove()

    def getAliveObjects(self):
        aliveObjects = {}
        for type in self.GroupsByBases.keys():
            if issubclass(type,aliveObject.AliveObject):
                aliveObjects = aliveObjects | self.GroupsByBases[type]
        return aliveObjects

    def spawnFromEntry(self,id:str,prefabPath:str,data:dict):
        """Create a sprite from serialized form (network delta or saved world)."""
        if not isinstance(data,dict):
            return None
        rect = data.get("rect")
        if not isinstance(prefabPath,str) or not isinstance(rect,dict):
            return None
        if not all(key in rect for key in ("x","y","dimension")):
            return None
        try:
            cls = self.getObjectByPrefabPath(prefabPath)
        except (ValueError,KeyError):
            cls = None
        if cls == None:
            # a prefab the packages no longer provide, or a domain that has no
            # getter to find it through
            self.raiseError("spriteNotRestored",f"{id} ({prefabPath}): no such prefab")
            return None
        try:
            object = cls(self,(rect["x"],rect["y"],rect["dimension"]))
        except Exception as e:
            # a class that can no longer be built from (core, pos) alone - it
            # grew a required argument since the save, say - costs this
            # sprite and nothing else. Where it failed goes in the message,
            # so a real bug in a constructor is not mistaken for that.
            self.raiseError("spriteNotRestored",f"{id} ({prefabPath}): {self.describeFailure(e)}")
            return None
        self.addObjectByID(object,id)
        try:
            self.patchObject(object,data)
        except Exception as e:
            # the stored fields no longer fit this class: drop the sprite
            # rather than leave a half-applied one in the world
            self.removeObjectByID(id)
            self.raiseError("spriteNotRestored",f"{id} ({prefabPath}): {self.describeFailure(e)}")
            return None
        return object

    @staticmethod
    def describeFailure(e:Exception) -> str:
        """The exception and the file and line it was raised at."""
        frames = traceback.extract_tb(e.__traceback__)
        if not frames:
            return f"{type(e).__name__}: {e}"
        frame = frames[-1]
        return f"{type(e).__name__}: {e} ({frame.filename}, line {frame.lineno})"

    def patchObject(self,object,data:dict) -> None:
        data = dict(data)
        currentAnimation = data.pop("currentAnimation",None)
        rect = data.get("rect")
        object.fromDict(data)
        drawIndex = getattr(object,"drawIndex",None)
        if isinstance(drawIndex,int) and drawIndex > self.drawCounter:
            # a saved or streamed sprite brings its place in the draw order
            # along. Whatever is made after it comes after it, rather than
            # taking a number that is already in use.
            self.drawCounter = drawIndex
        if rect != None:
            # a serialized rect carries the hitbox, which sits at the sprite
            # position plus the hitbox offset; feeding it back in as the
            # position would walk the sprite by that offset on every load
            hitbox = object.objectData.hitbox
            object.pos = (rect["x"]-hitbox.xOffset,rect["y"]-hitbox.yOffset,rect["dimension"])
        if currentAnimation != None:
            object.loadAnimation(currentAnimation)

    @staticmethod
    def getWorldPath(name:str) -> str:
        return f"save/{name}"

    def saveWorld(self,name:str) -> bool:
        """Write the world to save/<name>. True once both files are on disk.

        A world that cannot be written leaves the save that was there before
        as it was and raises a worldNotSaved error: a value that does not fit
        the file (a set in saveData, an object in saveState) makes this return
        False, and an OSError from the disk is raised again after the error,
        as it always was.
        """
        folder = self.getWorldPath(name)
        # made before the packages are asked for their state, so one that
        # keeps files of its own beside the world has a folder to put them in
        os.makedirs(folder,exist_ok=True)
        sprites = {}
        for id,object in list(self.sprites.items()):
            # sprites that only exist to show something - menus, cursors,
            # anything a package rebuilds on its own - set persistent False
            # so a saved world holds world state and nothing else
            if not getattr(object,"persistent",True):
                continue
            sprites[id] = {"prefabPath":object.prefabPath,"data":object.toSaveData()}
        custom = {}
        for packageName,package in self.packages.items():
            saveState = getattr(package.core,"saveState",None)
            if saveState != None:
                custom[packageName] = saveState(self)
        settings = {"name":name,"bannedPlayers":sorted(self.bannedPlayers),"custom":custom}
        # Both files are turned into text before either one is opened, so a
        # value that cannot be stored stops the save before anything is written.
        try:
            texts = {"sprites.json":json.dumps(sprites),"settings.yaml":yaml.safe_dump(settings)}
        except (TypeError,ValueError,yaml.YAMLError) as e:
            self.raiseError("worldNotSaved",f"{name}: {e}")
            return False
        # Both go to temporary files first and replace the old ones only once
        # both are written, so a full disk costs neither the copy that is
        # already there nor the match between the two files.
        paths = {fileName:f"{folder}/{fileName}" for fileName in texts}
        try:
            for fileName,text in texts.items():
                with open(f"{paths[fileName]}.tmp","w") as f:
                    f.write(text)
            for path in paths.values():
                os.replace(f"{path}.tmp",path)
        except OSError as e:
            for path in paths.values():
                try:
                    os.remove(f"{path}.tmp")
                except OSError:
                    pass
            self.raiseError("worldNotSaved",f"{name}: {e}")
            raise
        return True

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
        if not isinstance(sprites,dict):
            # refuse before touching the world: a half-cleared core is worse
            # than one that never started loading
            self.raiseError("worldCorrupt",f"the sprite table of {name} is not a mapping")
            return False
        if not isinstance(settings,dict):
            settings = {}
        for id in list(self.sprites.keys()):
            self.removeObjectByID(id)
        skipped = 0
        for id,entry in sprites.items():
            # one unreadable sprite - a prefab the packages no longer provide,
            # a truncated entry - must cost that sprite and nothing else
            data = entry.get("data") if isinstance(entry,dict) else None
            if not isinstance(data,dict) or self.spawnFromEntry(id,entry.get("prefabPath"),dict(data)) == None:
                skipped += 1
        if skipped:
            self.raiseError("worldPartlyLoaded",f"{skipped} sprites of {name} could not be restored")
        # identities are compared as text, and a list typed in by hand may
        # hold numbers; anything that is not a list is no ban list at all
        banned = settings.get("bannedPlayers")
        self.bannedPlayers = {str(player) for player in banned} if isinstance(banned,list) else set()
        custom = settings.get("custom",{})
        if not isinstance(custom,dict):
            custom = {}
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
    
    def host(self,port:int,password:str=None,sendRate:int=1) -> bool:
        if self.mode == self.Mode.host:
            self.raiseError("alreadyHosting",f"already hosting on this world")
            return False
        try:
            hostNetwork = network.HostNetwork(port)
        except OSError as e:
            # port taken, or no permission to bind it: a failed listen is not
            # a reason to take the game down
            self.raiseError("hostFailed",str(e))
            return False
        self.endNetworkSession()
        self.network = hostNetwork
        self.clientIdentities = {}   # transport id -> stable client id
        self.clientTransports = {}   # stable client id -> transport id
        self.clientMirrors = {}      # stable client id -> last data sent per sprite
        self.hostPassword = password
        self.sendRate = max(1,sendRate)
        self.mode = self.Mode.host
        pygame.display.set_caption("WorldSpawn - hosting")
        return True

    def join(self,ip:str,port:int,identity:str=None,password:str=None) -> bool:
        try:
            clientNetwork = network.ClientNetwork(ip,port)
        except OSError as e:
            self.raiseError("connectionFailed",str(e))
            return False
        self.endNetworkSession()
        self.network = clientNetwork
        self.identity = identity if identity != None else uuid.uuid4().hex
        self.network.send({"type":"hello","identity":self.identity,"password":password})
        self.mode = self.Mode.join
        pygame.display.set_caption("WorldSpawn - client")
        return True

    def endNetworkSession(self) -> None:
        """Close the connection that is open, if there is one.

        Hosting and joining replace each other. A host left open would keep
        its port and its guests with nothing serving them, and their input
        piling up in a queue nobody reads; a connection to another host would
        keep filling one too. A host lets its guests go first, so every
        clientConnected still meets its clientDisconnected.
        """
        if self.network == None:
            return
        if self.mode == self.Mode.host:
            for transportID in list(self.clientIdentities):
                self.detachClient(transportID)
        self.network.close()
        self.network = None

    def rejectClient(self,transportID:str,reason:str) -> None:
        self.network.sendTo(transportID,{"type":"rejected","reason":reason})
        self.network.dropClient(transportID)

    def kick(self,clientID:str) -> None:
        transportID = self.clientTransports.get(clientID)
        if transportID != None:
            self.network.sendTo(transportID,{"type":"rejected","reason":"kicked"})
            self.network.dropClient(transportID)
            self.detachClient(transportID)
            # What it said before it was cut off and nobody has read yet ends
            # with the connection. The events name the client, not the
            # connection, so a player who is straight back would otherwise be
            # kicked again by a message from the one that was just closed.
            self.dropPendingEvents(self.networkMessageEvent,clientID)

    def dropPendingEvents(self,eventID:int,clientID:str) -> None:
        """Take clientID's events of one kind out of those due next cycle."""
        pending = self.nextEvents.get(eventID)
        if pending:
            pending[:] = [event for event in pending if event.clientID != clientID]
            if not pending:
                del self.nextEvents[eventID]

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
                # every client that has been let in, and nobody else: a
                # socket that has not said hello has not given the password
                # either
                transportIDs = list(self.clientTransports.values())
            else:
                transportID = self.clientTransports.get(clientID)
                transportIDs = [] if transportID == None else [transportID]
            for transportID in transportIDs:
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
        # A client that dropped and came straight back inside one cycle would
        # be reported as gone and back at once, and a package that despawns on
        # the one and spawns on the other is left holding nothing for the
        # returning player. To the packages it never left.
        self.dropPendingEvents(self.clientDisconnectedEvent,clientID)
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
                # an id can be handed to a different kind of sprite between
                # two syncs; diffing against the old one would patch the
                # replacement's fields onto whatever the client still holds
                if known == None or known["prefabPath"] != entry["prefabPath"]:
                    changed[id] = entry
                else:
                    diff = {key:value for key,value in entry["data"].items()
                            if known["data"].get(key) != value}
                    if diff:
                        changed[id] = {"data":diff}
            removed = [id for id in mirror if id not in visible or id not in current]
            if changed or removed:
                self.network.sendTo(transportID,{"type":"delta","changed":changed,"removed":removed})
            for id in removed:
                mirror.pop(id,None)
            for id,entry in changed.items():
                # toDict already hands out copies of list and dict fields, so
                # nothing in an entry changes when the sprite does. The data
                # dict itself is shared by every client's diff this sync and
                # gets its own copy before a mirror updates it in place.
                if "prefabPath" in entry:
                    mirror[id] = {"prefabPath":entry["prefabPath"],"data":dict(entry["data"])}
                else:
                    mirror[id]["data"].update(entry["data"])

    def applyDelta(self,message:dict) -> None:
        for id in message["removed"]:
            if self.getObject(id) != None:
                self.removeObjectByID(id)
        for id,entry in message["changed"].items():
            object = self.getObject(id)
            prefabPath = entry.get("prefabPath")
            if object != None and prefabPath != None and object.prefabPath != prefabPath:
                # the host handed this id to a different kind of sprite
                self.removeObjectByID(id)
                object = None
            if object == None:
                self.spawnFromEntry(id,prefabPath,entry["data"])
            else:
                try:
                    self.patchObject(object,entry["data"])
                except Exception as e:
                    # the same as a sprite that cannot be built: this one
                    # goes, the rest of the delta still lands
                    self.removeObjectByID(id)
                    self.raiseError("spriteNotRestored",f"{id} ({object.prefabPath}): {self.describeFailure(e)}")

    def hostUpdate(self):
        while not self.network.messages.empty():
            transportID,message = self.network.messages.get()
            # every message comes from another program, and one that does not
            # speak this protocol must not be able to stop the host with it
            if not isinstance(message,dict):
                continue
            messageType = message.get("type")
            if messageType == "hello":
                if transportID in self.clientIdentities:
                    # one hello per connection: a second one under another
                    # name would leave the first attached with nothing to
                    # detach it
                    continue
                identity = message.get("identity")
                clientID = str(identity) if identity != None else transportID
                if clientID in self.bannedPlayers:
                    self.rejectClient(transportID,"banned")
                elif self.hostPassword != None and message.get("password") != self.hostPassword:
                    self.rejectClient(transportID,"wrong password")
                elif clientID == self.userID:
                    # the host's own character is named after userID, which is
                    # the same on every machine. A guest offering that name
                    # would be handed the host's character and its input
                    # manager, and the two would drive one sprite.
                    self.rejectClient(transportID,"identity already belongs to the host")
                else:
                    self.attachClient(transportID,clientID)
            elif messageType == "disconnected":
                self.detachClient(transportID)
            elif messageType == "input":
                clientID = self.clientIdentities.get(transportID)
                keys,mouse = message.get("keys"),message.get("mouse")
                if clientID != None and validInput(keys,mouse):
                    events = inputManager.deserializeEvents(message.get("events",[]))
                    self.setInput(clientID,events,keys,mouse)
            elif messageType == "custom":
                clientID = self.clientIdentities.get(transportID)
                if clientID != None:
                    self.addEvent(self.networkMessageEventTemplate(clientID,message.get("data")))
        self.serverUpdate()
        if self.cycles % self.sendRate == 0:
            self.syncClients()

    def clientNetworkUpdate(self):
        # anything already queued is read before the socket is judged: a host
        # that refuses a join sends the reason and then drops the connection,
        # so checking the socket first would replace "banned" or "wrong
        # password" with "lost connection" every time
        if not self.network.connected and self.network.messages.empty():
            self.raiseError("disconnected","lost connection to host")
            self.network.close()
            self.network = None
            self.setStartMode()
            return
        while not self.network.messages.empty():
            message = self.network.messages.get()
            messageType = message.get("type")
            if messageType == "welcome":
                # The host owns this world from here on and streams all of it
                # next. Whatever this process built on its own, or kept from a
                # session before, goes now, the way loadWorld clears before it
                # fills: the host never names those ids, so no delta would
                # ever take them away.
                for id in list(self.sprites.keys()):
                    self.removeObjectByID(id)
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