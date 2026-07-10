import os, sys, time
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import pygame
import data.core

core = data.core.Core()
player = core.getObject("main")
assert player is not None, "test package must register a sprite with id 'main'"

def cycle():
    pygame.event.pump()
    core.getInput()
    core.update()
    core.emittersManager.update(player, True)
    core.clearEvents()
    core.endCycle()

for _ in range(10):
    time.sleep(0.02)
    cycle()

startX = player.x
player.addVector((1,0),time=0.2,speed=5)
for _ in range(20):
    time.sleep(0.02)
    cycle()
assert player.x > startX, f"vector should move sprite right (x stayed {player.x})"

print("boot OK")
