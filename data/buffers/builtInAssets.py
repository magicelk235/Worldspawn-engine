from data.buffers.assetsLoader import AssetsLoader
from pygame.font import Font
from pygame.mixer import Sound
from pygame.image import load,frombytes
from pygame import SRCALPHA,Surface
from PIL import Image
from os.path import splitext

# font
class FontFamily:
    """One font file, at whatever sizes get asked for.

    pygame.font.Font bakes the point size in at construction, so a package
    that wants two text sizes out of one file needs two Font objects. The
    family owns them and hands them out by size; sizes come from widget code,
    so the set stays tiny and lives as long as the font buffer does.

    path None is pygame's built-in font, which is also the fallback asset.
    """

    def __init__(self,path=None):
        self.path = path
        self.sizes = {}

    @ property
    def antialias(self):
        # pixel fonts turn to mush when smoothed, so only the built-in font,
        # which has no pixel grid to protect, gets antialiasing
        return self.path == None

    def get(self,size=None):
        if size != None:
            size = int(size)
            if size <= 0:
                size = None
        font = self.sizes.get(size)
        if font == None:
            font = Font(self.path) if size == None else Font(self.path,size)
            self.sizes[size] = font
        return font

    def size(self,text,size=None):
        return self.get(size).size(str(text))

    def render(self,text,size=None,color=(255,255,255),antialias=None):
        antialias = self.antialias if antialias == None else antialias
        surface = self.get(size).render(str(text),antialias,color)
        # an unantialiased render comes back 8 bit with a black colourkey,
        # which nothing downstream can scale or blend. convert_alpha turns
        # the key into real transparency.
        return surface.convert_alpha()

def loadFont(path):
    return FontFamily(path)
fonts = {"":FontFamily()}
validExtensions = {".otf", ".ttf"}
AssetsLoader.newAsset("fonts",validExtensions,loadFont,buffers=fonts)

# sound
def loadSound(path):
    return Sound(path)
# What a sound key that does not exist plays. Silence, but real silence: a
# chunk with no samples in it is not something SDL_mixer will play, and
# handing one to a channel crashes the process outright often enough to lose
# a session to a single mistyped path. A few milliseconds of zeroed frames is
# a valid chunk, so it starts, finishes, and reports like any other clip.
sounds = {"":Sound(buffer=bytes(1024))}
validExtensions = {".ogg", ".wav"}
AssetsLoader.newAsset("sounds",validExtensions,loadSound,buffers=sounds)

# textures
def loadTexture(path):
    # the extension decides, not a substring of the whole path: a folder with
    # a dot in its name would otherwise pick the loader, and a file saved as
    # .PNG would match neither branch and land in the buffer as None
    extension = splitext(path)[1].lower()
    if extension == ".png":
        return [[load(path),1]]
    gif = Image.open(path)
    frames = []
    for frame in range(gif.n_frames):
        gif.seek(frame)
        seconds = gif.info.get("duration",1000)*0.001
        if frame == 0:
            frames.append([load(path), seconds])
        else:
            frames.append([frombytes(gif.tobytes(), gif.size, gif.mode), seconds])
    gif.close()
    return frames
validExtensions = {".png", ".gif"}

def updateTexture(asset,texture):
    if not texture[0][0].get_flags() & SRCALPHA:
        for i in range(len(texture)):
            texture[i][0] = texture[i][0].convert_alpha()
# What a texture key that does not exist draws. A plain dark square reads as
# ordinary art at small sizes, so a mistyped path can sit in a package for
# weeks; a checker cannot be mistaken for anything a person drew.
defaultTexture = Surface((16,16))
defaultTexture.fill((0,0,0))
for _y in range(0,16,8):
    for _x in range(0,16,8):
        if (_x // 8 + _y // 8) % 2 == 0:
            defaultTexture.fill((255,0,255),(_x,_y,8,8))
textures = {"":[[defaultTexture,1]]}
AssetsLoader.newAsset("textures",validExtensions,loadTexture,updateTexture,buffers=textures)