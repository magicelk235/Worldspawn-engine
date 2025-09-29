from data.core import events
from pygame.time import set_timer
import time



class Timer:
    startingTime = time.monotonic()
    def __init__(self,countDown,repeat=False):
        self.countDown = countDown
        self.repeat = repeat
        self.stopped = False
        self.stoppedTime = 0

    @ staticmethod
    def currentTime():
        return time.monotonic() - Timer.startingTime

    def getStartTime(self):
        return self.endTime - self.countDown

    @property
    def countDown(self):
        return self._countDown
    @countDown.setter
    def countDown(self,countDown):
        self._countDown = countDown
        self.endTime = Timer.currentTime() + countDown
        if self.countDown == -1:
            self.stop()
        else:
            self.start()

    @ property
    def remainingTime(self):
        if self.stopped:
            return float("inf")
        return self.endTime - Timer.currentTime()

    def restart(self):
        self.countDown = self.countDown
    def stop(self):
        self.stopped = True
        self.stoppedTime = Timer.currentTime()

    def start(self):
        if self.stopped:
            self.stopped = False
            self.countDown = self.endTime - self.stoppedTime
            self.stoppedTime = 0

    def ended(self) -> bool:
        if self.remainingTime() <= 0:
            if self.repeat:
                self.restart()
            return True
        return False

class TimeManager:
    timerEvent = events.EventRegister.register("timer",None)
        
    set_timer(timerEvent,20)

    def __init__(self,core):
        self.core = core
        self.timers = {}

    def extendTimer(self,name,amount):
        timer = self.getTimer(name)
        timer.endTime += amount

    def addTimer(self,name,start=-1,repeat=False):
        self.timers[name] = Timer(start,repeat)

    def isTimer(self,name):
        return name in self.timers

    def getTimer(self,name):
        return self.timers[name]

    def removeTimer(self,name):
        self.timers.pop(name)

    def getRemainingTime(self,name):
        return self.timers[name].remainingTime

    def timerEnded(self,name):
        timer = self.getTimer(name)
        if timer.ended():
            if not timer.repeat:
                self.removeTimer(name)