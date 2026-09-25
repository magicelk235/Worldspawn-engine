from data.managers import inputManager
from data.sprites import sprite


class UIObject(sprite.Sprite):
    def __init__(self,core,pos,objectData,visiblePlayers,interactivePlayers):
        super().__init__(core,pos,objectData)
        self.visiblePlayers = visiblePlayers
        self.interactivePlayers = interactivePlayers
        self.uiParts:list["UIObject"] = []

    # Teardown is explicit through remove(). Doing it from __del__ means
    # mutating the core's id tables at whatever point the collector gets
    # round to the widget, which is usually after its parts were already
    # dropped with their parent - or while the world is being torn down.

    def addUiPart(self,uiPart):
        """Hand a child widget over to this one.

        A part inherits visibility, audience and lifetime: it hides with the
        parent, gains the parent's new viewers, and goes when the parent goes.
        It does not inherit position. Parts are placed in the same window
        coordinates as everything else, and a composite widget moves its own
        parts, because not every part follows the parent - an inventory mark
        stays on the cell it marked while the cursor above it keeps moving.
        """
        if uiPart in self.uiParts:
            return
        self.uiParts.append(uiPart)
        self.core.addObject(uiPart)

    def removeUiPart(self,uiPart):
        # a part can already be gone: dropped with its parent, dropped by the
        # host's delta, or handed here twice by whatever built it
        if uiPart not in self.uiParts:
            return
        self.uiParts.remove(uiPart)
        self.core.removeObject(uiPart)

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
        # the blank event only means "something changed this cycle", so it is
        # pointless once the widget is already in the state being asked for
        if not self.visible:
            self.addBlankEvent()
        super().show()
        self.updatable = True
        for part in self.uiParts:
            part.show()
        
    def hide(self):
        if self.visible:
            self.addBlankEvent()
        super().hide()
        self.updatable = False
        for part in self.uiParts:
            part.hide()
        
    def toggleVisibility(self):
        # the parent decides: flipping each part on its own inverts anything
        # that was hidden by its own logic, and hiding a panel would then
        # reveal it
        if self.visible:
            self.hide()
        else:
            self.show()
            
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
        """Drop everything this widget built.

        Depth first, because a part is free to have parts of its own, and
        idempotent, because a widget is usually torn down by whoever owns it
        and again by the world being emptied around it.
        """
        for part in list(self.uiParts):
            part.remove()
            self.removeUiPart(part)

def getObject():
    return UIObject