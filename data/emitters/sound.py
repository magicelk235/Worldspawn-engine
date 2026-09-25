from data.common import runnable
from data.spatial.spatial import Spatial
from data.system import events
from data.buffers.assetsLoader import AssetsLoader
import pygame

class Sound(Spatial):
	soundEndedEvent = events.EventRegister.register("soundEnded",None)


	# channel index -> the sound playing on it. The end event carries the
	# index, and two pygame Channel wrappers for the same channel are
	# neither equal nor hash equal, so the index is what can be looked up.
	_channel_to_source = {}
	def __init__(self,core, pos:tuple[int,int,str],soundPath:str, loops=0, followID=None, maxHearDistance=300):
		super().__init__(core,pos)
		self.loops = loops
		self.maxHearDistance = maxHearDistance
		self.followID = followID

		# the buffer already holds a mixer Sound, and the same one can play on
		# as many channels at once as the mixer has. Wrapping it again decoded
		# a private copy of the samples for every source that started.
		# Loudness and panning are set on the channel, so nothing here reaches
		# back into the shared clip.
		self.sound = AssetsLoader.get("sounds",soundPath)
		# force: take over the oldest channel instead of handing back None
		# once every channel is busy
		self.channel = pygame.mixer.find_channel(True)
		# armed, and on the books, before the clip starts. A short one can be
		# over before the next statement runs, and a channel that finishes
		# with no end event armed posts nothing at all: the source would then
		# never reach the reaping loop and would sit in the mixer's books
		# being panned for the rest of the session.
		self.channel.set_endevent(self.soundEndedEvent)
		Sound._channel_to_source[self.channel.id] = self
		self.channel.play(self.sound, loops=loops)

	def updatePos(self):
		if self.followID != None:
			followed = self.core.getObject(self.followID)
			if followed == None:
				self.followID = None
			elif followed.eventHappened(events.EventRegister.getID("move")):
				self.pos = followed.pos

	def update(self, player):
		self.updatePos()
		if player.dimension != self.dimension:
			self.channel.set_volume(0.0,0.0)
			return
		delta = pygame.math.Vector2(self.x-player.x, self.y-player.y)
		dist = delta.length()
		volume = max(0.0, min(1.0, 1 - dist/self.maxHearDistance))
		# positive pan means the source sits to the right of the listener
		pan = max(-1.0, min(1.0, delta.x/self.maxHearDistance))
		left  = volume * (1 - pan) / 2
		right = volume * (1 + pan) / 2
		self.channel.set_volume(left, right)
