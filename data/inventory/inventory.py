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
		# handed out by toList(); the same list object is kept and refilled so
		# a widget holding it keeps seeing the current slots
		self.copyListInventory:list[InventoryItem] = self.toRawList()
		self._size = (w,h)
		self.owner = owner
		# first cell of the first row. Legacy drew its hotbar from the last
		# row and held the hand there; here row zero is the hotbar, so a hand
		# anywhere else is a slot the hotbar never shows and the held item
		# would be one the player cannot see or select
		self.handPos = (0,0)
		self.clearInventory()

	@ property
	def height(self):
		return self.size[1]

	@height.setter
	def height(self, height):
		self.size = (self.size[0],height)

	@ property
	def width(self):
		return self.size[0]

	@width.setter
	def width(self, width):
		self.size = (width,self.size[1])

	@ property
	def handPos(self):
		return self._handPos
	@handPos.setter
	def handPos(self,value:tuple[int,int]):
		# the hand is a slot, so it has to name one that exists. A saved
		# world, a client delta or a grid that shrank can all offer a cell
		# past the edge, and every read of the hand goes through getItem
		w,h = self.size
		self._handPos = (min(max(int(value[0]),0),w-1),min(max(int(value[1]),0),h-1))


	@ property
	def size(self):
		return self._size
	@size.setter
	def size(self, value:tuple[int,int]):
		w,h = value[0],value[1]
		if getattr(self,"_size",None) == (w,h):
			return
		self._size = (w,h)
		self.reshape(w,h)

	def reshape(self,w,h) -> None:
		"""Grow or shrink the grid, keeping whatever still fits."""
		rows = []
		for y in range(h):
			row = []
			for x in range(w):
				if y < len(self.inventory) and x < len(self.inventory[y]):
					row.append(self.inventory[y][x])
				else:
					row.append(InventoryItem(count=0))
			rows.append(row)
		self.inventory = rows
		self.refreshList()
		self.handPos = self.handPos
		owner = getattr(self,"owner",None)
		if owner != None:
			for y in range(h):
				for x in range(w):
					if self.getItem(x,y).getItem() == None:
						self.clearItem(x,y)
			self.applyModifiers()


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
		return self.getItem(w,h).canAddCount(item.getCount())

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
		pos = self.findItem(name)
		if pos == None:
			return False
		self.removeAt(*pos)
		return True

	def hasItemAt(self,w,h,name,count=-1):
		return self.getItem(w,h).sameName(name) and (count == -1 or self.getItem(w,h).canDecCount(count))

	def hasItem(self, name, count=-1):
		for h in range(self.getH()):
			for w in range(self.getW()):
				if self.hasItemAt(w,h,name,count):
					return True
		return False

	def hasItemInHand(self, name, count=-1):
		return self.hasItemAt(*self.handPos,name,count)

	def update(self):
		self.applyModifiers()

	def dropSpentStacks(self) -> None:
		"""Empty out any slot whose last item was used up.

		A slot that ran to zero still names what used to be in it, so it
		keeps answering hasItem, keeps being what the hand holds, and keeps
		handing its modifiers to the owner. Every caller that spends an item
		rebuilds the stats afterwards, so that is where the sweep belongs.
		"""
		for row in self.inventory:
			for item in row:
				if item.needsToBeEmpty():
					item.clear(self.owner.core)

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

	def refreshList(self) -> None:
		self.copyListInventory[:] = self.toRawList()

	def toList(self):
		return self.copyListInventory
	# modifiers
	def applyModifiers(self):
		self.dropSpentStacks()
		self.owner.resetModifiers()
		self.getHandItem().applyModifiers(self.owner,True)
		usedNames = set()
		for row in self.inventory:
			for item in row:
				if item.getItemName() not in usedNames:
					usedNames.add(item.getItemName())
					item.applyModifiers(self.owner)
		# timed effects go on top of the items, the way legacy ordered it:
		# an item that sets a stat outright must not wipe a live effect
		self.owner.applyTimedModifiers()


	# interaction
	def interact(self,w1,h1,w2,h2):
		if w1==w2 and h1==h2:
			return
		if not self.getItem(w1,h1).merge(self.getItem(w2,h2),self.owner.core):
			self.getItem(w1,h1).replace(self.getItem(w2,h2))
		# either slot can be the hand, so the stat block has to follow the
		# move the same way it follows an add or a remove
		self.applyModifiers()



	# load/copy function

	def copy(self,other):
		self.inventory = other.inventory
		self.refreshList()
		self._size = other.size
		self.owner = other.owner
		self.handPos = other.handPos

	# serialization: Sendable picks these up for anything that lists
	# "inventory" in its client or save data
	def toDict(self):
		return {"size":list(self.size),
				"handPos":list(self.handPos),
				"items":[[[item.getItemName(),item.getCount()] for item in row]
						 for row in self.inventory]}

	def fromDict(self,data):
		rows = data.get("items")
		if rows == None:
			return
		size = data.get("size")
		if size != None:
			self.size = (size[0],size[1])
		handPos = data.get("handPos")
		if handPos != None:
			self.handPos = (handPos[0],handPos[1])
		core = self.owner.core
		# the slots themselves are reused: widgets were handed these objects
		# by toList() and would otherwise keep showing the pre-load contents
		self.clearInventory()
		for h,row in enumerate(rows):
			if h >= self.getH():
				break
			for w,entry in enumerate(row):
				if w >= self.getW():
					break
				name,count = entry[0],entry[1]
				itemClass = core.getItems(name)
				if itemClass == None or count <= 0:
					continue
				slot = self.getItem(w,h)
				slot.item = itemClass()
				slot.count = count
		self.refreshList()
		self.applyModifiers()

	def drop(self,w,h):
		if not self.getItem(w,h).isEmpty():
			self.removeAt(w,h)

	def convertToDrops(self):
		for w in range(self.getW()):
			for h in range(self.getH()):
				self.drop(w,h)