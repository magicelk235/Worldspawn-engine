import os, sys, time
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import pygame
import data.core

core = data.core.Core()
# the client renders the host's world; local sprites get replaced by snapshots
assert core.join("127.0.0.1", 5599)

def cycle():
    pygame.event.pump()
    core.clientNetworkUpdate()
    core.clearEvents()
    core.endCycle()

# wait for welcome + first snapshot
deadline = time.time() + 5
while time.time() < deadline and core.userID == "main":
    cycle(); time.sleep(0.02)
assert core.userID.startswith("client"), "welcome should assign a client id"

deadline = time.time() + 5
while time.time() < deadline and core.getObject(core.userID) == None:
    cycle(); time.sleep(0.02)
player = core.getObject(core.userID)
assert player != None, "snapshot should create the client's player sprite"

startX = player.rect.x
localInput = core.getInputManager(core.userID)
deadline = time.time() + 5
while time.time() < deadline:
    localInput.keys = {"d"}          # simulate holding right
    cycle(); time.sleep(0.02)
    player = core.getObject(core.userID)
    if player != None and player.rect.x > startX:
        break
assert player.rect.x > startX, f"held key should move player (x stayed {player.rect.x})"
print("online OK", flush=True)
