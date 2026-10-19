import pygame
from data.system import events
from pygame.time import set_timer
# the tick is scheduled while this module is read, and scheduling needs the
# event subsystem up; init is idempotent, so asking again costs nothing
pygame.init()


class Timer:
    def __init__(self,core,countDown:int,repeat=False):
        self.core = core
        self.repeat = repeat
        # both are read by the countDown setter through stop()/start(),
        # so they have to exist before the countdown is assigned
        self.stopped = False
        self.stoppedCycle = 0
        self.countDown:int = countDown

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
        # assigning a countdown arms the timer from now; -1 means "no timer",
        # which is held as a stopped one so it never reports as ended
        self._countDown = countDown
        self.endCycle = self.currentCycle() + countDown
        if countDown == -1:
            # frozen from this cycle: re-arming has to move the mark too, or
            # a resume later would compute its remaining time from whenever
            # the timer happened to be stopped before
            self.stopped = True
            self.stoppedCycle = self.currentCycle()
        else:
            self.stopped = False
            self.stoppedCycle = 0

    @ property
    def remainingTime(self):
        if self.stopped:
            return float("inf")
        return self.endCycle - self.currentCycle()

    def restart(self):
        self.countDown = self.countDown
    def stop(self):
        # stopping an already stopped timer must not move the mark it was
        # frozen at, or every extra stop hands back a different remaining
        # time when it is resumed
        if self.stopped:
            return
        self.stopped = True
        self.stoppedCycle = self.currentCycle()

    def start(self):
        # resume: the time that was left when it stopped is the time it has
        # left now, and the nominal countdown is untouched. A countdown of -1
        # never had any time to resume; starting it would read as a timer
        # that ran out a cycle ago and fire it.
        if self.stopped and self.countDown != -1:
            self.stopped = False
            self.endCycle = self.currentCycle() + (self.endCycle - self.stoppedCycle)
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
        self.timers.pop(name,None)

    def getRemainingTime(self,name):
        timer = self.timers.get(name)
        # no timer is not "no time left": nothing is counting
        return float("inf") if timer == None else timer.remainingTime

    def timerEnded(self,name):
        """True on the one cycle a timer runs out.

        A one shot timer is dropped the moment it reports, so asking again
        asks about a name that no longer has a timer. Arming a cooldown once
        and polling it every cycle is the normal way to use this, and the
        answer for the cycles after is no: it already ended, and it is not
        going to end again.
        """
        timer = self.timers.get(name)
        if timer == None:
            return False
        ended = timer.ended()
        if ended and not timer.repeat:
            self.removeTimer(name)
        return ended