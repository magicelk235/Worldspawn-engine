from dataclasses import dataclass
from enum import Enum


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
        # a hand-only modifier counts once the item is actually held; one
        # that does not need the hand always counts
        return hand or not self.handNeeded

    @staticmethod
    def matchType(current,value):
        """Keep a stat the kind of number it already was.

        A stat is whole because what it counts is whole: hit points, cycles
        of cooldown, pixels of speed. A x1.25 potion that leaves 12.5 maximum
        hit points behind pushes a number that cannot exist through every
        comparison, clamp and label downstream. Legacy truncated its percent
        modifiers the same way and only kept a fraction where the stat was
        already fractional, which is the shield and cooldown case.
        """
        if isinstance(current,bool) or not isinstance(current,(int,float)):
            return value
        if isinstance(value,bool) or not isinstance(value,(int,float)):
            return value
        if isinstance(current,int):
            return int(value)
        return float(value)

    def apply(self,object,hand=False):
        if self.canBeApplied(hand):
            current = object.getAttr(self.name)
            object.setAttr(self.name,self.matchType(current,self.mode.apply(current,self.amount)))

    @staticmethod
    def applyForList(modifiers,object,hand=False):
        for modifier in modifiers:
            modifier.apply(object,hand)