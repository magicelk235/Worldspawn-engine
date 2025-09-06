import pygame
from data.managers import fileManager
from data.media.loaders import loader
def loadFont(path):
    return pygame.font.Font(path,16)
defaultFont = pygame.font.Font(None,16)
validExtensions = {".otf", ".ttf"}
global fonts
fonts = {}
for package in fileManager.getFolders("data/packages",True):
    loader.load(f"{package}/assets/fonts",validExtensions,fonts,loadFont)

def getFont(path):
    return fonts.get(path,defaultFont)
