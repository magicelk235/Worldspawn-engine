import random
from data.default import aliveObject,rect,inventory
from dataclasses import dataclass

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
		if not npcObject.isCountDown(self.countDownName):
			npcObject.addCountDown(self.countDownName,self.countDown)
			setattr(npcObject,self.setName,set())
			npcObject.addIdGroup(self.setName,lambda x,y:y in getattr(x,self.setName))

	def getSpawnedCount(self,npcObject:"NpcObject"):
		return len(getattr(npcObject,self.setName))

	def canSpawn(self,npcObject:"NpcObject"):
		return npcObject.countDownEnded(self.countDownName,self.countDown) and (not self.needsTarget or npcObject.hasTarget()) and self.getSpawnedCount(npcObject) < self.max

	def update(self,npcObject:"NpcObject"):
		self.npcObjectInit(npcObject)
		if self.canSpawn(npcObject):
			spawnedCount = self.getSpawnedCount(npcObject)
			for i in range(spawnedCount-self.max if spawnedCount+self.amount>self.max else self.amount):
				self.generateObject(npcObject)

	def generateObject(self,npcObject:"NpcObject"):
		path = self.choiceObject()
		pos = self.generatePos(npcObject.getPos())
		id = npcObject.core.getObjectByPath(path)(core=npcObject.core,pos=pos,tag=npcObject.id,**self.initData)
		getattr(npcObject,self.setName).add(id)
		if self.needsTarget:
			npcObject.core.getObject(id).target = npcObject.target


	def generatePos(self,center):
		x = random.randint(-self.radius,self.radius)
		y = random.randint(-self.radius,self.radius)
		return rect.Rect.addPos(center[:2],(x,y))+(center[2],)
	
	def choiceObject(self):
		return random.choice(self.objectList)


@ dataclass
class NpcObjectData(aliveObject.AliveObjectData):
	lootableList:list = []
	spawners:list = []

class NpcObject(aliveObject.AliveObject):
	def __init__(self, core, pos: tuple[3],objectData,tag=None,dictData={}):
		super().__init__(core, pos, objectData, tag, dictData)
		for lootable in self.objectData.lootableList:
			lootable.generateItem(self.inventory,self.core)
	def update(self):
		super().update()

	def updateSpawners(self):
		for spawner in self.objectData.spawners:
			spawner.update(self)