import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

from PIL import Image as PILImage
gifDir = "packages/package/assets/textures"
os.makedirs(gifDir, exist_ok=True)
frames = [PILImage.new("RGB",(8,8),c) for c in [(255,0,0),(0,255,0),(0,0,255)]]
frames[0].save(f"{gifDir}/testanim.gif", save_all=True, append_images=frames[1:], duration=50, loop=0)

import pygame
import data.core
from data.emitters.image import ImageData
from data.sprites.sprite import Animation

core = data.core.Core()
player = core.getObject("main")
player.objectData.animations["anim"] = Animation(ImageData(path="testanim"))

player.setAnimation("anim")
assert player.currentAnimation == "anim", "setAnimation should switch"

firstFrame = player.image.image.frame
firstSurface = player.image.getRawImage()
advanced = False
for _ in range(20):
    time.sleep(0.06)
    core.emittersManager.update(player, True)
    if player.image.image.frame != firstFrame:
        advanced = True
        break
assert advanced, "gif frame should advance over time"
assert player.image.getRawImage() is not firstSurface, "raw image cache should key per frame"

player.setAnimation("default")
assert player.currentAnimation == "default"
print("animation OK")
