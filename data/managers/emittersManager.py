
from data.managers import idManager
from data.emitters import sound
import pygame

class DisplayManager(pygame.sprite.Group):
	# what shows through where no floor was drawn: the gap between chunks, the
	# edge of a cave, the void past the generated world. Black reads as a
	# broken frame, this reads as unlit ground.
	backgroundColor = (25,23,22)

	def __init__(self):
		super().__init__()
		self.size = (800,400)


	@ property
	def halfW(self):
		return self.size[0] // 2
	@ property
	def halfH(self):
		return self.size[1] // 2


	@ property
	def size(self):
		return self._size
	@size.setter
	def size(self, value:tuple[int,int]):
		self._size = value
		self.screen = pygame.display.set_mode(self.size, pygame.SCALED | pygame.RESIZABLE)
		self.displaySurface = pygame.display.get_surface()

	def getSize(self):
		return self.size

	def removeObject(self,object):
		self.remove(object)

	def update(self,player,updateAllGifs=False):
		self.screen.fill(self.backgroundColor)
		playerOffset = pygame.math.Vector2()
		playerCenter = player.rect.center
		playerOffset.x = playerCenter[0] - self.halfW
		playerOffset.y = playerCenter[1] - self.halfH
		defaultRenderOrder = []
		lateRenderOrder = []

		for sprite in sorted(self.sprites(), key=lambda sprite: (sprite.renderOrder,sprite.drawIndex)):
			if updateAllGifs:
				sprite.image.image._animate()
			if sprite.renderOrder < 4:
				sprite.display(self.displaySurface,player,playerOffset)
			elif sprite.renderOrder == 4:
				defaultRenderOrder.append(sprite)
			else:
				lateRenderOrder.append(sprite)
			
		
		# Depth goes by the middle of the hitbox. The original sorted on the
		# middle of the image instead - its sprite.rect WAS the image rect,
		# with the hitbox kept alongside as a second rect - so this is a
		# deliberate change, not a copy. A tall texture with a short hitbox at
		# its foot is the reason: sorting a tree by the middle of its trunk
		# and canopy puts it in front of anything standing at its base. The
		# cost is a few pixels of depth on the handful of objects whose
		# hitbox is not centred in their art.
		for sprite in sorted(defaultRenderOrder,key=lambda sprite: (sprite.rect.rect.centery,sprite.drawIndex)):
			sprite.display(self.displaySurface,player,playerOffset)
		for sprite in lateRenderOrder:
			sprite.display(self.displaySurface,player,playerOffset)
		pygame.display.update()

class AudioManager(idManager.IDManager):
	def __init__(self,core):
		self.core = core
		self.activeSources = {}
		super().__init__(self.activeSources)
		
	def addSound(self, soundPath, pos, loop, follow):
		# pygame counts repeats, so -1 is "keep going" and 0 is "play once"
		source = sound.Sound(self.core,pos,soundPath,loops=-1 if loop else 0,followID=follow)
		self.dropStolenChannel(source)
		return self.addObject(source)

	def dropStolenChannel(self,source):
		"""Retire whoever was on the channel the new sound just took.

		Every channel can be busy, and the mixer then hands the oldest one
		over instead of refusing. The sound that was playing on it is
		silenced by that alone, but it stays in activeSources, keeps being
		panned every cycle, and its end event now belongs to the new sound.
		"""
		for id,other in list(self.activeSources.items()):
			if other is not source and other.channel.id == source.channel.id:
				self.group.pop(id,None)
				self.usedIDs.discard(id)

	def removeObjectByID(self,id):
		source = self.activeSources.get(id)
		if source != None:
			# only give the channel up if it is still ours: a later sound may
			# have taken it over, and stopping it would cut that one short
			if sound.Sound._channel_to_source.get(source.channel.id) is source:
				sound.Sound._channel_to_source.pop(source.channel.id,None)
				source.channel.stop()
		super().removeObjectByID(id)

	def update(self, player):
		self.reapFinished()
		for source in list(self.activeSources.values()):
			source.update(player)

	def reapFinished(self):
		"""Drop the sources whose channel has stopped playing.

		The end event is not enough to go on. A clip with no samples behind
		it - which is what a mistyped path falls back to - is a no-op to the
		mixer and never posts one, so its source would sit here forever. And
		an event that does arrive names a channel, not a sound, so once a
		channel has changed hands the event belongs to a sound that is no
		longer the one listening for it. What the channel is doing right now
		answers both: a source that owns a silent channel is done, and one
		that is still audible is not, whoever posted what.
		"""
		for source in list(self.activeSources.values()):
			if not source.channel.get_busy():
				self.removeObject(source)

class EmittersManager:
	def __init__(self,core):
		self.displayManager = DisplayManager()
		self.audioManager = AudioManager(core)
		
	def addSound(self, soundPath, pos, loop=False, follow=None):
		return self.audioManager.addSound(soundPath,pos,loop,follow)
		
	def update(self,player,updateAllGifs=False,):
		self.displayManager.update(player,updateAllGifs=updateAllGifs)
		self.audioManager.update(player)
		
	def removeObject(self,object):
		self.displayManager.removeObject(object)

	@ property
	def screenSize(self):
		return self.displayManager.getSize()


	def getScreenSize(self):
		return self.displayManager.getSize()