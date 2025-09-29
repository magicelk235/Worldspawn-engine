from data.media import image
from data.spatial.rect import DisplayType
from dataclasses import dataclass
from typing import Callable
@ dataclass
class Animation:

	imageData:image.ImageData = image.ImageData()
	displayType:DisplayType = DisplayType.topLeft
	countDown:float = -1.0
	weight:int = 1
	moveable:bool = True
	nextAnimation:str = "default"
	startFunc:Callable = lambda x: None
	endFunc:Callable = lambda x: None
	timer:float = 0
	

	def load(self,sprite):
		sprite.addCountDown("animation",self.countDown,True)
		oldAnimation = sprite.getAnimation(self.previousAnimation)
		previousAnimation = sprite.getCurrentAnimation()
		if not previousAnimation.imageData.resetGif and self == oldAnimation:
			sprite.countDowns["animation"] = self.timer
		
		sprite.moveable = self.moveable
		sprite.displayType = self.displayType
		sprite.image.setImageData(self.imageData)
		self.startFunc(sprite)

	def unload(self,sprite,newAnimation):
		if not newAnimation.imageData.resetGif:
			self.timer = sprite.getCountDown("animation")
		self.endFunc(sprite)

	def getImageData(self):
		return self.imageData
	
	def weightCheck(self,other):
		return self.weight >= other.weight
