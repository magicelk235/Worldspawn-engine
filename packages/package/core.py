class MyClass:
    def __init__(self):
        obj = self.getGroup1("object1")(self,(0,0,"word"))
        self.addObjectByID(obj,"main")
    def hostInit(self):...
    def clientInit(self):...
    def generalUpdate(self):...
    def clientUpdate(self):...
    def serverUpdate(self):
        for event in self.getEventList("clientConnected"):
            if self.getObject(event.clientID) == None:
                obj = self.getGroup1("object1")(self,(20,20,"word"))
                self.addObjectByID(obj,event.clientID)
        for event in self.getEventList("networkMessage"):
            kind = event.data.get("kind") if isinstance(event.data,dict) else None
            if kind == "ping":
                self.send({"kind":"pong"},event.clientID)
            elif kind == "despawn-mark":
                if self.getObject(f"{event.clientID}-mark") != None:
                    self.removeObjectByID(f"{event.clientID}-mark")
        for clientID in list(self.inputMangers.keys()):
            if clientID == self.userID:
                continue
            inp = self.getInputManager(clientID)
            if inp.isKeyPressed("e") and self.getObject(f"{clientID}-mark") == None:
                mark = self.getGroup1("object1")(self,(40,40,"word"))
                self.addObjectByID(mark,f"{clientID}-mark")
            player = self.getObject(clientID)
            if player == None:
                continue
            if inp.isKeyHeld("d"):
                player.addExcluciveVector((1,0),0.05)
            if inp.isKeyHeld("a"):
                player.addExcluciveVector((-1,0),0.05)
            if inp.isKeyHeld("w"):
                player.addExcluciveVector((0,-1),0.05)
            if inp.isKeyHeld("s"):
                player.addExcluciveVector((0,1),0.05)

def getObject():
    return MyClass
