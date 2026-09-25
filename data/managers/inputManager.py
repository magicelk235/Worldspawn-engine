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

# convertKeys reports these under a readable name, so getKey has to be able to
# turn that same name back into a key code
NAMED_KEYS = {
    "left shift": pygame.K_LSHIFT,
    "right shift": pygame.K_RSHIFT,
    "left ctrl": pygame.K_LCTRL,
    "right ctrl": pygame.K_RCTRL,
    "left alt": pygame.K_LALT,
    "right alt": pygame.K_RALT,
}

# pygame.key.get_pressed() hands back a scancode indexed array whose subscript
# translates a key code into that scancode, so held keys have to be probed by
# code. Walking the array positionally reads scancodes, and naming those as if
# they were key codes turns "d" into "" and "e" into "backspace".
KEY_CODES = sorted({value for name,value in vars(pygame).items()
                    if name.startswith("K_") and type(value) == int})
KEY_NAMES = {code:pygame.key.name(code) for code in KEY_CODES}

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
        keyNames = set()
        for code in KEY_CODES:
            try:
                held = keys[code]
            except (IndexError,KeyError,TypeError):
                continue
            if held:
                name = KEY_NAMES[code]
                # codes SDL knows but this build cannot name are skipped
                # rather than reported as an empty key
                if name != "":
                    keyNames.add(name)
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
        if key in NAMED_KEYS:
            return NAMED_KEYS[key]
        # pygame names every key it can report as held, so the same name maps
        # straight back to a code: "space", "up" and "[1]" included
        return pygame.key.key_code(key)

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
        # pygame numbers the buttons left 1, middle 2, right 3
        button = 3 if right else 1
        for event in self.getEventList(pygame.MOUSEBUTTONDOWN):
            if event.button == button:
                return True
        return False
    
    def mouseScroll(self,down=False):
        # the wheel is its own event; it stopped arriving as buttons 4 and 5
        # in pygame 2, and buttons 3 and 4 were never the wheel at all
        for event in self.getEventList(pygame.MOUSEWHEEL):
            if (event.y < 0) == down and event.y != 0:
                return True
        return False
    
    def getMousePos(self):
        return self.mousePos

    def collideMouse(self,sprite):
        return sprite.rect.rect.collidepoint(self.getMousePos())

