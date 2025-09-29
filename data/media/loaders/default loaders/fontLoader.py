from pygame.font import Font
from data.media.loaders import Assetsloader
def loadFont(path):
    return Font(path)
mediaDict = {"":Font()}
validExtensions = {".otf", ".ttf"}
Assetsloader.Loader.newAsset("fonts",validExtensions,loadFont,mediaDict=mediaDict)