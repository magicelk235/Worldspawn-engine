import random
from data.inventory import inventory
from data.spatial import rect
from data.sprites import aliveObject
from dataclasses import dataclass, field

@ dataclass
class Lootable:
	itemID:str
	count:int = 1
	chance:float = 1.0
		
	def generateItem(self,inventory:inventory.Inventory,core):
		if random.random() < self.chance:
			if isinstance(self.itemID,set):
				item = random.choice(list(self.itemID))
			else:
				item = self.itemID
			inventory.addItemByCount(core.getItem(item)(),self.count)


@ dataclass
class Spawner:
	index:int
	options:list["NpcObject"]
	amount:int
	radius:int 
	countDown:int
	max:int
	needsTarget:bool
	initData:dict[str:any]

	def __post_init__(self):
		self.countDownName = "spawner"+str(self.index)
		self.setName = "spawnedObjects"+str(self.index)

	def npcObjectInit(self,npcObject:"NpcObject"):
		if not npcObject.isTimer(self.countDownName):
			npcObject.addTimer(self.countDownName,self.countDown,True)
			setattr(npcObject,self.setName,set())
			npcObject.addIdGroup(self.setName,lambda x,y:y in getattr(x,self.setName))

	def getSpawnedCount(self,npcObject:"NpcObject"):
		return len(getattr(npcObject,self.setName))

	def canSpawn(self,npcObject:"NpcObject"):
		return npcObject.timerEnded(self.countDownName) and (not self.needsTarget or npcObject.hasTarget()) and self.getSpawnedCount(npcObject) < self.max

	def update(self,npcObject:"NpcObject"):
		self.npcObjectInit(npcObject)
		if self.canSpawn(npcObject):
			spawnedCount = self.getSpawnedCount(npcObject)
			for i in range(spawnedCount-self.max if spawnedCount+self.amount>self.max else self.amount):
				self.generateObject(npcObject)

	def generateObject(self,npcObject:"NpcObject"):
		prefabPath = self.choiceObject()
		pos = self.generatePos(npcObject.pos)
		id = npcObject.core.getObjectByPrefabPath(prefabPath)(core=npcObject.core,pos=pos,tag=npcObject.id,**self.initData)
		getattr(npcObject,self.setName).add(id)
		if self.needsTarget:
			npcObject.core.getObject(id).target = npcObject.target


	def generatePos(self,center):
		x = random.randint(-self.radius,self.radius)
		y = random.randint(-self.radius,self.radius)
		return rect.Rect.addPos(center[:2],(x,y))+(center[2],)
	
	def choiceObject(self):
		return random.choice(self.options)


@ dataclass
class NpcObjectData(aliveObject.AliveObjectData):
	lootableList:list = field(default_factory=list)
	spawners:list = field(default_factory=list)

class NpcObject(aliveObject.AliveObject):
	def __init__(self, core, pos: tuple[int,int,str],objectData,tag=None,dictData={}):
		super().__init__(core, pos, objectData, tag, dictData)
		for lootable in self.objectData.lootableList:
			lootable.generateItem(self.inventory,self.core)
	def update(self):
		super().update()

	def updateSpawners(self):
		for spawner in self.objectData.spawners:
			spawner.update(self)