import pygame
from dataclasses import dataclass,field
from data.spatial import rect,hitbox
from data.sprites.sprite import Sprite,Animation,SpriteData
from data.inventory import inventory
from data.core import events
from data.emitters import image

@dataclass(frozen=True)
class RideData:
    point:tuple = (0,0)
    max:int = 1
    offset:tuple = (0,0)

@dataclass
class AliveObjectData(SpriteData):
    save:list = field(default_factory=list)
    health:int = 1
    damage:int = 1
    shield:int = 1
    speed:int = 1
    react:int = 1
    attackCountDown:int = 1
    visionRadius:int = 200
    inventorySize:int = 5
    rideData:RideData=field(default_factory=RideData)

    def __post_init__(self):
        super().__post_init__()
        self.save+=["rect","objectType"]
        
class AliveObject(Sprite):
    eventRegister = events.EventRegister
    
    @staticmethod
    def attackEventTemplate(attacker:str,attacked:str,remaining:int):
        return pygame.event.Event(events.EventRegister.getID("attack"),locals())

    @staticmethod
    def healthChangedEventTemplate(healed:str,currentHealth:int,oldHealth:int):
        return pygame.event.Event(events.EventRegister.getID("attack"),locals())
    
    @staticmethod
    def riderMountEventTemplate(rideID,riderID,remainingSlots):
        return pygame.event.Event(events.EventRegister.getID("riderMount"))
    @ staticmethod
    def riderDismountEventTemplate(rideID,riderID,remainingSlots):
        return pygame.event.Event(events.EventRegister.getID("riderDismount"))

    attackEvent = eventRegister.register("attack",attackEventTemplate)

    healthChangedEvent = eventRegister.register("healthChanged",healthChangedEventTemplate)

    riderMountEvent = eventRegister.register("riderMount",riderMountEventTemplate)

    riderDismount = eventRegister.register("riderDismount",riderDismountEventTemplate)


    def __init__(self, core, pos: tuple[int,int,str],objectData,tag=None,dictData={}):
        super().__init__(core, pos,objectData)
        self._health = 0
        self.resetModifiers()
        self.health = self.objectData.health
        self.tag = tag

        self.temporaryModifiers = []
        self.allies = set()
        self.attacker = None
        self.target = None
        self.inventory = inventory.Inventory(5,5,self)
        self.riders:set[str] = set()
        self.ride = None
        self.addIdGroup("riders",self.isRider)
        self.addIdGroup("allies",self.shareID)
        
    @ property
    def target(self):
        return self._target
    @ target.setter
    def target(self,target):
        self._target = target

    def hasTarget(self):
        return self.target is not None

    def getDefaultData(self):
        self.objectData = AliveObjectData(hitbox.Hitbox(1,1),{"default":Animation(image.ImageData(flipX="@directionX")),"walk":Animation(image.ImageData(flipX="@directionX")),"damage":Animation(imageData=image.ImageData(flipX="@directionX",color=(270,0,0,0)))})

    def UpdateRidersPos(self):
        for i in range(len(self.riders)):
            riderID = self.riders[i]
            rider:"AliveObject" = self.core.getObject(riderID)
            rider.pos = self.pos
            rider.axis += self.objectData.rideData.point
            for _ in range(i):
                rider.axis += self.objectData.rideData.offset

    def getRemainingSlots(self):
        return len(self.riders)-self.objectData.rideData.max

    def removeRider(self,rider:str):
        self.riders.remove(rider)
        self.addEvent(self.riderDismountEventTemplate(self.id,rider,self.getRemainingSlots()))
        self.UpdateRidersPos()

    def addRider(self,rider: str) -> bool:
        if not (self.isRider(rider) or self.getRemainingSlots()==0):
            self.riders.add(rider)
            self.addEvent(self.riderMountEventTemplate(self.id,rider,self.getRemainingSlots()))
            self.UpdateRidersPos()
            return True
        return False

    def isRider(self,rider: str) -> bool:
        return rider in self.riders

    def deathCheck(self) -> bool:
        if self.eventHappened(self.attackEvent):
            if self.health == 0:
                self.inventory.convetToDrops()
                return True
        return False

    @ property
    def health(self):
        return self._health
    @ health.setter
    def health(self,health:int):
        health = max(health,0)
        health = min(self.maxHealth,health)
        self.addEvent(self.healthChangedEventTemplate(self.id,health,self.health))
        self._health = health

    @ Sprite.x.setter
    def x(self,x:int) -> None:
        Sprite.x.fset(self,x)
        self.visionRect.center = self.axis

    @ Sprite.y.setter
    def y(self,y:int) -> None:
        Sprite.y.fset(self,y)
        self.visionRect.center = self.axis

    @ Sprite.dimension.setter
    def dimension(self,dimension:str) -> None:
        Sprite.dimension.fset(self,dimension)
        self.visionRect.dimension = dimension

    def shareID(self,id:str) -> bool:
        other = self.core.getObject(id)
        if hasattr(other,"tag"):
            if self.id == other.tag and self.tag == other.id and self.tag == other.tag:
                if id not in self.allies:
                    self.allies.add(id)
                return True
        return False
        

    def collideVisionCheck(self,other:"AliveObject") -> bool:
        return other.collideCheckRect(self.visionRect)

    @ property
    def inventorySize(self) -> int:
        return self._inventorySize
    
    @ inventorySize.setter
    def inventorySize(self,inventorySize):
        self._inventorySize = inventorySize
        self.inventory.size = (inventorySize,inventorySize)


    @property
    def maxHealth(self):
        return self._maxHealth
    @ maxHealth.setter
    def maxHealth(self,maxHealth):
        self._maxHealth = maxHealth
        self.health = self.health
    @ property
    def damage(self):
        return self._damage
    @ damage.setter
    def damage(self,damage):
        self._damage = damage
    @property
    def attackCountDown(self):
        return self._attackCountDown
    @ attackCountDown.setter
    def attackCountDown(self,attackCountDown):
        self._attackCountDown = attackCountDown
    @ property
    def shield(self):
        return self._shield
    @ shield.setter
    def shield(self,shield:float):
        self._shield = shield

    @ property
    def visionRadius(self):
        return self._visionRadius

    @ visionRadius.setter
    def visionRadius(self,visionRadius:int):
        self._visionRadius = visionRadius
        try:
            self.visionRect.setSize(self.visionRadius,self.visionRadius)
        except:
            self.visionRect:rect.Rect = rect.Rect(pygame.rect.Rect(*self.axis,self.visionRadius,self.visionRadius),self.dimension)
        self.visionRect.rect.center = self.axis

    def resetModifiers(self) -> None:
        self.maxHealth: int = self.objectData.health
        self.damage: int = self.objectData.damage
        self.attackCountDown = self.objectData.attackCountDown
        self.shield: float = self.objectData.shield
        self.speed: int = self.objectData.speed
        self.react: int = self.objectData.react
        self.visionRadius:int = self.objectData.visionRadius
        
    def attack(self, attacked) -> None:
        attacked.applyDamage(self.damage)
        
    def applyDamage(self, damage, attacker=None) -> None:
        if self.timers.get("damage", None) == None:
            self.timers["damage"] = 0
        if attacker != None and not self.shareID(attacker,self.id):
            self.attacker = attacker
            for id in self.allies:
                self.core.getObject(id).attacker = self.attacker
        self.health -= round(damage * (1.00 - self.shield))
        self.addEvent(self.attackEventTemplate(attacker.id,self.id,self.health))

    def update(self) -> bool:
        super().update()
        return self.deathCheck()