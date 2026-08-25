from data.managers import inputManager
from data.sprites import sprite


class UIObject(sprite.Sprite):
    def __init__(self,core,pos,objectData,visiblePlayers,interactivePlayers):
        super().__init__(core,pos,objectData)
        self.visiblePlayers = visiblePlayers
        self.interactivePlayers = interactivePlayers
        self.uiParts:list["UIObject"] = []
        for part in self.uiParts:
            self.core.addObject(part)

    def __del__(self):
        for part in self.uiParts:
            self.core.removeObject(part)

    def addUiPart(self,uiPart):
        self.uiParts.append(uiPart)
        self.core.addObject(uiPart)

    def removeUiPart(self,uiPart):
        self.core.removeObject(uiPart)
        self.uiParts.remove(uiPart)

    def addVisiblePlayer(self,playerID):
        self.visiblePlayers.add(playerID)
        for part in self.uiParts:
            part.addVisiblePlayer(playerID)

    def addInteractivePlayer(self,playerID):
        self.interactivePlayers.add(playerID)
        for part in self.uiParts:
            part.addInteractivePlayer(playerID)
        self.addVisiblePlayer(playerID)

    def show(self):
        self.addBlankEvent()
        super().show()
        self.updatable = True
        for part in self.uiParts:
            part.show()
        
    def hide(self):
        self.addBlankEvent()
        super().hide()
        self.updatable = False
        for part in self.uiParts:
            part.hide()
        
    def toggleVisibility(self):
        self.addBlankEvent()
        super().toggleVisibility()
        self.updatable = not self.updatable
        for part in self.uiParts:
            part.toggleVisibility()
            
    def getInputList(self):
        inpList:list[inputManager.InputManager] = []
        for id in self.interactivePlayers:
            inpList.append(self.core.getInputManager(id))
        return inpList

    def update(self):
        if not self.visible:
            return
        super().update()

    def isPlayerVisible(self, player) -> bool:
        return self.visible and player.id in self.visiblePlayers

    def display(self,displaySurf,player,displayOffset) -> None:
        if self.isPlayerVisible(player):
            self.displayImage(displaySurf,player,displayOffset)

    def displayImage(self,displaySurf,player,displayOffset) -> None:
        self.getDirection()
        offset = self.calculatePosByDisplayType()
        self.image.display(displaySurf,offset)

    def remove(self):
        for part in list(self.uiParts):
            self.removeUiPart(part)

def getObject():
    return UIObject