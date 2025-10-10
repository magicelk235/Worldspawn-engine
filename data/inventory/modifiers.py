from dataclasses import dataclass
from enum import Enum
from data.managers.timeManager import Timer


class Mode(Enum):
    Set = 0
    MaxSet = 1
    MinSet = 2
    Add = 3
    Mul = 4


    @staticmethod
    def applySetMode(value, amount):
        return amount
    @staticmethod
    def applyMaxSetMode(value,amount):
        return max(value,amount)
    @staticmethod
    def applyMinSetMode(value,amount):
        return min(value,amount)
    @staticmethod
    def applyAddMode(value,amount):
        return value+amount
    @staticmethod
    def applyMulMode(value,amount):
        return value*amount

    def apply(self,value,amount):
        return getattr(self,f"apply{self.name}Mode")(value,amount)

@ dataclass(frozen=True)
class Modifier:
    name:str
    amount:int|float
    mode:Mode = Mode.Set
    handNeeded:bool = True


    def canBeApplied(self, hand):
        return self.handNeeded and not hand

    def apply(self,object,hand=False):
        if self.canBeApplied(hand):
            object.setAttr(self.name,self.mode.apply(object.getAttr(self.name),self.amount))

    @staticmethod
    def applyForList(modifiers,object,hand=False):
        for modifier in modifiers:
            modifier.apply(object,hand)

@ dataclass(frozen=True)
class TemporaryModifier(Timer,Modifier):
    countDown:int

    def update(self):
        return self.ended()

    def __eq__(self, other):
        if isinstance(other,TemporaryModifier):
            return self.__hash__() == other.__hash__()
        return False

    def __hash__(self):
        return super().__hash__()