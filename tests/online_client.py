import os, sys, time
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import pygame
import data.core

core = data.core.Core()

def cycle():
    pygame.event.pump()
    if core.mode == core.Mode.join and core.network != None:
        core.clientNetworkUpdate()
    core.clearEvents()
    core.endCycle()
    time.sleep(0.02)

def waitFor(check, why, seconds=6, poke=None):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if poke != None:
            poke()
        cycle()
        if check():
            return
    assert False, why

# wrong password: host must reject and we fall back to start mode
assert core.join("127.0.0.1", 5599, identity="badclient", password="nope")
waitFor(lambda: core.mode == core.Mode.start, "wrong password should be rejected")

# correct password: full session
assert core.join("127.0.0.1", 5599, identity="testclient", password="hunter2")

# identity handshake: the persistent identity becomes the client id
waitFor(lambda: core.userID == "testclient", "welcome should adopt the client identity")

# delta create: the host spawns our player and streams it over
waitFor(lambda: core.getObject("testclient") != None, "delta should create the client's player sprite")

# the visibility filter must keep 'secret' off this client
assert core.getObject("secret") == None, "filtered sprite leaked to the client"

# delta update: held key moves the player on the host, change streams back
startX = core.getObject("testclient").rect.x
localInput = core.getInputManager("testclient")
waitFor(lambda: core.getObject("testclient").rect.x > startX,
        "held key should move player",
        poke=lambda: setattr(localInput,"keys",{"d"}))
localInput.keys = set()

# discrete event transport: a KEYDOWN travels to the host's input manager
waitFor(lambda: core.getObject("testclient-mark") != None,
        "KEYDOWN 'e' should make the host spawn a marker",
        poke=lambda: localInput.addEvent(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,mod=0,unicode="e")))

# custom messages: ping to the host package, pong comes back
gotPong = []
def checkPong():
    for event in core.getEventList("networkMessage"):
        if isinstance(event.data,dict) and event.data.get("kind") == "pong":
            gotPong.append(True)
    return bool(gotPong)
waitFor(checkPong, "ping should be answered with pong",
        poke=lambda: core.send({"kind":"ping"}))

# delta remove: host despawns the marker, removal streams back
waitFor(lambda: core.getObject("testclient-mark") == None,
        "despawn should remove the marker on the client",
        poke=lambda: core.send({"kind":"despawn-mark"}))

# reconnect: same identity resumes the same player after a drop
core.network.close()
assert core.join("127.0.0.1", 5599, identity="testclient", password="hunter2")
startX = core.getObject("testclient").rect.x
localInput = core.getInputManager("testclient")
waitFor(lambda: core.getObject("testclient").rect.x > startX,
        "player should still respond after reconnecting with the same identity",
        poke=lambda: setattr(localInput,"keys",{"d"}))
localInput.keys = set()

# kick: host boots us, we land back in start mode
waitFor(lambda: core.mode == core.Mode.start,
        "kick should drop the client back to start mode",
        poke=lambda: core.send({"kind":"kick-me"}) if core.mode == core.Mode.join and core.network != None else None)

# ban: get banned, then a rejoin with the same identity is refused
assert core.join("127.0.0.1", 5599, identity="testclient", password="hunter2")
waitFor(lambda: core.userID == "testclient" and core.network != None and core.network.connected,
        "rejoin after kick should work")
waitFor(lambda: core.mode == core.Mode.start,
        "ban should drop the client",
        poke=lambda: core.send({"kind":"ban-me"}) if core.mode == core.Mode.join and core.network != None else None)
assert core.join("127.0.0.1", 5599, identity="testclient", password="hunter2")
waitFor(lambda: core.mode == core.Mode.start, "banned identity must be rejected on rejoin")

assert core.getObject("secret") == None, "filtered sprite leaked to the client"
print("online OK", flush=True)
