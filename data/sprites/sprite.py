from data.system import events
from data.spatial.hitbox import Hitbox
from data.managers.timeManager import Timer
from data.spatial import hitbox,spatial
from data.spatial.rect import Rect,DisplayType
from data.common import sendable
from sympy import cos,sin,pi
from data import core
from dataclasses import dataclass,field
import pygame,enum
from data.emitters.image import Image,ImageData
from typing import Callable
import queue

@ dataclass
class Animation:
    imageData:ImageData = ImageData()
    displayType:DisplayType = DisplayType.topLeft
    countDown:float = -1.0
    weight:int = 1
    moveable:bool = True
    nextAnimation:str = "default"
    startFunc:Callable = lambda x: None
    endFunc:Callable = lambda x: None
    timer:Timer = None
    
    @ property
    def resetGif(self):
        return self.imageData.resetGif

    def load(self,sprite:"Sprite"):
        sprite.addTimer("animation",self.countDown,True)
        if not self.resetGif and self.timer != None:
            # this animation is meant to carry on where it stopped, so the
            # frozen timer goes back in and starts counting again
            sprite.replaceTimer("animation",self.timer)
            self.timer.start()
        sprite.moveable = self.moveable
        sprite.displayType = self.displayType
        sprite.image.setImageData(self.imageData)
        if self.resetGif:
            sprite.image.image.reset()
        self.startFunc(sprite)

    def unload(self,sprite:"Sprite",newAnimation:"Animation"):
        if not self.resetGif and sprite.isTimer("animation"):
            timer = sprite.getTimer("animation")
            # freezing it, otherwise the cycles spent in other animations
            # count against this one and it ends the moment it comes back.
            # A stopped timer is not counting at all - a countdown of -1 is
            # held that way - and freezing that would come back as time
            # already spent, so it is dropped and the countdown is armed
            # afresh on the next load.
            self.timer = None if timer.stopped else timer.copyAndStop()
        self.endFunc(sprite)

    def getImageData(self):
        return self.imageData
    
    def weightCheck(self,other:"Animation"):
        return self.weight >= other.weight




@ dataclass
class SpriteData:
    hitbox:Hitbox = field(default_factory=lambda: Hitbox(1,1))
    animations:dict[str:Animation] = field(default_factory=dict)
    clientData:list = field(default_factory=list)
    saveData:list = field(default_factory=list)
    # Whether the anchor follows the way the sprite is facing. A sprite whose
    # art is mirrored as it turns needs it, because the overhang swaps sides
    # with the picture; anything else - a widget, a floor tile, a dropped item
    # - keeps the anchor its animation asked for.
    displayByDirectionX:bool = False
    displayByDirectionY:bool = False

    def __post_init__(self):
        # visible travels with the rest of what decides the picture: a client
        # or a loaded world rebuilds the sprite through __init__, which starts
        # it shown, and a hidden one would come back drawn
        self.clientData=["rect","currentAnimation","drawIndex","visible"]+self.clientData


class Sprite(spatial.Spatial,pygame.sprite.Sprite,sendable.Sendable):
    
    # event manager
    @staticmethod
    def switchAnimationEventTemplate(newAnimation,oldAnimation,objectID):
        return pygame.event.Event(events.EventRegister.getID("switchAnimation"),locals())
        
    
    switchAnimationEvent = events.EventRegister.register("switchAnimation",switchAnimationEventTemplate)
    


    # custom classes

    class DirectionX(enum.Enum):
        left = False
        right = True

    class DirectionY(enum.Enum):
        top = False
        bottom = True

    
    def __init__(self, core:"core.Core", pos: tuple[int,int,str],objectData=None,dictData={}):
        if objectData != None:
            self.objectData = objectData
        else:
            self.getDefaultData()
        # taken before the sprite joins the draw group, so nothing can be
        # drawn without a place in the order
        self.drawIndex:int = core.nextDrawIndex()
        spatial.Spatial.__init__(self,core,pos)
        # no draw group yet: the core puts a sprite in it when the sprite is
        # added to the world and takes it out again when it is removed, so
        # one that is built and never added is neither drawn nor kept alive
        pygame.sprite.Sprite.__init__(self)
        self.directionX:"Sprite.DirectionX" = self.DirectionX.left
        self.directionY:"Sprite.DirectionY" = self.DirectionY.top
        self.addTimer("animation",repeat=True)
        self.image: Image = Image(self.getAnimation().getImageData(),self)
        self.core = core
        self.visible:bool = True
        self.speed:int = 1
        self.moveable:bool = True
        self.rect:Rect = self.objectData.hitbox.getRect(pos)
        self.previousAnimation:str = "default"
        self.currentAnimation:str = "default"
        self.animationsQueue = queue.Queue()
        self.loadCurrentAnimation()
        self.dictData = dictData
    
    def getDefaultData(self) -> None:
        self.objectData = SpriteData(hitbox.Hitbox(0, 0, 0, 0),{"default":Animation()})

    def __post_init__(self):
        # a leaf class calls this once its own __init__ is done: the data can
        # name any attribute, so nothing may be applied before it exists.
        # Loading a saved or streamed sprite goes through core.patchObject
        # instead, which does the same thing from the outside.
        self.handleDictData()

    def handleDictData(self):
        if self.dictData != {}:
            self.fromDict(self.dictData)
            
    def toData(self):
        return self.toDict(self.objectData.clientData)

    def toSaveData(self):
        return self.toDict(self.objectData.clientData + self.objectData.saveData)

    @ property
    def size(self) -> tuple[int,int]:
        return self.rect.size

    @ size.setter
    def size(self,size) -> None:
        self.objectData.hitbox.changeSize(*size)
        self.rect.size = size
        self.objectData.hitbox.updateRect(self.rect,self.pos)

    def updateDirection(self) -> None:
        """Note which way the sprite is heading.

        This has to run while the vectors are still in hand. A step lasts one
        cycle, updateVectors spends it and drops it, and drawing happens after
        all of that: a sprite asked at draw time is always standing still and
        would keep the facing it was built with forever.
        """
        if not self.moveable:
            return
        change = (0,0)
        for vector in self.vectors.values():
            change = Rect.addPos(change,vector.calculateDelta(self))
        if change[0] > 0:
            self.directionX = self.DirectionX.right
        elif change[0] < 0:
            self.directionX = self.DirectionX.left
        if change[1] < 0:
            self.directionY = self.DirectionY.top
        elif change[1] > 0:
            self.directionY = self.DirectionY.bottom

    def getDirection(self) -> None:
        """Put the anchor on the side the sprite is facing.

        The art is mirrored as the sprite turns, so whatever overhangs the
        hitbox swaps sides with it. Facing left means the overhang is on the
        left, which is the right hand edge of the picture holding still.
        """
        if self.objectData.displayByDirectionX:
            directionX = self.DirectionX(not self.directionX.value).name
            self.setDisplayTypeEnd(directionX)

        if self.objectData.displayByDirectionY:
            directionY = self.DirectionY(not self.directionY.value).name
            self.setDisplayTypeStart(directionY)

    @ property
    def renderOrder(self) -> int:
        return self.image.renderOrder

    def setDisplayTypeEnd(self,end) -> None:
        self.displayType = self.displayType.setEnd(end)

    def setDisplayTypeStart(self,start) -> None:
        self.displayType = self.displayType.setStart(start)


    def getType(self) -> str:
        return self.__module__.split(".")[0]


    # animations

    def getAnimation(self,name:str="default") -> Animation:
        return self.objectData.animations.get(name,self.objectData.animations["default"])

    def loadCurrentAnimation(self) -> None:
        self.getCurrentAnimation().load(self)

    def loadAnimation(self,name:str="default") -> None:
        if self.currentAnimation != name:
            newAnimation = self.getAnimation(name)
            self.getCurrentAnimation().unload(self,newAnimation)
            self.addEvent(self.switchAnimationEventTemplate(name,self.currentAnimation,self.id))
            self.previousAnimation = self.currentAnimation
            self.currentAnimation = name
            self.loadCurrentAnimation()

    def getCurrentAnimation(self) -> Animation:
        return self.getAnimation(self.currentAnimation)

    def getNextAnimationName(self) -> str:
        if self.animationsQueue.empty():
            return self.getCurrentAnimation().nextAnimation
        return self.animationsQueue.get()

    def updateAnimations(self) -> None:
        if self.timerEnded("animation"):
            self.loadAnimation(self.getNextAnimationName())

    def setAnimation(self,name,extend=True) -> None:
        if extend and name == self.currentAnimation:
            self.getTimer("animation").restart()
        if self.getAnimation(name).weightCheck(self.getCurrentAnimation()):
            self.loadAnimation(name)

    def addAnimationToQueue(self,name:str) -> None:
        self.animationsQueue.put(name)
        
    def hide(self) -> None:
        self.visible = False

    def show(self) -> None:
        self.visible = True

    def toggleVisibility(self) -> None:
        self.visible = not self.visible

    def isVisible(self) -> bool:
        return self.visible

    def calculatePosByDisplayType(self) -> tuple[int,int]:
        displayedPos = self.displayType.calculatePosByDisplayType(self.image,self.rect,self.axis)
        return displayedPos

    def canDisplay(self,displaySurf,player,displayOffset) -> bool:
        if not self.isVisible():
            return False
        if self.rect.dimension != player.rect.dimension:
            return False
        view = displaySurf.get_rect()
        view.topleft = (displayOffset.x,displayOffset.y)
        # inflate the view by a screen so oversized images near the edge never pop
        # out, and the sprite rect by a pixel so zero-size hitboxes still collide
        return self.rect.rect.inflate(2,2).colliderect(view.inflate(view.w,view.h))

    def display(self,displaySurf,player,displayOffset) -> None:
        if self.canDisplay(displaySurf,player,displayOffset):
            self.displayImage(displaySurf,player,displayOffset)

    def displayImage(self,displaySurf,player,displayOffset) -> None:
        self.getDirection()
        
        offset = self.calculatePosByDisplayType() - displayOffset
        self.image.display(displaySurf,offset)
        self.rect.display(displaySurf)


    @ property
    def artRect(self) -> Rect:
        """The frame on screen, as a world rect.

        `rect` is the hitbox, which is what a sprite walks into things with.
        It can be a fraction of the picture: a tall lamp is a few pixels of
        base. Aiming at a sprite means aiming at what is drawn, so anything
        resolving a click wants this instead.
        """
        pos = self.calculatePosByDisplayType()
        size = self.image.getRawImage().get_size()
        return Rect(pygame.rect.Rect(int(pos[0]),int(pos[1]),*size),self.dimension)

    def collideCheckArt(self,rect:Rect,additionalRange:int=0) -> bool:
        return self.artRect.collideRect(rect,additionalRange)

    # rect

    def collideCheck(self,other:"Sprite",additionalRange:int=0) -> bool:
        return self.collideCheckRect(other.rect,additionalRange)
        
    def collideCheckIgnoreDimensions(self,other:"Sprite"):
        return self.rect.collideRectIgnoreDimension(other.rect)
        
    def collideCheckRect(self,rect:Rect,additionalRange:int=0) -> bool:
        return self.rect.collideRect(rect,additionalRange)
        
    @ property
    def displayType(self) -> DisplayType:
        return self.rect.displayType

    @ displayType.setter
    def displayType(self,displayType:DisplayType):
        self.rect.displayType = displayType

    # update/main

    def update(self) -> bool:
        super().update()
        self.updateAnimations()
        self.updateDirection()
        self.updateVectors()
        return False