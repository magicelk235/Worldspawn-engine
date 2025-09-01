from data.default import events
from pygame.time import set_timer
import time

class Timer:
	timerEvent = events.EventRegister.register("timer",None)
	startTime = time.monotonic()
	set_timer(timerEvent,20)

	def __init__(self,core):
		self.core = core
		self.countDowns = {}
	
	def addCountDown(self,name,start=None):
		if start == None:
			self.countDowns[name] = None
		else:
			self.countDowns[name] = start+self.currentTime()

	def isCountDown(self,name):
		return name in self.countDowns

	@ staticmethod
	def currentTime():
		return time.monotonic() - Timer.startTime

	def getCountDown(self,name):
		if self.countDowns[name] == None:
			return float("inf")
		return self.countDowns[name]-self.currentTime()

	def countDownEnded(self,name,start:int|None=None):
		if self.getCountDown(name) <= 0:
			self.countDowns.pop(name)
			if start != None:
				self.addCountDown(name,start)
			return True
		return False