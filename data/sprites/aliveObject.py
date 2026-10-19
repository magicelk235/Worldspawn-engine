import pygame
from dataclasses import dataclass,field
from data.spatial import rect,hitbox
from data.sprites.sprite import Sprite,Animation,SpriteData
from data.inventory import inventory
from data.system import events
from data.emitters import image

@dataclass(frozen=True)
class RideData:
    point:tuple = (0,0)
    max:int = 1
    offset:tuple = (0,0)

@dataclass
class AliveObjectData(SpriteData):
    health:int = 1
    damage:int = 1
    # the share of incoming damage that is absorbed, 0 to 1
    shield:float = 0.0
    speed:int = 1
    react:int = 1
    attackCountDown:int = 1
    visionRadius:int = 200
    inventorySize:int = 5
    rideData:RideData=field(default_factory=RideData)

    def __post_init__(self):
        super().__post_init__()
        # what makes an alive object the one it was before the save: the
        # position already travels in clientData, the rest of the state
        # does not, and a mob that comes back at full health with an empty
        # inventory is a new mob wearing the old one's name. The tag is who
        # it belongs to; without it a pet comes back a stranger to its owner.
        # spawnedBy names which of the owner's spawners made it, so each
        # spawner can tell its own spawns apart again after a load.
        self.saveData = [key for key in ("tag","spawnedBy","health","inventory") if key not in self.saveData] + self.saveData
        
class AliveObject(Sprite):
    eventRegister = events.EventRegister
    
    @staticmethod
    def attackEventTemplate(attacker:str,attacked:str,remaining:int):
        return pygame.event.Event(events.EventRegister.getID("attack"),locals())

    @staticmethod
    def healthChangedEventTemplate(healed:str,currentHealth:int,oldHealth:int):
        return pygame.event.Event(events.EventRegister.getID("healthChanged"),locals())
    
    @staticmethod
    def riderMountEventTemplate(rideID,riderID,remainingSlots):
        return pygame.event.Event(events.EventRegister.getID("riderMount"),locals())
    @ staticmethod
    def riderDismountEventTemplate(rideID,riderID,remainingSlots):
        return pygame.event.Event(events.EventRegister.getID("riderDismount"),locals())

    attackEvent = eventRegister.register("attack",attackEventTemplate)

    healthChangedEvent = eventRegister.register("healthChanged",healthChangedEventTemplate)

    riderMountEvent = eventRegister.register("riderMount",riderMountEventTemplate)

    riderDismount = eventRegister.register("riderDismount",riderDismountEventTemplate)


    # objectData is optional, as it is on Sprite: a saved world and a host's
    # delta rebuild every sprite with cls(core, pos), so a prefab that only
    # overrides getDefaultData has to be buildable from that alone
    def __init__(self, core, pos: tuple[int,int,str],objectData=None,tag=None,dictData={}):
        super().__init__(core, pos,objectData,dictData)
        self._health = 0
        self.resetModifiers()
        self.health = self.objectData.health
        self.tag = tag
        self.spawnedBy = None

        self.temporaryModifiers = []
        self.allies = set()
        self.attacker = None
        self.target = None
        self.inventory = inventory.Inventory(self.objectData.inventorySize,
                                             self.objectData.inventorySize,self)
        # the grid is built at this size directly, without going through the
        # inventorySize setter, so the value it reads back has to be put in
        self._inventorySize = self.objectData.inventorySize
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
        # a target that has left the world is no target, whatever still
        # points at it: a spawner that needs one would keep spawning for
        # something that has already died
        target = self.target
        if target is None:
            return False
        id = getattr(target,"id",None)
        return id is None or self.core.getObject(id) is target

    def getDefaultData(self):
        # the art faces left, so the mirrored frame is the one facing right
        mirror = "@directionX.value"
        self.objectData = AliveObjectData(hitbox.Hitbox(1,1),
                                          {"default":Animation(image.ImageData(flipX=mirror)),
                                           "walk":Animation(image.ImageData(flipX=mirror)),
                                           # a red flash: the tint multiplies the
                                           # frame, so a channel over 255 or a
                                           # zero alpha is not a colour at all
                                           "damage":Animation(imageData=image.ImageData(flipX=mirror,color=(255,60,60,255)))},
                                          # these frames are mirrored as the
                                          # object turns, so the anchor has to
                                          # change sides with them
                                          displayByDirectionX=True)

    def UpdateRidersPos(self):
        # sorted, so a second rider does not swap places with the first one
        # every time the set happens to iterate differently
        for i,riderID in enumerate(sorted(self.riders)):
            rider:"AliveObject" = self.core.getObject(riderID)
            if rider == None:
                continue
            rider.pos = self.pos
            rider.axis = rect.Rect.addPos(rider.axis,self.objectData.rideData.point)
            for _ in range(i):
                rider.axis = rect.Rect.addPos(rider.axis,self.objectData.rideData.offset)

    def getRemainingSlots(self):
        return self.objectData.rideData.max-len(self.riders)

    def removeRider(self,rider:str) -> bool:
        # a rider that dies stops riding the moment its id leaves the world,
        # so whatever was holding onto it can ask to dismount afterwards
        if rider not in self.riders:
            return False
        self.riders.discard(rider)
        self.addEvent(self.riderDismountEventTemplate(self.id,rider,self.getRemainingSlots()))
        self.UpdateRidersPos()
        return True

    def addRider(self,rider: str) -> bool:
        if not (self.isRider(rider) or self.getRemainingSlots()<=0):
            self.riders.add(rider)
            self.addEvent(self.riderMountEventTemplate(self.id,rider,self.getRemainingSlots()))
            self.UpdateRidersPos()
            return True
        return False

    def isRider(self,rider: str) -> bool:
        return rider in self.riders

    def deathCheck(self) -> bool:
        # anything that empties the health bar kills, not only a hit: poison,
        # drowning or a script setting health straight to zero
        if self.health <= 0:
            self.inventory.convertToDrops()
            return True
        return False

    @ property
    def health(self):
        return self._health
    @ health.setter
    def health(self,health:int):
        # hit points are whole: a modifier, a shielded hit or a saved world
        # can all offer a fraction, and half a heart is not a state anything
        # downstream knows how to compare or draw
        health = int(max(health,0))
        health = min(self.maxHealth,health)
        if health == self._health:
            return
        self.addEvent(self.healthChangedEventTemplate(self.id,health,self.health))
        self._health = health

    def fromDict(self,data:dict) -> None:
        # health is clamped against maxHealth, and the ceiling depends on the
        # restored inventory and the other fields, so health goes in last
        super().fromDict({key:value for key,value in data.items() if key != "health"})
        if "health" in data:
            self.health = data["health"]

    @ Sprite.pos.setter
    def pos(self,pos:tuple[int,int,str]) -> None:
        """Move the object, and the box it watches the world through with it.

        Every other way of moving one ends up here: x, y, axis, dimension, a
        teleport, a portal, a respawn, and the core patching a sprite that
        arrived from a save or from a host. Hanging the vision box off the x
        and y setters instead left it behind on all of those, and an object
        whose vision box is somewhere else cannot see what is standing on it.
        """
        Sprite.pos.fset(self,pos)
        # constructing a Spatial assigns a position before resetModifiers has
        # built the box
        vision = getattr(self,"visionRect",None)
        if vision != None:
            vision.center = self.axis
            vision.dimension = self.dimension

    def shareID(self,id:str) -> bool:
        """Whether id is on this object's side.

        One matching tag is enough: an owner and its pet, a pet and its
        owner, or two things spawned by the same parent.
        """
        other = self.core.getObject(id)
        if other == None:
            return False
        tag = getattr(other,"tag",None)
        shared = ((self.tag != None and (self.tag == other.id or self.tag == tag))
                  or (tag != None and tag == self.id))
        if shared and id not in self.allies:
            self.allies.add(id)
        return shared
        

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
        # the ceiling health is clamped against, so it has to be whole too
        self._maxHealth = int(maxHealth)
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
        # a share of incoming damage, so it is fractional by definition even
        # when the content that declares it writes a plain 0. Without this,
        # a modifier keeps the stat the kind of number it found and every
        # piece of armour rounds itself away to nothing.
        self._shield = float(shield)

    @ property
    def visionRadius(self):
        return self._visionRadius

    @ visionRadius.setter
    def visionRadius(self,visionRadius:int):
        self._visionRadius = visionRadius
        vision = getattr(self,"visionRect",None)
        if vision == None:
            self.visionRect = rect.Rect(pygame.rect.Rect(*self.axis,visionRadius,visionRadius),
                                        self.dimension)
        else:
            vision.size = (visionRadius,visionRadius)
        self.visionRect.rect.center = self.axis

    def resetModifiers(self) -> None:
        # straight to the field, not through the setter: this is the first
        # step of a stat rebuild, and clamping health against the bare maximum
        # here cut it down every cycle before the items that raise the ceiling
        # had their turn. Inventory.applyModifiers clamps once it is done.
        self._maxHealth = int(self.objectData.health)
        self.damage: int = self.objectData.damage
        self.attackCountDown = self.objectData.attackCountDown
        self.shield: float = self.objectData.shield
        self.speed: int = self.objectData.speed
        self.react: int = self.objectData.react
        self.visionRadius:int = self.objectData.visionRadius
        
    def applyTimedModifiers(self) -> None:
        """Hook for effects that outlive a stat reset.

        Inventory.applyModifiers calls this after the items have had their
        say, so a timed effect lands on top of a modifier that sets a stat
        outright instead of being wiped by it.
        """
        pass

    def attack(self, attacked) -> None:
        attacked.applyDamage(self.damage,self)
        
    def applyDamage(self, damage, attacker=None) -> None:
        attackerID = attacker.id if attacker != None else None
        if attacker != None and not self.shareID(attackerID):
            self.attacker = attacker
            for id in self.allies:
                ally = self.core.getObject(id)
                if ally != None:
                    ally.attacker = self.attacker
        # a share of the hit, so at most all of it: armour stacked past 1.0
        # would turn every hit into healing
        self.health -= round(damage * (1.00 - min(self.shield,1.0)))
        self.addEvent(self.attackEventTemplate(attackerID,self.id,self.health))

    def update(self) -> bool:
        super().update()
        # riders are carried: whatever moved the mount this cycle has to move
        # them with it, or they are left standing where they got on
        self.UpdateRidersPos()
        # a slot emptied by spending its last item still carries the old item
        # until this runs, so anything asking the inventory what it holds
        # would keep getting the spent name back
        self.inventory.update()
        return self.deathCheck()