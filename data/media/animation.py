from data.media import image
from data.default.displayType import DisplayType
from dataclasses import dataclass
from typing import Callable
@ dataclass
class Animation:

	imageData:image.ImageData = image.ImageData()
	displayType:DisplayType = DisplayType.topLeft
	countDown:float|None = None
	renderOrder:int = None
	weight:int = 1
	moveable:bool = True
	nextAnimation:str = "default"
	startFunc:Callable = lambda x: None
	endFunc:Callable = lambda x: None
	timer:float = 0
	

	def load(self,sprite):
		sprite.addCountDown("animation",self.countDown)
		oldAnimation = sprite.getAnimation(previousAnimation)
		previousAnimation = sprite.getCurrentAnimation()
		if not previousAnimation.imageData.resetGif and self == oldAnimation:
			sprite.countDowns["animation"] = self.timer
		
		sprite.moveable = self.moveable
		sprite.setDisplayType(self.displayType)
		sprite.setRenderOrder(self.renderOrder)
		sprite.image.setImageData(self.imageData)
		self.startFunc(sprite)

	def unload(self,sprite,newAnimation):
		if not newAnimation.imageData.resetGif:
			try:
				self.timer = sprite.getCountDown("animation")
			except:
				self.timer = 0
		self.endFunc(sprite)

	def getImageData(self):
		return self.imageData
	
	def weightCheck(self,other):
		return self.weight >= other.weight
