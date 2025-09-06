from data.managers import fileManager
from data.media.loaders import loader
import pygame
def loadSound(path):
    return pygame.mixer.Sound(path)

validExtensions = {".oog", ".wav"}
global sounds
sounds = {}
for package in fileManager.getFolders("data/packages",True):
    loader.load(f"{package}/assets/sounds",validExtensions,sounds,loadSound)

def getSound(path):
    return sounds.get[path]