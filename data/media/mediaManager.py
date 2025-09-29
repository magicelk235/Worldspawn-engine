
from data.managers import idManager
from data.media import sound
import pygame

class DisplayManager(pygame.sprite.Group):
	def __init__(self):
		super().__init__()
		self.size = (800,400)
		self.screen = pygame.display.set_mode(self.size, pygame.SCALED | pygame.RESIZABLE)
		self.displaySurface = pygame.display.get_surface()

		self.halfW = self.screen.get_width() // 2
		self.halfH = self.screen.get_height() // 2

	def getSize(self):
		return self.size

	def removeObject(self,object):
		self.remove(object)

	def update(self,player,updateAllGifs=False):
		self.screen.fill((0,0,0))
		playerOffset = pygame.math.Vector2()
		playerCenter = player.center
		playerOffset.x = playerCenter[0] - self.halfW
		playerOffset.y = playerCenter[1] - self.halfH
		defaultRenderOrder = []
		lateRenderOrder = []

		for sprite in sorted(self.sprites(), key=lambda sprite: sprite.renderOrder):
			if updateAllGifs:
				sprite.image.image._animate()
			if sprite.rect.renderOrder < 4:
				sprite.display(self.displaySurface,player,playerOffset)
			elif sprite.rect.renderOrder == 4:
				
				defaultRenderOrder.append(sprite)
			else:
				lateRenderOrder.append(sprite)
			
		
		for sprite in sorted(defaultRenderOrder,key=lambda sprite: sprite.y):
			sprite.display(self.displaySurface,player,playerOffset)
		for sprite in lateRenderOrder:
			sprite.display(self.displaySurface,player,playerOffset)
		pygame.display.update()

class AvManager(idManager.IDManager):
	def __init__(self,core):
		self.core = core
		self.activeSources = {}
		super().__init__(self.activeSources)
		
	def addSound(self, soundPath, pos, loop, follow):
		source = sound.Sound(self.core,soundPath=soundPath, pos=pos, loop=loop, follow=follow)
		self.addObject(self.activeSources,source)

	def removeObjectByID(self,id):
		channel = self.activeSources[id].channel
		sound.Sound._channel_to_source.pop(channel)
		super().removeObjectByID(id)

	def update(self, player):
		for source in list(self.activeSources.values()):
			source.update(player)
		for event in self.core.getEventList(sound.Sound.soundEndedEvent):
			source = sound.Sound._channel_to_source.get(pygame.mixer.Channel(event.channel))
			self.removeObject(source)

class mediaManager:
	def __init__(self,core):
		self.displayManager = DisplayManager()
		self.audioManager = AudioManager(core)
		
	def addSound(self, soundPath, pos, loop=False, follow=None):
		self.audioManager.addSound(soundPath,pos,loop,follow)
		
	def update(self,player,updateAllGifs=False,):
		self.displayManager.update(player,updateAllGifs=updateAllGifs)
		self.audioManager.update(player)
		
	def removeObject(self,object):
		self.displayManager.removeObject(object)

	def getScreenSize(self):
		return self.displayManager.getSize()