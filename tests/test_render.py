import os, sys
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,root); os.chdir(root)

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
print("render OK", flush=True)
