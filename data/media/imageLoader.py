import pygame
from data.default import fileManager
from data.media import loader
from PIL import Image
def loadImage(path):
    if ".png" in path:
        return [[pygame.image.load(path),1]]
    elif ".gif" in path:
        gif = Image.open(path)
        frames = []
        for frame in range(gif.n_frames):
            gif.seek(frame)
            if frame == 0:
                frames.append([pygame.image.load(path), gif.info.get("duration", 1000)*0.001])
            else:
                frames.append([pygame.image.frombytes(gif.tobytes(), gif.size, gif.mode), gif.info["duration"]*.001])
        gif.close()
        return frames
defaultPath = "ui/failed"
validExtensions = {".png", ".gif"}
global images
images = {}
for package in fileManager.getFolders("data/packages",True):
    loader.load(f"{package}/assets/images",validExtensions,images,loadImage)

def updateImage(path):
    image = images.get(path,images[defaultPath])
    if not image[0][0].get_flags() & pygame.SRCALPHA:
        for i in range(len(image)):
            image[i][0] = image[i][0].convert_alpha()

def getImage(path):
    updateImage(path)
    return images.get(path,images[defaultPath])
