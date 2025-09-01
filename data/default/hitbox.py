from data.default import rect
import pygame
class Hitbox:
    def __init__(self,w:int,h:int,xOffset:int=0,yOffset:int=0):
        self.w = w
        self.h = h
        self.xOffset = xOffset
        self.yOffset = yOffset

    def changeSize(self,w:int,h:int):
        self.w = w
        self.h = h

    def getCenter(self) -> tuple[int,int]:
        return self.w//2,self.h//2

    def updateRect(self,hitbox,pos) -> None:
        hitbox.setX(pos[0] + self.xOffset)
        hitbox.setY(pos[1] + self.yOffset)
        hitbox.setDimension(pos[2])
        
    def getRect(self,pos:tuple) -> rect.Rect:
        return rect.Rect(pygame.rect.Rect(*pos[:2], self.w, self.h), pos[2])