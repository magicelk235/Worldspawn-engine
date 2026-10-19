"""Headless checks on the draw path: bands, screen space UI, void colour, fonts.

    python tests/test_display.py

test_render.py covers what gets culled and how the y sorted band is ordered.
This one covers the rest of what the original's CameraGroup did: the view is
the window with no zoom step, the render bands layer in a fixed order around
that sorted band, UI is drawn in screen space with no camera offset, the void
behind the world is the original's dark brown, and a font can be asked for at
a size.
"""

import sys
from dataclasses import replace

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import harness

ROOT = harness.buildRoot()

import pygame

import data.core
from data.buffers.assetsLoader import AssetsLoader
from data.buffers.builtInAssets import FontFamily
from data.emitters.image import Image, ImageData
from data.managers.emittersManager import DisplayManager
from data.spatial.hitbox import Hitbox
from data.sprites import sprite as spriteModule
from data.sprites import uiObject

core = data.core.Core()
player = core.getObject("main")             # at (0,0,"word")
display = core.emittersManager.displayManager


def place(id, pos, renderOrder, hitbox=None):
    object = core.getGroup1("object1")(core, pos)
    if hitbox != None:
        object.objectData.hitbox = hitbox
        object.rect = hitbox.getRect(pos)
    animation = object.getCurrentAnimation()
    animation.imageData = replace(animation.imageData, renderOrder=renderOrder)
    object.image.setImageData(animation.imageData)
    core.addObjectByID(object, id)
    return object


def record():
    """Draw a frame, returning the ids drawn in order and where each landed."""
    order = []
    spots = {}
    originalSprite = spriteModule.Sprite.displayImage
    originalUi = uiObject.UIObject.displayImage

    def spy(self, surf, viewer, offset):
        order.append(self.id)
        spots[self.id] = (surf, offset)
    spriteModule.Sprite.displayImage = spy
    uiObject.UIObject.displayImage = spy
    try:
        core.emittersManager.update(player, True)
    finally:
        spriteModule.Sprite.displayImage = originalSprite
        uiObject.UIObject.displayImage = originalUi
    return order, spots


# --- the view is the window, with no zoom or rescale in between -------------

assert display.getSize() == (800, 400), display.getSize()
assert display.displaySurface.get_size() == (800, 400), display.displaySurface.get_size()
order, spots = record()
assert spots["main"][0] is display.displaySurface, \
    "sprites must be drawn straight onto the display surface, not a scaled copy"

# the camera puts the middle of the player in the middle of the window, so the
# visible area is exactly the window: 800x400, same as the original's internal
# surface at zoom 1
offset = spots["main"][1]
assert tuple(offset) == (player.rect.center[0] - 400, player.rect.center[1] - 200), offset

# --- render bands ----------------------------------------------------------

# everything under 4 draws in band order, 4 is the y sorted band, everything
# above draws in band order after it. A floor is a band 1 sprite well below a
# band 4 one: the band has to win over the y sort, or the ground covers what
# stands on it.
floor = place("floor", (0, 120, "word"), 1)
detail = place("detail", (0, 110, "word"), 2)
walker = place("walker", (0, -40, "word"), 4, Hitbox(12, 20))
window = place("window", (0, 100, "word"), 5)
overlay = place("overlay", (0, 100, "word"), 8)

order, spots = record()
positions = {id: index for index, id in enumerate(order)}
assert positions["floor"] < positions["detail"] < positions["walker"], \
    f"ground bands draw before the sorted band: {order}"
assert positions["walker"] < positions["window"] < positions["overlay"], \
    f"UI and overlay bands draw after the sorted band: {order}"
assert floor.rect.rect.centery > walker.rect.rect.centery, \
    "the floor has to be below the walker for this to prove anything"

# A tall texture with a foot level hitbox, both sides of a character. The depth
# key is the hitbox centre, which is a deliberate change from the original's
# image centre - see the note in emittersManager.
tree = place("tree", (0, 0, "word"), 4, Hitbox(16, 8, 0, 40))
walker.axis = (0, 30)                       # hitbox centre 40, above the trunk's 44
order, spots = record()
positions = {id: index for index, id in enumerate(order)}
assert tree.y < walker.y, "positions must disagree with the hitboxes"
assert tree.rect.rect.centery > walker.rect.rect.centery
assert positions["walker"] < positions["tree"], \
    "a character standing behind a trunk is drawn before the tree"
walker.axis = (0, 50)
order, spots = record()
positions = {id: index for index, id in enumerate(order)}
assert tree.rect.rect.centery < walker.rect.rect.centery
assert positions["tree"] < positions["walker"], \
    "and a character in front of the trunk is drawn over it"

# --- UI is screen space ----------------------------------------------------

# a bare UIObject has no package domain to be registered under, and the draw
# path only needs it in the display group, which the core would otherwise do
# when the sprite is added to the world
def widget(pos, viewers, id):
    object = uiObject.UIObject(core, pos, None, viewers, viewers)
    object.id = id
    display.add(object)
    return object


owned = widget((700, 300, "word"), {"main"}, "widget")
order, spots = record()
assert "widget" in order, "a widget its viewer owns has to be drawn"

# a widget outside the camera's box still draws: it is not in world space, so
# the view test that culls world sprites would only ever cull it by mistake
far = widget((99999, 99999, "word"), {"main"}, "farWidget")
order, __ = record()
assert "farWidget" in order, "screen space UI must not be culled against the world"

unowned = widget((10, 10, "word"), set(), "hiddenWidget")
order, __ = record()
assert "hiddenWidget" not in order, "a widget nobody owns is not drawn"

# the camera offset never reaches a widget's blit position: UIObject draws at
# its own coordinates, so a widget stays put while the world scrolls under it
blits = []
originalDisplay = Image.display
Image.display = lambda self, surf, pos: blits.append((self, tuple(pos)))
try:
    core.emittersManager.update(player, True)
    before = dict((id(image), pos) for image, pos in blits)[id(owned.image)]
    player.axis = (player.x + 120, player.y + 60)
    blits.clear()
    core.emittersManager.update(player, True)
    after = dict((id(image), pos) for image, pos in blits)[id(owned.image)]
finally:
    Image.display = originalDisplay
assert before == after, f"a widget must not move with the camera: {before} -> {after}"
assert before == owned.calculatePosByDisplayType(), \
    "a widget lands where its own alignment puts it, in window coordinates"

# and the alignment itself: the image's anchor point goes on the hitbox's, so
# a tall texture pinned by its foot grows upwards out of a short hitbox
from data.spatial.rect import DisplayType

foot = place("foot", (0, 0, "word"), 4, Hitbox(16, 8))
foot.objectData.displayByDirectionX = False
foot.displayType = DisplayType.bottomLeft
height = foot.image.size[1]
assert foot.calculatePosByDisplayType() == (0, 8 - height), \
    foot.calculatePosByDisplayType()

# --- the void behind the world --------------------------------------------

assert DisplayManager.backgroundColor == (25, 23, 22), DisplayManager.backgroundColor
core.emittersManager.update(player, True)
assert display.displaySurface.get_at((799, 399))[:3] == DisplayManager.backgroundColor, \
    "unpainted screen keeps the original's dark ground, not black"

# --- fonts come in sizes ---------------------------------------------------

builtIn = AssetsLoader.get("fonts", None)
assert isinstance(builtIn, FontFamily), type(builtIn)
assert builtIn.get(24) is builtIn.get(24), "one Font per size, kept"
assert builtIn.get(24) is not builtIn.get(12), "and a different one per size"
small = builtIn.size("4242", 12)
large = builtIn.size("4242", 40)
assert large[0] > small[0] and large[1] > small[1], (small, large)
assert builtIn.size("4242") == builtIn.size("4242", None), "no size means the font's own"
assert builtIn.antialias, "the built-in font has no pixel grid to protect"
assert not FontFamily("whatever.ttf").antialias, "a supplied font is pixel art"

# an unantialiased render comes back 8 bit with a colourkey; it has to reach
# the draw path as real transparency or every label gets a black box
plain = builtIn.render("42", 24, antialias=False)
assert plain.get_flags() & pygame.SRCALPHA, "text must carry per pixel alpha"
assert plain.get_at((0, 0))[3] == 0, "the background of a glyph run is transparent"

sizedSmall = Image.measure(ImageData(text="4242", fontSize=12))
sizedLarge = Image.measure(ImageData(text="4242", fontSize=40))
assert sizedLarge[0] > sizedSmall[0], (sizedSmall, sizedLarge)
assert Image.measure(ImageData(text="4242", fontSize=-1)) == \
    builtIn.render("4242").get_size(), "-1 leaves the font at its own size"

# Font.size() reports the font's metrics, which are not the size of the
# surface the glyphs land on. Anything sizing a box around a line has to
# measure the render, or the box misses the text by a couple of pixels.
assert builtIn.render("4242", 12).get_size() != builtIn.size("4242", 12), \
    "if these ever agree the warning above can go"

# A field can follow one of its owner's attributes with "@name". The fields a
# picture is drawn with always did, but a text or a path that followed one
# kept the frames it was first loaded with, and cached them under the new key.
from data.common.attributeAccessor import AttributeAccessor


class Scoreboard(AttributeAccessor):
    score = "1"


board = Scoreboard()
score = Image(ImageData(text="@score"), board)
assert score.size == builtIn.render("1").get_size()
board.score = "12345"
assert score.size == builtIn.render("12345").get_size(), \
    "a text that follows an attribute has to show what the attribute says now"

# --- a widget's players can leave -------------------------------------------

# a client that disconnects loses its input manager at once, while the
# widgets it could click only hear about it on a later cycle; asking one of
# them for its players' input used to raise for the one who left
core.addInputManager("guest")
shared = widget((10, 10, "word"), {"main", "guest"}, "sharedWidget")
core.inputMangers.pop("guest")
assert shared.getInputList() == [core.getInputManager("main")], shared.getInputList()

print("display OK", flush=True)
