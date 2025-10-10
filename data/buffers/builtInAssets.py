from data.buffers.assetsLoader import AssetsLoader
from pygame.font import Font
from pygame.mixer import Sound
from pygame.image import load,frombytes
from pygame import SRCALPHA,Surface
from PIL import Image

# font
def loadFont(path):
    return Font(path)
fonts = {"":Font()}
validExtensions = {".otf", ".ttf"}
AssetsLoader.newAsset("fonts",validExtensions,loadFont,buffers=fonts)

# sound
def loadSound(path):
    return Sound(path)
sounds = {"":Sound(buffer=b'')}
validExtensions = {".oog", ".wav"}
AssetsLoader.newAsset("sounds",validExtensions,loadSound,buffers=sounds)

# textures
def loadTexture(path):
    if ".png" in path:
        return [[load(path),1]]
    elif ".gif" in path:
        gif = Image.open(path)
        frames = []
        for frame in range(gif.n_frames):
            gif.seek(frame)
            if frame == 0:
                frames.append([load(path), gif.info.get("duration", 1000)*0.001])
            else:
                frames.append([frombytes(gif.tobytes(), gif.size, gif.mode), gif.info["duration"]*.001])
        gif.close()
        return frames
validExtensions = {".png", ".gif"}

def updateTexture(asset,texture):
    if not texture[0][0].get_flags() & SRCALPHA:
        for i in range(len(texture)):
            texture[i][0] = texture[i][0].convert_alpha()
defaultTexture = Surface((10,10))
defaultTexture.fill((0,0,0))
textures = {"":[[defaultTexture,1]]}
AssetsLoader.newAsset("textures",validExtensions,loadTexture,updateTexture,buffers=textures)