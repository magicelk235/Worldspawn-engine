import shutil
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

# a prefab that can no longer be rebuilt from (core, pos) alone, the way one
# looks once its constructor has grown a required argument
import os
with open(os.path.join(ROOT,"packages","package","sprites","group1","coin.py"),"w") as f:
    f.write("import data.sprites.sprite\n"
            "class coin(data.sprites.sprite.Sprite):\n"
            "    def __init__(self, core, pos, value):\n"
            "        self.value = value\n"
            "        super().__init__(core, pos)\n"
            "def getObject():\n"
            "    return coin\n")

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

# --- what a sprite is, not only where it is ---------------------------------

# A hidden sprite used to come back drawn: a load rebuilds it through
# __init__, which starts everything shown, and visibility was never saved.
# A host streams the same fields, so a client is covered by the same entry.
secret = core.getGroup1("object1")(core,(30,30,"word"))
core.addObjectByID(secret,"secret")
secret.hide()
streamed = core.spawnFromEntry("secret-copy","group1.object1",secret.toData())
assert streamed != None and not streamed.isVisible(), "a client draws a sprite the host hides"

# Prefabs written the way a package would, an alive object and a widget with
# no constructor of their own, have to come back from cls(core, pos): that is
# all a save or a host's delta gives them. An alive object's inventory clears
# its slots with core.getItems("none"), so the check brings its own items.
from data.inventory.modifiers import Modifier, Mode

class Item:
    def __init__(self, name, max=32, modifiers=()):
        self.name, self.max, self.modifiers = name, max, tuple(modifiers)
    def getName(self):
        return self.name
    def getMax(self):
        return self.max
    def applyModifiers(self, object, hand=False):
        Modifier.applyForList(self.modifiers, object, hand)

items = {"none": lambda: Item("none", 0),
         # carried, it lifts the ceiling health is clamped against
         "chain": lambda: Item("chain", 1, (Modifier("maxHealth", 14, Mode.MaxSet, handNeeded=False),))}
core.createFunction("getItems", lambda self, name: items.get(name))

mob = core.getGroup1("mob")(core,(50,50,"word"))
core.addObjectByID(mob,"mob")
mob.inventory.addItemByCount(items["chain"](),1)
mob.health = 13
panel = core.getGroup1("panel")(core,(5,5,"word"))
core.addObjectByID(panel,"panel")

core.saveWorld("objects")
assert core.loadWorld("objects"), "saved world should load"
restored = core.getObject("mob")
assert restored != None, "an alive object with no constructor of its own did not come back"
assert restored.inventory.hasItem("chain"), "its inventory did not come back"
# health is clamped against the ceiling the items make, so it has to go in
# after them: taken in field order, 13 of 14 came back as 10
assert restored.health == 13, f"health clamped against the bare maximum: {restored.health}"
assert core.getObject("panel") != None, "a widget with no constructor of its own did not come back"
assert not core.getObject("secret").isVisible(), "a hidden sprite came back drawn"
shutil.rmtree("save/objects")

# A spawner keeps count of what it made to stay under its limit. The count is
# not saved, so after a load it has to know its own spawns again by the tag
# and spawner index they carry, and both have to survive the save for that -
# the tag is also what a pet knows its owner by.
import pygame
from data.managers.timeManager import TimeManager
from data.sprites.npcObject import Spawner

def nest(npc):
    # two at a time, and never more than two of them alive
    npc.objectData.spawners.append(Spawner(0, ["group1.mob"], 2, 5, 1, 2, False, {}))

def run(npc, cycles):
    for _ in range(cycles):
        core.addEvent(pygame.event.Event(TimeManager.timerEvent))
        core.clearEvents()
        core.endCycle()
        npc.update()

queen = core.getGroup1("mob")(core,(200,200,"word"))
core.addObjectByID(queen,"queen")
others = {id for id,object in core.sprites.items() if object.prefabPath == "group1.mob"}

def brood():
    return [object for id,object in core.sprites.items()
            if object.prefabPath == "group1.mob" and id not in others]

nest(queen)
run(queen,5)
assert len(brood()) == 2, len(brood())
core.saveWorld("brood")
assert core.loadWorld("brood"), "saved world should load"
assert all(object.tag == "queen" for object in brood()), "spawns forgot who made them"
queen = core.getObject("queen")
nest(queen)
run(queen,5)
assert len(brood()) == 2, f"a spawner went past its limit after a load: {len(brood())}"
shutil.rmtree("save/brood")

# Two spawners on one NPC that make the same prefab keep separate counts, both
# while they run and after a load, when each has to pick its own spawns out of
# the restored world again.
def pair(npc):
    npc.objectData.spawners.append(Spawner(0, ["group1.mob"], 2, 5, 1, 2, False, {}))
    npc.objectData.spawners.append(Spawner(1, ["group1.mob"], 2, 5, 3, 2, False, {}))

def counts(npc):
    return [len(getattr(npc,spawner.setName)) for spawner in npc.objectData.spawners]

def twins():
    return [object for object in core.sprites.values() if getattr(object,"tag",None) == "twin"]

twin = core.getGroup1("mob")(core,(400,400,"word"))
core.addObjectByID(twin,"twin")
pair(twin)
run(twin,12)
assert len(twins()) == 4, f"one spawner counted the other's spawns: {len(twins())}"
assert counts(twin) == [2,2], counts(twin)
core.saveWorld("twins")
assert core.loadWorld("twins"), "saved world should load"
twin = core.getObject("twin")
pair(twin)
for spawner in twin.objectData.spawners:
    # what a spawner's first update does: start the count, seeded from the world
    spawner.npcObjectInit(twin)
assert counts(twin) == [2,2], f"spawners lost track of their own spawns after a load: {counts(twin)}"
run(twin,12)
assert len(twins()) == 4, f"spawners went past their limit after a load: {len(twins())}"
shutil.rmtree("save/twins")

# --- saves that go wrong ------------------------------------------------------

import json
import pygame

# A value the file cannot hold - a set in saveData, an object from saveState -
# used to stop the write half way: the sprite table was left unreadable or the
# settings empty, and the world saved there before was lost with it.
def keptFiles():
    return {name: open(f"save/kept/{name}").read() for name in ("settings.yaml","sprites.json")}

core.saveWorld("kept")
before = keptFiles()
tagged = core.getGroup1("object1")(core,(1,2,"word"))
tagged.objectData.saveData = tagged.objectData.saveData + ["tags"]
tagged.tags = {"a"}
core.addObjectByID(tagged,"tagged")
assert core.saveWorld("kept") == False, "a world that cannot be written has to say so"
core.removeObjectByID("tagged")
packageCore = core.packages["package"].core
saveState = packageCore.saveState
packageCore.saveState = lambda self: {"area": pygame.Rect(0,0,1,1)}
assert core.saveWorld("kept") == False, "a world that cannot be written has to say so"
packageCore.saveState = saveState
core.clearEvents()
assert len(core.getErrors("worldNotSaved")) == 2, "a failed save has to raise worldNotSaved"
assert keptFiles() == before, "a failed save damaged the save that was already there"
assert core.saveWorld("kept") == True
shutil.rmtree("save/kept")

# A sprite whose class can no longer be built from (core, pos) used to stop
# the load half way, after the world had been cleared: what came after it in
# the file, the bans and the package state never came back.
coin = core.getGroup1("coin")(core,(3,3,"word"),5)
core.addObjectByID(coin,"coin")
keep = core.getGroup1("object1")(core,(9,9,"word"))
core.addObjectByID(keep,"keep")
core.bannedPlayers = {"cheater"}
core.saveWorld("coins")
core.bannedPlayers = set()
core.restoredCounter = None
assert core.loadWorld("coins"), "one sprite that cannot be rebuilt stopped the load"
core.clearEvents()
assert core.getObject("coin") == None and core.errorHappened("spriteNotRestored")
assert core.getObject("keep") != None and core.getObject("main") != None, "the rest of the world did not come back"
assert core.bannedPlayers == {"cheater"}, "bans were not restored"
assert core.restoredCounter == 41, "package state was not restored"
notRestored = [event.message for event in core.getErrors("spriteNotRestored")]
assert any("coin (group1.coin)" in message and ", line " in message for message in notRestored), \
    f"the error does not say where the constructor failed: {notRestored}"

# A world saved by a long session carries draw numbers well past what this one
# has handed out. Whatever is made after loading it has to draw after all of
# it, not take a number that came out of the file.
with open("save/coins/sprites.json") as f:
    entries = json.load(f)
entries["keep"]["data"]["drawIndex"] = 10**6
with open("save/coins/sprites.json","w") as f:
    json.dump(entries,f)
assert core.loadWorld("coins")
later = core.getGroup1("object1")(core,(0,0,"word"))
assert later.drawIndex > 10**6, f"a new sprite drew among the loaded ones: {later.drawIndex}"

# An entry whose prefab no longer resolves is named in an error, as one whose
# class cannot be built is, instead of only being counted.
entries["ghost"] = {"prefabPath":"group1.gone","data":entries["keep"]["data"]}
entries["stray"] = {"prefabPath":"nowhere.thing","data":entries["keep"]["data"]}
with open("save/coins/sprites.json","w") as f:
    json.dump(entries,f)
assert core.loadWorld("coins")
core.clearEvents()
notRestored = [event.message for event in core.getErrors("spriteNotRestored")]
for named in ("ghost (group1.gone)","stray (nowhere.thing)"):
    assert any(named in message for message in notRestored), f"{named} was skipped silently: {notRestored}"
shutil.rmtree("save/coins")

print("saves OK", flush=True)
