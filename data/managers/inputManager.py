import pygame
from data.system.events import EventManager
# discrete events allowed on the wire, with the attributes that survive serialization
WIRE_EVENTS = {
    pygame.KEYDOWN: ("key","mod","unicode"),
    pygame.KEYUP: ("key","mod"),
    pygame.MOUSEBUTTONDOWN: ("button","pos"),
    pygame.MOUSEBUTTONUP: ("button","pos"),
    pygame.MOUSEWHEEL: ("x","y","flipped"),
}

def serializeEvents(events) -> list[dict]:
    payload = []
    for event in events:
        fields = WIRE_EVENTS.get(event.type)
        if fields == None:
            continue
        entry = {"type": event.type}
        for field in fields:
            value = getattr(event, field, None)
            entry[field] = list(value) if isinstance(value, tuple) else value
        payload.append(entry)
    return payload

def deserializeEvents(payload) -> list[pygame.event.Event]:
    events = []
    if not isinstance(payload,list):
        return events
    for entry in payload:
        if not isinstance(entry,dict):
            continue
        fields = WIRE_EVENTS.get(entry.get("type"))
        if fields == None:
            continue
        attrs = {}
        for field in fields:
            value = entry.get(field)
            if field == "pos":
                attrs[field] = tuple(value) if isinstance(value,list) and len(value) == 2 else (0,0)
            elif field == "unicode":
                attrs[field] = value if isinstance(value,str) else ""
            elif field == "flipped":
                attrs[field] = bool(value)
            else:
                attrs[field] = value if type(value) == int else 0
        events.append(pygame.event.Event(entry["type"],attrs))
    return events

class InputManager(EventManager):
    def __init__(self):
        super().__init__()
        self.keys:set = set()
        self.mousePos = (0,0)

    def convertKeys(self,keys):
        modifier_keys = {
            pygame.K_LSHIFT: "left shift",
            pygame.K_RSHIFT: "right shift",
            pygame.K_LCTRL: "left ctrl",
            pygame.K_RCTRL: "right ctrl",
            pygame.K_LALT: "left alt",
            pygame.K_RALT: "right alt",
        }
        keyNames = set()
        for index in range(len(keys)):
            if keys[index]:
                if index in modifier_keys:
                    keyNames.add(modifier_keys[index])
                else:
                    keyNames.add(pygame.key.name(index))
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_LSHIFT:
            if "left shift" not in keyNames:
                keyNames.add("left shift")
        if mods & pygame.KMOD_RSHIFT:
            if "right shift" not in keyNames:
                keyNames.add("right shift")
        if mods & pygame.KMOD_LCTRL:
            if "left ctrl" not in keyNames:
                keyNames.add("left ctrl")
        if mods & pygame.KMOD_RCTRL:
            if "right ctrl" not in keyNames:
                keyNames.add("right ctrl")
        if mods & pygame.KMOD_LALT:
            if "left alt" not in keyNames:
                keyNames.add("left alt")
        if mods & pygame.KMOD_RALT:
            if "right alt" not in keyNames:
                keyNames.add("right alt")
        self.keys = keyNames


    def isKeyHeld(self, key) -> bool:
        return key in self.keys
    
    def isKeyPressed(self,key:str) -> bool:
        for event in self.getEventList(pygame.KEYDOWN):
            if event.key == self.getKey(key):
                return True
        return False
    def isKeyReleased(self,key:str) -> bool:
        for event in self.getEventList(pygame.KEYUP):
            if event.key == self.getKey(key):
                return True
        return False

    @staticmethod
    def getKey(key):
        return getattr(pygame,f"K_{key.upper() if len(key)>1 else key}")

    def setRawInput(self,rawEvents,rawKeys,mousePos):
        self.convertEventList(rawEvents)
        self.convertKeys(rawKeys)
        self.mousePos = mousePos

    def setInput(self,events,keys,mousePos):
        self.convertEventList(events)
        self.keys = set(keys)
        self.mousePos = tuple(mousePos)

    def pendingEvents(self) -> list:
        pending = []
        for eventList in self.nextEvents.values():
            pending.extend(eventList)
        return pending
    
    def mouseClicked(self,right=False):
        for event in self.getEventList(pygame.MOUSEBUTTONDOWN):
            if event.button == 1 and not right:
                return True
            elif event.button == 2 and right:
                return True
        return False
    
    def mouseScroll(self,down=False):
        for event in self.getEventList(pygame.MOUSEBUTTONDOWN):
            if event.button == 3 and not down:
                return True
            elif event.button == 4 and down:
                return True
        return False
    
    def getMousePos(self):
        return self.mousePos

    def collideMouse(self,sprite):
        return sprite.rect.rect.collidepoint(self.getMousePos())

