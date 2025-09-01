
from data.default import default,events
class Modifier:
	def __init__(self,name,amount,setMode=True,handNeeded=True,chooseBigger=True,percent=False):
		"""
		:param name: damage,shield,max_health
		:param amount: either int or float(%)
		:param set: false for add, true for set
		:param handNeeded: if the modifier needs in the hand slot
		"""
		self.name = name
		self.amount = amount
		self.setMode = setMode
		self.handNeeded = handNeeded
		self.chooseBigger = chooseBigger
		self.percent = percent

	def __eq__(self, other):
		if isinstance(other,Modifier):
			return self.__hash__() == other.__hash__()
		return False

	@staticmethod
	def find(name,list):
		for object in list:
			if object.name == name:
				return object
			
	@staticmethod
	def get(name,list):
		for object in list:
			if object.name == name:
				return object.amount

	def __hash__(self):
		return hash(tuple(self.__dict__.items()))

	def canBeApllied(self,hand):
		return self.handNeeded and not hand

	def apply(self,object,hand=False):
		if self.canBeApllied(hand):
				if self.setMode:
					if self.chooseBigger and default.getAttr(object,self.name) < self.amount:
						default.setAttr(object,self.name,self.amount)
					elif not self.chooseBigger:
						default.setSttr(object, self.name, self.amount)
				else:
					if self.percent:
						if isinstance(default.getAttr(object,self.name),float):
							value = default.getAttr(object,self.name)*(self.amount+1.0)
							value = int(value*10)
							default.setAttr(object, self.name,value)
						else:
							default.setAttr(object,self.name,int(default.getAttr(object,self.name)*(self.amount+1.0)))
					else:
						default.setAttr(object, self.name, default.getAttr(object, self.name)+self.amount)
	@staticmethod
	def applyForList(modifiers,object,hand=False):
		for modifier in modifiers:
			modifier.apply(object,hand)

class TemporaryModifier:
	def __init__(self,modifier,cooldown):
		self.modifier = modifier
		self.cooldown = cooldown

	def update(self,core):
		if core.eventHappend(events.timer):
			self.cooldown -= 1
			if self.cooldown == 0:
				return True

	def __eq__(self, other):
		if isinstance(other,TemporaryModifier):
			return self.__hash__() == other.__hash__()
		return False

	def __hash__(self):
		return self.modifier.__hash__()
		
	def apply(self,object,rightClicked,hand):
		self.modifier.apply(object,rightClicked,hand)