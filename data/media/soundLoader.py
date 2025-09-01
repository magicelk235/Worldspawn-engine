from data.default import fileManager
from data.media import loader
import pygame,os
def loadSound(path):
    return pygame.mixer.Sound(path)

validExtensions = {".oog", ".wav"}
global sounds
sounds = {}
for package in fileManager.getFolders("data/packages",True):
    loader.load(f"{package}/assets/sounds",validExtensions,sounds,loadSound)

def getSound(path):
    return sounds.get[path]