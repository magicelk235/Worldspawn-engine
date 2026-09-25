import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

import data.core
from data.sprites import sprite as spriteModule

core = data.core.Core()
player = core.getObject("main")            # sits at (0,0,"word"), screen is 800x400

near = core.getGroup1("object1")(core,(10,10,"word"))
core.addObjectByID(near,"near")
far = core.getGroup1("object1")(core,(99999,99999,"word"))
core.addObjectByID(far,"far")
other = core.getGroup1("object1")(core,(10,10,"elsewhere"))
core.addObjectByID(other,"other")
hidden = core.getGroup1("object1")(core,(12,12,"word"))
core.addObjectByID(hidden,"hidden")
hidden.hide()

drawn = []
original = spriteModule.Sprite.displayImage
spriteModule.Sprite.displayImage = lambda self,surf,player,offset: drawn.append(self.id)
try:
    core.emittersManager.update(player,True)
finally:
    spriteModule.Sprite.displayImage = original

assert "main" in drawn and "near" in drawn, f"visible sprites not drawn: {drawn}"
assert "far" not in drawn, "offscreen sprite should be culled"
assert "other" not in drawn, "other-dimension sprite should be culled"
assert "hidden" not in drawn, "hidden sprite should not be drawn"

# Depth in the y sorted band goes by the middle of the hitbox. The original
# sorted on the middle of the image, so this is a deliberate change: a tree is
# a tall texture with a short hitbox at its foot, and sorting it by the middle
# of trunk and canopy together draws it over anything standing at its base.
from data.spatial.hitbox import Hitbox

def place(id,pos,hitbox):
    object = core.getGroup1("object1")(core,pos)
    object.objectData.hitbox = hitbox
    object.rect = hitbox.getRect(pos)
    core.addObjectByID(object,id)
    return object

tree = place("tree",(0,0,"word"),Hitbox(16,8,0,40))     # trunk 40px down the texture
walker = place("walker",(4,30,"word"),Hitbox(12,20,0,0))

def walkerFirst():
    drawn.clear()
    spriteModule.Sprite.displayImage = lambda self,surf,player,offset: drawn.append(self.id)
    try:
        core.emittersManager.update(player,True)
    finally:
        spriteModule.Sprite.displayImage = original
    return drawn.index("walker") < drawn.index("tree")

assert tree.y < walker.y, "the sprite positions have to disagree with the hitboxes"
assert walkerFirst(), "a character behind a trunk must be drawn before the tree"
walker.axis = (4,50)
assert tree.rect.rect.centery < walker.rect.rect.centery
assert not walkerFirst(), "a character in front of a trunk must be drawn over the tree"

# Inside one render band the order used to be whatever order the sprites were
# built in. A client builds its sprites as deltas arrive, in no particular
# order, so a panel could be drawn over the buttons sitting on it. Every
# sprite carries a number from the core instead, and the number is streamed,
# so a client draws a band in the host's order.
ui = [place(f"ui{i}",(0,0,"word"),Hitbox(4,4)) for i in range(4)]
for object in ui:
    object.image.setAttr("renderOrder",6)
assert [o.drawIndex for o in ui] == sorted(o.drawIndex for o in ui), \
    "sprites should be numbered in the order they are made"

def bandOrder():
    drawn.clear()
    spriteModule.Sprite.displayImage = lambda self,surf,player,offset: drawn.append(self.id)
    try:
        core.emittersManager.update(player,True)
    finally:
        spriteModule.Sprite.displayImage = original
    return [id for id in drawn if id.startswith("ui")]

assert bandOrder() == ["ui0","ui1","ui2","ui3"], bandOrder()
# a host telling this client that ui3 was made first has to move it first,
# which is the whole point of streaming the number
core.patchObject(ui[3],{"drawIndex":0})
assert bandOrder() == ["ui3","ui0","ui1","ui2"], bandOrder()
assert "drawIndex" in ui[0].objectData.clientData, "the order has to reach clients"

# The cache of rendered looks is keyed by the image data itself, so it has to
# stay hashable. Colours and sizes are tuples in the engine and lists once
# they have been through JSON, which is every save file and every delta.
from data.emitters.image import ImageData

fromWire = ImageData(color=[10,20,30,255],scaleSize=[16,16])
assert fromWire.color == (10,20,30,255) and fromWire.scaleSize == (16,16)
assert hash(fromWire) == hash(ImageData(color=(10,20,30,255),scaleSize=(16,16))), \
    "a colour off the wire must key the same look as one written in code"

print("render OK", flush=True)
