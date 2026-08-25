import os, sys, time
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import pygame
import data.core

core = data.core.Core()
assert core.join("127.0.0.1", 5599, identity="testclient")

def cycle():
    pygame.event.pump()
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
assert core.join("127.0.0.1", 5599, identity="testclient")
startX = core.getObject("testclient").rect.x
localInput = core.getInputManager("testclient")
waitFor(lambda: core.getObject("testclient").rect.x > startX,
        "player should still respond after reconnecting with the same identity",
        poke=lambda: setattr(localInput,"keys",{"d"}))

assert core.getObject("secret") == None, "filtered sprite leaked to the client"
print("online OK", flush=True)
