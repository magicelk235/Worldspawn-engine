from data.core import events
from pygame.time import set_timer


class Timer:
    def __init__(self,core,countDown:int,repeat=False):
        self.core = core
        self.countDown:int = countDown
        self.repeat = repeat
        self.stopped = False
        self.stoppedCycle = 0

    def currentCycle(self) -> int:
        return self.core.cycles

    def getStartTime(self) -> int:
        return self.endCycle - self.countDown

    def copy(self) -> "Timer":
        timer = Timer(self.core,self.countDown,self.repeat)
        timer.stoppedCycle = self.stoppedCycle
        timer.stopped = self.stopped
        timer.endCycle = self.endCycle
        return timer

    def copyAndStop(self):
        timer = self.copy()
        timer.stop()
        return timer

    @property
    def countDown(self):
        return self._countDown
    @countDown.setter
    def countDown(self,countDown):
        self._countDown = countDown
        self.endCycle = self.currentCycle() + countDown
        if self.countDown == -1:
            self.stop()
        else:
            self.start()

    @ property
    def remainingTime(self):
        if self.stopped:
            return float("inf")
        return self.endCycle - self.currentCycle()

    def restart(self):
        self.countDown = self.countDown
    def stop(self):
        self.stopped = True
        self.stoppedCycle = self.currentCycle()

    def start(self):
        if self.stopped:
            self.stopped = False
            self.countDown = self.endCycle - self.stoppedCycle
            self.stoppedCycle = 0

    def ended(self) -> bool:
        if self.remainingTime <= 0:
            if self.repeat:
                self.restart()
            return True
        return False

class TimeManager:# cycles = 20/1000 s
    timerEvent = events.EventRegister.register("timer",None)
    set_timer(timerEvent,20)

    def __init__(self,core):
        self.core = core
        self.timers:dict[str,Timer] = {}

    def extendCycler(self,name,amount):
        timer = self.getTimer(name)
        timer.endCycle += amount

    def replaceTimer(self,name,timer:Timer) -> None:
        self.timers[name] = timer

    def addTimer(self,name,start=-1,repeat=False):
        self.timers[name] = Timer(self.core,start,repeat)

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
        ended = timer.ended()
        if ended and not timer.repeat:
            self.removeTimer(name)
        return ended