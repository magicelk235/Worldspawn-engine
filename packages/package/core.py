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
            obj = self.getGroup1("object1")(self,(20,20,"word"))
            self.addObjectByID(obj,event.clientID)
        for clientID in list(self.inputMangers.keys()):
            if clientID == self.userID:
                continue
            player = self.getObject(clientID)
            if player == None:
                continue
            inp = self.getInputManager(clientID)
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
