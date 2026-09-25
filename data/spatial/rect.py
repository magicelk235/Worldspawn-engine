from data.common import sendable

import pygame

from enum import Enum

class DisplayType(Enum):
    topLeft = "topleft"
    topRight = "topright"
    bottomLeft = "bottomleft"
    bottomRight = "bottomright"
    center = "center"

    def getStart(self):
        return self.value.replace("left","").replace("right","")

    def getEnd(self):
        return self.value.replace("bottom","").replace("top","")

    def setStart(self, value):
        if self.value != "center":
            end = self.getEnd()
            return DisplayType(value+end)
        return self
    def setEnd(self, value):
        if self.value != "center":
            start = self.getStart()
            return DisplayType(start+value)
        return self

    def calculatePosByDisplayType(self,image,hitbox, pos):
        # how far along the overhang the anchor sits: 0 keeps the image edge
        # on the hitbox edge, 1 pushes it to the far edge, 0.5 centres it
        startDict = {"top":0,"bottom":1,"center":0.5}
        endDict = {"left":0,"right":1,"center":0.5}
        start,end = self.getParts()
        imageSize = image.size
        size = hitbox.size
        start,end = startDict[start],endDict[end]
        delta = ((size[0]-imageSize[0])*end,(size[1]-imageSize[1])*start)
        from data.spatial.rect import Rect
        return Rect.addPos(pos,delta)

    def getParts(self):
        return self.getStart(),self.getEnd()


class Rect(sendable.Sendable):
    def __init__(self, rect, dimension,displayType=DisplayType.topLeft):
        self.visible = False
        self.rect:pygame.rect.Rect = rect
        self.dimension = dimension
        self.displayType = displayType
        self.fracX = 0
        self.fracY = 0

    def toDict(self):
        return super().toDict(["x","y","w","h","dimension"])

    @staticmethod
    def addPos(pos1,pos2):
        return pos1[0] + pos2[0],pos1[1] + pos2[1]
    @staticmethod
    def subPos(pos1,pos2):
        return pos1[0] - pos2[0],pos1[1]-pos2[1]

    def display(self,displaySurf):
        if self.visible:
            self.draw(displaySurf)

    def draw(self,displaySurf:pygame.Surface):
        pygame.draw.rect(displaySurf, (255, 0, 0), self.rect, 2)

    @staticmethod
    def isPosBetween(mainPos,pos1,pos2):
        min_bound = (min(pos1[0], pos2[0]), min(pos1[1], pos2[1]))
        max_bound = (max(pos1[0], pos2[0]), max(pos1[1], pos2[1]))
        return min_bound[0] <= mainPos[0] <= max_bound[0] and min_bound[1] <= mainPos[1] <= max_bound[1]

    

    @ property
    def w(self):
        return self.rect.w

    @ w.setter
    def w(self, w):
        self.rect.w = w

    @ property
    def h(self):
        return self.rect.h
    @ h.setter
    def h(self, h):
        self.rect.h = h

    @property
    def size(self):
        return self.rect.size
    @ size.setter
    def size(self,size):
        self.w = size[0]
        self.h = size[1]

    @ property
    def axis(self):
        return self.x,self.y
    @ axis.setter
    def axis(self,axis):
        self.x = axis[0]
        self.y = axis[1]

    @property
    def x(self):
        return self.rect.x

    @x.setter
    def x(self,x):
        # the rect is whole pixels; the leftover is kept so distances stay
        # honest for anything moving slower than a pixel per cycle
        self.rect.x = int(x)
        self.fracX = x-int(x)
    @ property
    def y(self):
        return self.rect.y
    @y.setter
    def y(self,y):
        self.rect.y = int(y)
        self.fracY = y-int(y)
    @property
    def dimension(self):
        return self._dimension
    @dimension.setter
    def dimension(self,dimension):
        self._dimension = dimension

    @property
    def pos(self):
        return *self.axis,self.dimension
    @pos.setter
    def pos(self,pos):
        self.x = pos[0]
        self.y = pos[1]
        self.dimension = pos[2]

    def getByDisplay(self,displayType=None) -> tuple[int,int]:
        displayType = displayType if displayType != None else self.displayType
        return self.getAttr("rect." + displayType.value)

    def copy(self) -> "Rect":
        copied = Rect(self.rect.copy(), self.dimension, self.displayType)
        copied.fracX = self.fracX
        copied.fracY = self.fracY
        return copied

    def calculateDistanceX(self,other:"Rect") -> float:
        return abs((other.rect.centerx+other.fracX) - (self.rect.centerx+self.fracX))

    def calculateDistanceY(self,other:"Rect") -> float:
        return abs((other.rect.centery+other.fracY) - (self.rect.centery+self.fracY))

    def calculateDistance(self,other:"Rect") -> float:
        return self.calculateDistanceX(other) + self.calculateDistanceY(other)

    def __eq__(self, other:"Rect") -> bool:
        if isinstance(other, Rect):
            if not self.sameDimension(other):
                return False
            return self.rect.x == other.rect.x and self.rect.y == other.rect.y and self.rect.w == other.rect.w and self.rect.h == other.rect.h
        return False

    def sameDimension(self,other:"Rect") -> bool:
        return self.dimension == other.dimension

    def collideRectIgnoreDimension(self,other:"Rect") -> bool:
        return self.rect.colliderect(other.rect)

    def containsRect(self,other:"Rect") -> bool:
        return self.sameDimension(other) and self.rect.contains(other)

    def collideRect(self, other:"Rect",additionalRange=0) -> bool:
        return self.sameDimension(other) and self.rect.inflate(additionalRange,additionalRange).colliderect(other.rect)

    def collidePoint(self, x, y, dimension) -> bool:
        return self.dimension == dimension and self.rect.collidepoint(x,y)

    @ property
    def center(self):
        return self.rect.center

    @ center.setter
    def center(self,center):
        self.axis = center[0]-self.w//2,center[1]-self.h//2

    @ property
    def bottomRight(self):
        return self.rect.bottomright
    
    @ bottomRight.setter
    def bottomRight(self,bottomRight):
        self.rect.bottomright = bottomRight

    @ property
    def bottomLeft(self):
        return self.rect.bottomleft
    
    @ bottomLeft.setter
    def bottomLeft(self,bottomLeft):
        self.rect.bottomleft = bottomLeft

    @ property
    def topLeft(self):
        return self.rect.topleft

    @ topLeft.setter
    def topLeft(self,topLeft):
        self.rect.topleft = topLeft

    @ property
    def topRight(self):
        return self.rect.topright
    
    @ topRight.setter
    def topRight(self,topRight):
        self.rect.topright = topRight