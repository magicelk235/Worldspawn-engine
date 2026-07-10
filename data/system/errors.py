import sys, traceback
import pygame
from data.system import events

def errorEventTemplate(name:str, message:str="", fatal:bool=False):
    return pygame.event.Event(events.EventRegister.getID("error"), {"name":name,"message":message,"fatal":fatal})

errorEvent = events.EventRegister.register("error", errorEventTemplate)

class ErrorManager:
    def raiseError(self, name:str, message:str="", fatal:bool=False) -> None:
        print(f"[worldspawn error] {name}: {message}", file=sys.stderr)
        traceback.print_stack(file=sys.stderr)
        self.addEvent(errorEventTemplate(name, message, fatal))
        if fatal:
            self.running = False

    def errorHappened(self, name:str) -> bool:
        return any(event.name == name for event in self.getEventList(errorEvent))

    def getErrors(self, name:str=None) -> list:
        errorList = self.getEventList(errorEvent)
        if name == None:
            return errorList
        return [event for event in errorList if event.name == name]
