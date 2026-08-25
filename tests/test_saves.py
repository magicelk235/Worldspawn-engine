import os, sys, shutil
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

import data.core

core = data.core.Core()
player = core.getObject("main")
player.pos = (123,45,"word")
core.bannedPlayers = {"cheater"}
mark = core.getGroup1("object1")(core,(7,8,"word"))
core.addObjectByID(mark,"marked")

core.saveWorld("testworld")

# wreck the live world, then restore it
core.removeObjectByID("marked")
player.pos = (0,0,"word")
core.bannedPlayers = set()
assert core.getObject("marked") == None

assert core.loadWorld("testworld"), "saved world should load"
player = core.getObject("main")
assert player != None, "player should be restored"
assert (player.rect.x, player.rect.y) == (123,45), f"player position lost: {(player.rect.x,player.rect.y)}"
mark = core.getObject("marked")
assert mark != None and (mark.rect.x, mark.rect.y) == (7,8), "extra sprite lost"
assert core.bannedPlayers == {"cheater"}, "banned players lost"

# package state round trip (test package stores a counter)
assert getattr(core,"restoredCounter",None) == 41, f"package saveState/loadState broken: {getattr(core,'restoredCounter',None)}"

# missing world raises an error instead of crashing
assert not core.loadWorld("no-such-world")
core.clearEvents()
assert core.errorHappened("worldNotFound"), "missing world should raise worldNotFound"

shutil.rmtree("save/testworld")
print("saves OK", flush=True)
