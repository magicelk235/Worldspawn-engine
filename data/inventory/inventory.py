class InventoryItem:
	def __init__(self, item=None, count=0):
		self.item = item
		self.count = count


	# checks
	def needsToBeEmpty(self):
		return self.isEmpty() and self.getItemName() != "none"

	def sameName(self,name):
		return self.getItemName() == name

	def sameItemType(self,item):
		return self.sameName(item.getItemName())

	def isEmpty(self):
		return self.getCount() == 0



	# getters

	def getItemName(self):
		return self.getItem().getName()

	def getItem(self):
		return self.item

	def getCount(self):
		return self.count

	def getMax(self):
		return self.getItem().getMax()



	# count functions
	def setCount(self,count):
		self.count = count

	def addCount(self,count):
		if self.canAddCount(count):
			self.setCount(self.getCount()+count)
			return True
		return False

	def canAddCount(self,count):
		return self.getCount() + count <= self.getMax()

	def decCount(self,count):
		if self.canDecCount(count):
			self.setCount(self.getCount()-count)
			return True
		return False

	def canDecCount(self,count):
		return self.getCount() - count >= 0



	# inventory functions
	def copy(self, item):
		self.item = item.getItem()
		self.count = item.count
		

	def move(self,item,core):
		self.copy(item)
		item.clear(core)

	def clear(self,core):
		self.item = core.getItems("none")()
		self.count = 0
		
	def replace(self,item):
		self.count,item.count = item.count,self.count
		self.item,item.item = item.item,self.item

	def merge(self,item,core):
		if self.sameItemType(item):
			if self.canAddCount(item.getCount()):
				self.addCount(item.getCount())
				item.clear(core)
			else:
				item.decCount(self.getMax()-self.getCount())
				self.setCount(self.getMax())
			return True
		return False

	# modifiers

	def applyModifiers(self,object,hand=False):
		self.getItem().applyModifiers(object,hand)

	def __eq__(self, other):
		if isinstance(other,InventoryItem):
			if other.count == self.count and other.item == self.item:
				return True
		return False

class Inventory:
	def __init__(self,w,h,owner):
		self.inventory:list[list[InventoryItem]] = [[InventoryItem(count=0) for i in range(w)]for j in range(h)]
		self.copyListInventory:list[InventoryItem] = self.toRawList()
		self.size = (w,h)
		self.owner = owner
		self.handPos = (4,4)
		self.clearInventory()



	# getters
	def getItem(self,w,h) ->InventoryItem:
		return self.inventory[h][w]

	def getSize(self):
		return self.size
		
	def getH(self):
		return self.size[1]
		
	def getW(self):
		return self.size[0]

	def getHandItem(self):
		return self.getItem(*self.handPos)

	def getItemByName(self, name):
		try:
			return self.getItem(*self.findItem(name))
		except:
			return None



	# setters
	def setSize(self,size):
		self.size = size
		
	def setH(self,h):
		
		self.size = (self.w,h)
	def setW(self,w):
		self.size = (w,self.h)



	# inventory functions
	def findItem(self, name):
		for w in range(self.getW()):
			for h in range(self.getH()):
				if self.getItem(w,h).sameName(name):
					return [w, h]
		return None

	def canAddItemAt(self,w,h,item):
		if not self.getItem(w,h).sameItemType(item):
			return False
		return self.getItem(w,h).canAddCount(item.GetCount())

	def addItemByCount(self,item,count):
		return self.addItem(InventoryItem(item,count))

	def addItem(self, item):
		for h in range(self.getH()):
			for w in range(self.getW()):
				if self.getItem(w,h).sameItemType(item):
					if self.getItem(w,h).addCount(item.getCount()):
						self.applyModifiers()
						return True
		for h in range(self.getH()):
			for w in range(self.getW()):
				if self.getItem(w,h).isEmpty():
					self.getItem(w,h).copy(item)

					self.applyModifiers()
					return True
		return False

	def removeItemByAmount(self, name, count):
		for h in range(self.getH()):
			for w in range(self.getW()):
				if self.getItem(w,h).sameName(name) and self.getItem(w,h).decCount(count):
					self.applyModifiers()
					return True
		return False

	def removeAt(self,w,h):
		self.clearItem(w,h)
		self.applyModifiers()

	def removeItem(self, name):
		try:
			self.removeAt(self.findItem(name))
			return True
		except:
			return False

	def hasItemAt(self,w,h,name,count=-1):
		return self.getItem(w,h).sameName(name) and (count == -1 or self.getItem(w,h).canDecCount(count))

	def hasItem(self, name, count=-1):
		for h in range(self.getH()):
			for w in range(self.getW()):
				if self.hasItemAt(w,h,name,count):
					return True
		return False

	def hasItemInHand(self, name, count=None):
		return self.hasItemAt(*self.handPos,name,count)

	def update(self):
		for row in self.inventory:
			for item in row:
				if item.needsToBeEmpty():
					item.clear(self.owner.core)
		self.applyModifiers()

	def clearItem(self,w,h):
		self.getItem(w,h).clear(self.owner.core)

	def clearInventory(self):
		for w in range(self.getW()):
			for h in range(self.getH()):
				self.clearItem(w,h)
		self.applyModifiers()

	def toRawList(self):
		itemList = []
		for row in self.inventory:
			itemList = itemList + row
		return itemList
	
	def toList(self):
		return self.copyListInventory
	# modifiers
	def applyModifiers(self):
		self.owner.resetModifiers()
		self.getHandItem().applyModifiers(self.owner,True)
		usedNames = set()
		for row in self.inventory:
			for item in row:
				if item.getItemName() not in usedNames:
					usedNames.add(item.getItemName())
					item.applyModifiers(self.owner)


	# interaction
	def interact(self,w1,h1,w2,h2):
		if w1==w2 and h1==h2:
			return
		if not self.getItem(w1,h1).merge(self.getItem(w2,h2),self.owner.core):
			self.getItem(w1,h1).replace(self.getItem(w2,h2))



	# load/copy function

	def copy(self,other):
		self.inventory = other.inventory
		self.w = other.w
		self.h = other.h
		self.owner = other.owner
		self.handPos =  other.handPos

	def drop(self,w,h):
		if not self.getItem(w,h).isEmpty():
			self.removeAt(w,h)
			self.applyModifiers()

	def convertToDrops(self):
		for w in range(self.getW()):
			for h in range(self.getH()):
				self.drop(w,h)