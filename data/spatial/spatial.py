import pygame
from dataclasses import dataclass
from data.core import events

from data.common.runnable import Runnable
from sympy import cos,sin,pi
class Spatial(Runnable):


    @ dataclass
    class Vector:
        direction:tuple[int,int]
        time:float = 0.02 
        speed:int = None

        @ property
        def opposedDirection(self) -> int:
            return self.direction[0]*-1,self.direction[1]*-1

        def decTime(self) -> bool:
            self.time -= 0.02
            return self.time <= 0

        def getSpeed(self,spatial:"Spatial"):
            return spatial.speed if self.speed == None else self.speed

        def calculateDelta(self) -> tuple[float,float]:
            speed = self.getSpeed
            dx = speed*self.direction[0]
            dy = speed*self.direction[1]
            return dx, dy

        def update(self,spatial:"Spatial") -> bool:
            spatial.axis = self.calculateDelta()
            return self.decTime()

        def mergeOpposeds(self,vectors) -> None:
            other:"Spatial.Vector" = vectors.get(self.opposedDirection)
            if other != None:
                if self.speed == other.speed:
                    if self.time > other.time:
                        vectors.pop(other.direction)
                        self.time -= other.time
                    elif self.time < other.time:
                        vectors.pop(self.direction)
                        other.time -= self.time
                    else:
                        vectors.pop(self.direction)
                        vectors.pop(other.direction)

    @staticmethod
    def moveEventTemplate(objectID):
        return pygame.event.Event(events.EventRegister.getID("move"),locals())
    moveEvent = events.EventRegister.register("move",moveEventTemplate) 
    def __init__(self,core,pos:tuple[int,int,str]=(0,0,"world")):
        super().__init__(core)
        self.pos = pos
        self.vectors:dict[tuple[int,int]:"Spatial.Vector"] = {}
        self.speed = 1

    @ property
    def speed(self):
        return self._speed
    @ speed.setter
    def speed(self,speed):
        self._speed = speed

    @ property
    def pos(self) -> tuple[int,int,str]:
        return self.pos

    @ property
    def axis(self) -> tuple[int,int]:
        return self.x,self.y
    
    @ property
    def x(self) -> int:
        return self.pos[0]
    
    @ property
    def y(self) -> int:
        return self.pos[1]
    
    @ property
    def dimension(self) -> int:
        return self.pos[2]
    @ x.setter
    def x(self,x:int) -> None:
        self.pos = (x,)+(self.y,)+(self.dimension,)
        self.objectData.hitbox.updateRect(self.rect, self.pos)
        self.addEvent(self.moveEventTemplate(self.id))
    @ y.setter
    def y(self,y:int) -> None:
        self.pos = (y,)+(self.x,)+(self.dimension,)
        self.objectData.hitbox.updateRect(self.rect, self.pos)
        self.addEvent(self.moveEventTemplate(self.id))
    
    @ axis.setter
    def axis(self,axis:tuple[int,int]) -> None:
        self.x = axis[0]
        self.y = axis[1]

    @ pos.setter
    def pos(self,pos:tuple[int,int,str]) -> None:
        self.x = pos[0]
        self.y = pos[1]
        self.dimension = pos[2]
        
    @ dimension.setter
    def dimension(self,dimension:str) -> None:
        self.pos = self.getAxis+(dimension,)
        self.rect.dimension = dimension
        self.addEvent(self.moveEventTemplate(self.id))

    @ staticmethod
    def convertAngleToDirection(angle) -> tuple[float,float]:
        return (cos(angle*pi/180),sin(angle*pi/180))

    def addExcluciveVector(self,direction:tuple[int,int],time:float,speed:int=None) -> None:
        if direction not in self.vectors:
            self.addVector(direction,time,speed)

    def addVector(self,direction:tuple[int,int],time:float,speed:int=None) -> None:
        if speed == None:
            speed = self.speed
        vector = self.Vector(direction,time,speed)
        other = self.vectors.get(direction)
        if other != None:
            other.time += vector.time
        else:
            self.vectors[vector.direction] = vector
        vector.mergeOpposeds(self.vectors)
        
    def updateVectors(self) -> None:
        if self.moveable:
            if self.core.eventHappened(self.timerEvent):
                for vector in list(self.vectors.values()):
                    if vector.update(self):
                        del self.vectors[vector.direction]