from data.core import events
from data.spatial.hitbox import Hitbox
from data.managers.timeManager import TimeManager,Timer
from data.spatial import hitbox,spatial,rect
from data.common import sendable
from sympy import cos,sin,pi # type: ignore
from data import core
from dataclasses import dataclass,field
import pygame,enum
from data.emitters import image
from typing import Callable
import queue

@ dataclass
class Animation:
    imageData:image.ImageData = image.ImageData()
    displayType:rect.DisplayType = rect.DisplayType.topLeft
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
        oldAnimation = sprite.getAnimation(sprite.previousAnimation)
        previousAnimation = sprite.getCurrentAnimation()
        if not previousAnimation.resetGif and self == oldAnimation:
            sprite.replaceTimer("animation",self.timer)
        
        sprite.moveable = self.moveable
        sprite.displayType = self.displayType
        sprite.image.setImageData(self.imageData)
        self.startFunc(sprite)

    def unload(self,sprite:"Sprite",newAnimation:"Animation"):
        if not newAnimation.resetGif:
            self.timer = sprite.getTimer("animation")
        self.endFunc(sprite)

    def getImageData(self):
        return self.imageData
    
    def weightCheck(self,other:"Animation"):
        return self.weight >= other.weight




@ dataclass
class SpriteData:
    hitbox:Hitbox = field(default_factory=Hitbox(1,1))
    animations:dict[str:Animation] = field(default_factory=dict)
    clientData:list = field(default_factory=list)
    displayByDirectionX:bool = True
    displayByDirectionY:bool = False

    def __post_init__(self):
        self.clientData=["rect","objectType","currentAnimation"]+self.clientData


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
        spatial.Spatial.__init__(self,core,pos)
        pygame.sprite.Sprite.__init__(self,core.emittersManager.displayManager)
        self.directionX:"Sprite.DirectionX" = self.DirectionX.left
        self.directionY:"Sprite.DirectionY" = self.DirectionY.top
        self.addTimer("animation",repeat=True)
        self.image: image.Image = image.Image(self,self.getAnimation().getImageData())
        self.core = core
        self.visible:bool = True
        self.speed:int = 1
        self.moveable:bool = True
        self.rect:rect.Rect = self.objectData.hitbox.getRect(pos)
        self.previousAnimation:str = "default"
        self.currentAnimation:str = "default"
        self.animationsQueue = queue.Queue()
        self.loadCurrentAnimation()
        self.dictData = dictData
    
    def getDefaultData(self) -> None:
        self.objectData = SpriteData(hitbox.Hitbox(0, 0, 0, 0),{"default":Animation()})

    def __post_init__(self):
        self.handleDictData()

    def handleDictData(self):
        if self.dictData != {}:
            self.fromDict()
            
    def toData(self):
        return self.toDict(self.objectData.clientData)

    @ property
    def size(self) -> tuple[int,int]:
        return self.rect.size()

    @ size.setter
    def size(self,size) -> None:
        self.objectData.hitbox.changeSize(*size)
        self.rect.setSize(*size)
        self.objectData.hitbox.updateRect(self.rect,self.pos)

    def getDirection(self) -> None:
        change = (0,0)
        if self.moveable:
            for vector in self.vectors.values():
                change = rect.Rect.addPos(change,vector.calculateDelta())
        if change[0] > 0:
            self.directionX = self.DirectionX.right
        elif change[0] < 0:
            self.directionX = self.DirectionX.left
        if change[1] < 0:
            self.directionY = self.DirectionY.top
        elif change[1] > 0:
            self.directionY = self.DirectionY.bottom

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
        self.displaytype = self.displayType.setEnd(end)

    def setDisplayTypeStart(self,start) -> None:
        self.displayType = self.displayType.setStart(start)


    def getType(self) -> str:
        return self.__module__.split(".")[0]


    # animations

    def getAnimation(self,name:str="default") -> Animation:
        return self.objectData.animations.get(name,self.objectData.animations["default"])

    def loadCurrentAnimation(self) -> None:
        animation = self.getAnimation(self.currentAnimation)
        animation.unload(self,self.getAnimation(self.currentAnimation))
        animation.load(self)
        
    def loadAnimation(self,name:str="default") -> None:
        if self.currentAnimation != name:
            self.getCurrentAnimation().unload(self)
            self.addEvent(self.switchAnimationEventTemplate(name,self.currentAnimation,self.id))
            self.currentAnimation = name
            self.loadCurrentAnimation()

    def getCurrentAnimation(self) -> Animation:
        return self.getAnimation(self.currentAnimation)

    def getNextAnimation(self) -> Animation:
        if self.animationsQueue.empty():
            return self.getAnimation()
        return self.getAnimation(self.animationsQueue.get())

    def updateAnimations(self) -> None:
        if self.timerEnded("animation"):
            self.getCurrentAnimation().unload(self,)
            self.loadAnimation()

    def setAnimation(self,name,extend=True) -> None:
        if extend and name == self.currentAnimation:
            self.extendTimer()
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
        return self.isVisible()

    def display(self,displaySurf,player,displayOffset) -> None:
        if self.canDisplay():
            self.displayImage(displaySurf,player,displayOffset)

    def displayImage(self,displaySurf,player,displayOffset) -> None:
        self.getDirection()
        
        offset = self.calculatePosByDisplayType() - displayOffset
        self.image.display(displaySurf,offset)
        self.rect.display(displaySurf)

    # rect

    def collideCheck(self,other:"Sprite",additionalRange:int=0) -> bool:
        return self.collideCheckRect(other.rect,additionalRange)
        
    def collideCheckIgnoreDimensions(self,other:"Sprite"):
        return self.rect.collideRectIgnoreDimension(other.rect)
        
    def collideCheckRect(self,rect:rect.Rect,additionalRange:int=0) -> bool:
        return self.rect.collideRect(rect,additionalRange)
        
    @ property
    def displayType(self) -> rect.DisplayType:
        return self.rect.displayType

    @ displayType.setter
    def displayType(self,displayType:rect.DisplayType):
        self.rect.displayType = displayType

    # update/main

    def update(self) -> bool:
        super().update()
        self.updateAnimations()
        self.updateVectors()
        return False