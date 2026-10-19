import time
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

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

# --- package loading -------------------------------------------------------

import os
import pathlib
import tempfile
from data.managers import fileManager

# Windows hands its folders over with backslashes, and a package folder has
# to pass the name check however its path is spelled
assert fileManager.validPath(pathlib.PureWindowsPath("packages", "worldspawn"))
assert not fileManager.validPath(pathlib.PureWindowsPath("packages", "__pycache__"))

# __init__.py turns a prefab folder into a Python package; it is not a prefab
# and has no getObject for the loader to call
prefabFolder = tempfile.mkdtemp(dir=ROOT)
for name in ("__init__.py", "thing.py", ".DS_Store"):
    open(os.path.join(prefabFolder, name), "w").close()
prefabFiles = fileManager.getFiles(prefabFolder, True, extensions={".py"})
assert prefabFiles == ["thing"], prefabFiles

# --- inventory and item modifiers ------------------------------------------

from data.inventory.modifiers import Modifier, Mode
from data.sprites.aliveObject import AliveObject, AliveObjectData
from data.sprites.sprite import Animation
from data.spatial.hitbox import Hitbox

class StubItem:
    """What the inventory expects of an item; a package's items domain has these."""
    def __init__(self, name, max, modifiers=()):
        self.name, self.max, self.modifiers = name, max, modifiers
    def getName(self):
        return self.name
    def getMax(self):
        return self.max
    def applyModifiers(self, object, hand=False):
        Modifier.applyForList(self.modifiers, object, hand)

stubItems = {
    "none": lambda: StubItem("none", 0),
    "rock": lambda: StubItem("rock", 64),
    "wings": lambda: StubItem("wings", 1, (Modifier("speed", 3, Mode.Add, handNeeded=False),)),
    "chain": lambda: StubItem("chain", 1, (Modifier("maxHealth", 14, Mode.MaxSet, handNeeded=False),)),
}
core.createFunction("getItems", lambda self, name: stubItems.get(name))

def aliveStub(**stats):
    return AliveObject(core, (0, 0, "word"),
                       AliveObjectData(Hitbox(1, 1), {"default": Animation()}, **stats))

def stacks(inventory):
    return [(slot.getItemName(), slot.getCount()) for slot in inventory.toList()
            if slot.getItemName() != "none"]

# a modifier that works from any slot counts once, held or not
flier = aliveStub(speed=1)
flier.inventory.addItemByCount(stubItems["wings"](), 1)
assert flier.inventory.hasItemInHand("wings")
assert flier.speed == 4, f"held wings were counted twice: speed {flier.speed}"
flier.inventory.interact(1, 0, 0, 0)
assert not flier.inventory.hasItemInHand("wings") and flier.speed == 4, flier.speed

# a stack never goes past its item's max, and a stack that cannot all fit is
# turned away whole
carrier = aliveStub()
assert carrier.inventory.addItemByCount(stubItems["rock"](), 100)
assert stacks(carrier.inventory) == [("rock", 64), ("rock", 36)], stacks(carrier.inventory)
pocket = aliveStub(inventorySize=1)
pocket.inventory.addItemByCount(stubItems["rock"](), 60)
assert not pocket.inventory.addItemByCount(stubItems["rock"](), 10)
assert stacks(pocket.inventory) == [("rock", 60)], stacks(pocket.inventory)

# the stats are rebuilt from the base every cycle. Health an item's higher
# maximum allows has to survive that, and go once the item does.
tough = aliveStub(health=10)
tough.inventory.addItemByCount(stubItems["chain"](), 1)
tough.health = 14
tough.inventory.update()
assert (tough.maxHealth, tough.health) == (14, 14), (tough.maxHealth, tough.health)
tough.inventory.removeItem("chain")
assert (tough.maxHealth, tough.health) == (10, 10), (tough.maxHealth, tough.health)

# something that carries nothing has no slot for a hand
emptyHanded = aliveStub(inventorySize=0)
assert not emptyHanded.inventory.hasItemInHand("rock")

# --- vectors are timed in whole cycles --------------------------------------

from data.managers.timeManager import TimeManager

# one timer event per cycle, handed in rather than waited for, so the count
# does not depend on how busy the machine is
def step(cycles, update):
    for _ in range(cycles):
        core.addEvent(pygame.event.Event(TimeManager.timerEvent))
        core.clearEvents()
        update()

mover = core.getGroup1("object1")(core,(0,0,"word"))
core.addObjectByID(mover,"mover")

# 0.02 has no exact binary form, so counting a 0.2 second push down by it left
# a sliver above zero and the push ran an eleventh cycle
mover.addVector((1,0),0.2,5)
step(30, mover.updateVectors)
assert mover.x == 50, f"a 0.2s push at 5 a cycle covers 50, not {mover.x}"

# a push the other way for as long as the one there cancels it, instead of
# leaving a few billionths of a second that still move a whole cycle: 0.1 and
# 0.2 seconds make 0.30000000000000004 of them
mover.addVector((1,0),0.1,5)
mover.addVector((1,0),0.2,5)
mover.addVector((-1,0),0.3,5)
assert mover.vectors == {}, f"equal opposite pushes have to cancel out: {mover.vectors}"

# more time in a direction that is already moving goes into the push that is
# there. The new copy used to be merged against the opposite push as well,
# which deleted the push it had just extended.
mover.addVector((1,0),0.2,5)
mover.addVector((-1,0),0.2,3)
mover.addVector((1,0),0.2,3)
assert (1,0) in mover.vectors and (-1,0) in mover.vectors, \
    f"extending a push must not delete it: {mover.vectors}"
mover.vectors.clear()

# --- alive objects ------------------------------------------------------------

# riders are carried: they used to stay where they got on while the mount
# walked off, unless the package moved them itself every cycle
horse = core.getGroup1("mob")(core,(0,0,"word"))
core.addObjectByID(horse,"horse")
rider = core.getGroup1("mob")(core,(60,60,"word"))
core.addObjectByID(rider,"rider")
assert horse.addRider("rider")
horse.addVector((1,0),0.1,4)
step(5, horse.update)
assert horse.x == 20 and rider.pos == horse.pos, \
    f"rider left behind: horse {horse.pos}, rider {rider.pos}"

# a shield is the share of a hit that is absorbed, so at most all of it:
# stacked past 1.0 it turned every hit into healing
tank = aliveStub(health=10)
tank.health = 5
tank.shield = 1.5
tank.applyDamage(4)
assert tank.health == 5, f"a hit through a full shield changed health to {tank.health}"

# the size the inventory was built at reads back
assert tank.inventorySize == tank.objectData.inventorySize

# a target that has left the world is no target any more, whatever still
# holds on to it
prey = core.getGroup1("mob")(core,(90,90,"word"))
core.addObjectByID(prey,"prey")
tank.target = prey
assert tank.hasTarget()
core.removeObjectByID("prey")
assert not tank.hasTarget(), "a sprite that left the world still counts as a target"

# --- packages and the core they are grafted onto -----------------------------

import json
import shutil
import subprocess

def bootElsewhere(script, files=None):
    """Boot a core in a process of its own and return the last line script prints.

    Packages import under fixed module names and are grafted onto the one Core
    class, so a different set of them cannot share this process. files are
    written under packages/ next to a copy of the sample package; leaving them
    out leaves packages/ out entirely, the way a fresh clone has it.
    """
    root = tempfile.mkdtemp(dir=ROOT)
    os.symlink(os.path.join(harness.REPO, "data"), os.path.join(root, "data"))
    if files != None:
        shutil.copytree(os.path.join(harness.FIXTURES, "package"),
                        os.path.join(root, "packages", "package"))
        for path, text in files.items():
            path = os.path.join(root, "packages", path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
    child = subprocess.run([sys.executable, "-c", script], cwd=root,
                           capture_output=True, text=True, timeout=60)
    assert child.returncode == 0, f"core did not boot:\n{child.stdout}\n{child.stderr}"
    return json.loads(child.stdout.strip().splitlines()[-1])

# `python main.py` in a fresh clone, where nothing has made a packages/ folder
# yet, stopped on a FileNotFoundError before the first frame
fresh = bootElsewhere(
    "import json, threading, data.core\n"
    "core = data.core.Core()\n"
    "threading.Timer(0.5, lambda: setattr(core, 'running', False)).start()\n"
    "core.main()\n"
    "print(json.dumps({'packages': len(core.packages)}))\n")
assert fresh == {"packages": 0}, fresh

# A package written from the README alone - a name and nothing else in its
# settings, a domains.yaml with no domains in it, no serverUpdate or
# clientUpdate - next to the sample package grown a second dynamic domain and
# prefab folders named after core methods, a package declaring the sprites
# domain over again, and two folders the loader has to turn away out loud.
SPRITE_BASE = "import data.sprites.sprite\ndef getObject():\n    return data.sprites.sprite.Sprite\n"
DOMAIN = ("  create-static-getter: true\n  create-dynamic-getter: true\n"
          "  add-function: |\n    super(Core,self).addObjectByID(object,id)\n"
          "  remove-function: |\n    super(Core,self).removeObjectByID(id)\n")

def prefabSource(name):
    return (f"import data.sprites.sprite\nclass {name}(data.sprites.sprite.Sprite):\n    pass\n"
            f"def getObject():\n    return {name}\n")

with open(os.path.join(harness.FIXTURES, "package", "domains.yaml")) as f:
    sampleDomains = f.read().rstrip("\n")

loaded = bootElsewhere(
    "import json, data.core\n"
    "core = data.core.Core()\n"
    "stone = core.getFloor('stone')(core, (0, 0, 'word'))\n"
    "core.addObjectByID(stone, 'stone')\n"
    "core.serverUpdate()\n"
    "core.clientUpdate()\n"
    "core.clearEvents()\n"
    "print(json.dumps({\n"
    "    'packages': sorted(core.packages),\n"
    "    'extra': getattr(core, 'extraLoaded', False),\n"
    "    'pebble': core.getRock('pebble').__name__,\n"
    "    'tileInWorld': 'stone' in core.sprites and 'stone' in core.tiles,\n"
    "    'mainInGroups': 'main' in core.sprites and 'main' in core.group1,\n"
    "    'hostCallable': callable(core.host),\n"
    "    'getObject': core.getObject('main') is core.sprites.get('main'),\n"
    "    'errors': sorted([e.name, e.message.split(':')[0]] for e in core.getErrors()),\n"
    "}))\n",
    {
        "extra/settings.yaml": "name: extra\n",
        "extra/domains.yaml": "# this package adds no domains\n",
        "extra/core.py": "class Extra:\n    def __init__(self):\n        self.extraLoaded = True\n\n"
                         "def getObject():\n    return Extra\n",
        "package/settings.yaml": "name: package\ndependencies: []\nused-domains:\n"
                                 "  - sprites\n  - tiles\nalways-enabled: true\n",
        "package/domains.yaml": sampleDomains + "\ntiles:\n" + DOMAIN,
        "package/tiles/base.py": SPRITE_BASE,
        "package/tiles/floor/base.py": SPRITE_BASE,
        "package/tiles/floor/stone.py": prefabSource("stone"),
        "package/sprites/host/base.py": SPRITE_BASE,
        "package/sprites/host/beacon.py": prefabSource("beacon"),
        "package/sprites/object/base.py": SPRITE_BASE,
        "package/sprites/object/crate.py": prefabSource("crate"),
        "game/settings.yaml": "name: game\ndependencies:\n  - package\nused-domains:\n  - sprites\n",
        "game/domains.yaml": "sprites:\n" + DOMAIN,
        "game/sprites/base.py": SPRITE_BASE,
        "game/core.py": "class Game:\n    pass\n\ndef getObject():\n    return Game\n",
        "my_extra/settings.yaml": "name: my_extra\n",
        "mismatch/settings.yaml": "name: other\n",
        "orphan/settings.yaml": "name: orphan\ndependencies:\n  - nowhere\n",
        "bare/settings.yaml": "name: bare\ndependencies:\n  - package\nused-domains:\n  - sprites\n  - nosuch\n",
        "bare/sprites/rock/base.py": SPRITE_BASE,
        "bare/sprites/rock/pebble.py": prefabSource("pebble"),
        "notes/readme.txt": "not a package\n",
    })
assert loaded["packages"] == ["bare", "extra", "game", "package"], loaded["packages"]
assert loaded["extra"], "a package with only a name in its settings has to load"
assert loaded["pebble"] == "pebble", "a package with no core.py or domains.yaml has to load its prefabs"
# core.sprites is the world: the loop updates it, saves write it, clients are
# synced from it. A second dynamic domain used to fall out of all three.
assert loaded["tileInWorld"], "a tile is missing from core.sprites"
# declaring a domain again used to swap its group for an empty one, and the
# sample package's player went with it
assert loaded["mainInGroups"], "a package declaring sprites again emptied the groups"
assert loaded["hostCallable"] and loaded["getObject"], "a prefab folder replaced a core method"
assert loaded["errors"] == [["domainNotFound", "packages/bare"],
                            ["getterNameTaken", "packages/package/sprites/object"],
                            ["groupNameTaken", "packages/package/sprites/host"],
                            ["packageNotLoaded", "packages/mismatch"],
                            ["packageNotLoaded", "packages/my_extra"],
                            ["packageNotLoaded", "packages/orphan"]], loaded["errors"]

# --- ids in the world ------------------------------------------------------------

# Adding under an id that is taken replaces the sprite there. The one it
# replaced used to stay in the draw group, drawn for good with no id left to
# remove it by.
drawn = core.emittersManager.displayManager
first = core.getGroup1("object1")(core,(0,0,"word"))
core.addObjectByID(first,"twice")
second = core.getGroup1("object1")(core,(0,0,"word"))
core.addObjectByID(second,"twice")
assert core.getObject("twice") is second
assert first not in drawn, "the sprite an id used to name is still drawn"
core.removeObjectByID("twice")
assert second not in drawn

# The update walks a copy of the world. A sprite removed earlier in the same
# walk, its id already handed to a replacement, used to be updated anyway, and
# when it asked to be removed the replacement went instead.
Base = core.getGroup1("object1")

class Doomed(Base):
    updates = 0
    def update(self):
        super().update()
        Doomed.updates += 1
        return True

class Executioner(Base):
    def update(self):
        super().update()
        if isinstance(core.getObject("doomed"), Doomed):
            core.removeObjectByID("doomed")
            core.addObjectByID(Base(core,(1,1,"word")),"doomed")
        return False

# the domain and prefab of a sprite are read off its module
Doomed.__module__ = Executioner.__module__ = Base.__module__
core.addObjectByID(Executioner(core,(0,0,"word")),"executioner")
core.addObjectByID(Doomed(core,(0,0,"word")),"doomed")
core.update()
assert Doomed.updates == 0, "a sprite removed earlier in the cycle was still updated"
assert core.getObject("doomed") != None, "the replacement under the same id was removed"
core.removeObjectByID("executioner")
core.removeObjectByID("doomed")

print("boot OK")
