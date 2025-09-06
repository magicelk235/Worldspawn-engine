from dataclasses import dataclass
from enum import Enum
from data.managers.timeManager import Timer


class Mode(Enum):
	Set = 0
	MaxSet = 1
	MinSet = 2
	Add = 3
	Mul = 4

	def applySetMode(self,value,amount):
		return amount
	def applyMaxSetMode(self,value,amount):
		return max(value,amount)
	def applyMinSetMode(self,value,amount):
		return min(value,amount)
	def applyAddMode(self,value,amount):
		return value+amount
	def applyMulMode(self,value,amount):
		return value*amount

	def apply(self,value,amount):
		getattr(self,f"apply{self.name}Mode")(value,amount)

@ dataclass(frozen=True)
class Modifier:
	name:str
	amount:int|float
	mode:Mode = Mode.Set


	def canBeApllied(self,hand):
		return self.handNeeded and not hand

	def apply(self,object,hand=False):
		if self.canBeApllied(hand):
			object.setAttr(self.name,self.mode.apply(object.getAttr(self.name),self.amount))

	@staticmethod
	def applyForList(modifiers,object,hand=False):
		for modifier in modifiers:
			modifier.apply(object,hand)

@ dataclass(frozen=True)
class TemporaryModifier(Timer,Modifier):
	countDown:int

	def update(self):
		if self.ended():
			return True

	def __eq__(self, other):
		if isinstance(other,TemporaryModifier):
			return self.__hash__() == other.__hash__()
		return False

	def __hash__(self):
		return super().__hash__()