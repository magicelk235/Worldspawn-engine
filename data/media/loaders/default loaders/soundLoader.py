from data.media.loaders.assetsLoader import AssetsLoader
from pygame.mixer import Sound
def loadSound(path):
    return Sound(path)

validExtensions = {".oog", ".wav"}
AssetsLoader.newAsset("sounds",validExtensions,loadSound)
