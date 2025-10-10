from uuid import uuid4
class IDManager:
	def __init__(self,mainGroup:dict):
		self.usedIDs = set()
		self.group:dict = mainGroup
		
	def idUsed(self,id:str) -> bool:
		return id in self.usedIDs
		
	def generateID(self) -> str:
		while True:
			id = str(uuid4())
			print(id)
			if not self.idUsed(id):
				return id
		
	def getObject(self,id:str) -> any:
		return self.group.get(id)

	def addObject(self,object) -> str:
		id = self.generateID()
		self.addObjectByID(object,id)
		return id
		
	def addObjectByID(self,object,id:str) -> None:
		self.usedIDs.add(id)
		self.group[id] = object
		object.id = id
		
	def objectExist(self,id:str) -> bool:
		return self.idUsed(id)

	def removeObject(self,object) -> None:
		self.removeObjectByID(object.id)
		
	def removeObjectByID(self,id) -> None:
		self.usedIDs.remove(id)
		self.group.pop(id)