from data.default import runnable,events
from data.media import soundLoader
import pygame
class Sound(runnable.Runnable):
	soundEndedEvent = events.EventRegister.register("soundEnded",None)


	_channel_to_source = {}
	def __init__(self,core, soundPath, pos, loops=1, followID=None, maxHearDistance=300):
		super().__init__(core)
		self.loops = loops
		self.pos = pos
		self.maxHearDistance = maxHearDistance
		self.followID = followID

		self.sound = pygame.mixer.Sound(soundLoader.getSound(soundPath))
		self.channel = pygame.mixer.find_channel()
		
		self.channel.play(self.sound, loops=loops)
		self.channel.set_endevent(self.soundEndedEvent)
		Sound._channel_to_source[self.channel] = self

	def updatePos(self):
		if self.followID:
			if self.core.objectExist(self.followID):
				if self.core.getObjectByID(self.followID).eventHappend(events.EventRegister.getID("move")):
					self.pos = self.core.getObjectByID(self.followID).getAxis()
			else:
				self.followID = None

	def update(self, player):
		self.updatePos()
		delta = player.getAxis() - self.pos
		dist = delta.length()
		volume = max(0.0, min(1.0, 1 - dist/self.max_hear))
		pan = max(-1.0, min(1.0, delta.x/self.max_hear))
		left  = volume * (1 - pan) / 2
		right = volume * (1 + pan) / 2
		self.channel.set_volume(left, right)