from data.default import default,displayType
from data.media import imageLoader,fontLoader
from dataclasses import dataclass
import pygame,gif_pygame

@ dataclass(frozen=True)
class ImageData:
	path:str = None
	scaleSize:int|tuple = -1
	cutSize:int|tuple = -1
	flipX:bool = None
	flipY:bool = None
	color:tuple = None
	angle:float = None
	factoredSize:int = None
	resetGif:bool = False
	renderOrder:int = None
	text:str = None

	def getValue(self,sprite,value):
		if str(default.getAttr(self,value))[0] == "@":
			return default.getAttr(sprite,default.getAttr(self,value)[1:])
		else:
			return default.getAttr(self,value)
	# loaded
	def setData(self,name,image,sprite):
		if default.getAttr(self,name) != None:
			if self.getValue(sprite,name) != default.getAttr(image,name):
				default.setAttr(image,name,self.getValue(sprite,name))
		
	def load(self,image:"Image",sprite):
		keys = ["path","scaleSize","cutSize","flipX","flipY","color","angle","factoredSize","text"]
		for key in keys:
			self.setData(key,image,sprite)

class Image:
	def __init__(self,sprite,imageData):
		self.sprite = sprite
		self.path = imageLoader.defaultPath
		self.scaleSize = None
		self.cutSize = None
		self.flipX = False
		self.flipY = False
		self.color = (255,255,255,255)
		self.angle = 0
		self.renderOrder = 4
		self.factoredSize = 1
		self.text = None
		self.textMode = False
		self.image = gif_pygame.GIFPygame(imageLoader.getImage(""))
		self.imageData = imageData
		self.oldPath = None
		self._cache = {}
		self.loadImage()

	def getSize(self):
		return self.getRawImage().get_size()

	# data setter
	def setImageData(self,imageData):
		self.imageData = imageData
		self.loadImage()

	def toDict(self):
		return {"path":self.path,"scaleSize":self.scaleSize,"cutSize":self.cutSize,"flipX":self.flipX,"flipY":self.flipY,"color":self.color,"angle":self.angle,"factoredSize":self.factoredSize,"text":self.text,"textMode":self.textMode,"image.frame":self.image.frame}

	def toHash(self):
		return str(self.toDict())

	def loadImage(self):
		frame = 0
		frame_time = 0
		self.imageData.load(self,self.sprite)
		if self.text != None:
			self.textMode = True
		if self.image and not self.imageData.resetGif:
			frame = self.image.frame
			frame_time = self.image.frame_time

		self.createGif()

		if len(self.image.frames)<=frame:
			self.image.frame = len(self.image.frames)-1
		else:
			self.image.frame = frame

		self.image.frame_time = frame_time
		if self.cutSize == -1:
			self.cutSize = self.image.get_size()
		if self.scaleSize == -1:
			self.scaleSize = self.image.get_size()
		
		

	def updateImage(self):
		if self.sprite.eventHappened():
			self.loadImage()

	def getImageFrames(self):
		if self.textMode:
			font = fontLoader.getFont(self.path)
			image = font.render(str(self.text), font,(255,255,255))
			return [[image,1]]
		else:
			return imageLoader.getImage(self.path)
	
	def getImageFrame(self):
		return self.getImageFrames()[self.image.frame][0]

	def createGif(self):
		if self.textMode:
			self.image = gif_pygame.GIFPygame(self.getImageFrames())
		elif self.path != self.oldPath:
			self.getImageFrames()
			self.image = gif_pygame.GIFPygame(self.getImageFrames())

	# display
	def getAlignmentOffset(self,targetPoint,basePoint=displayType.DisplayType.topLeft):
		tempRect = self.getRawImage().get_rect(**{basePoint.value:(0,0)})
		base = pygame.math.Vector2(tempRect.topleft)
		target = pygame.math.Vector2(default.getAttr(tempRect,targetPoint.value))
		offset = target - base
		return offset

	def getRawImageByData(self):
		try:
			return self._cache[self.toHash()]
		except:
			image = self.getImageFrame()
			image = pygame.transform.scale(image,self.scaleSize)
			
			image = self.cutImage(image)
			image = pygame.transform.scale_by(image,self.factoredSize)
			image.fill(self.color,special_flags=pygame.BLEND_RGBA_MULT)
			image = pygame.transform.flip(image,self.flipX,self.flipY)
			image = pygame.transform.rotate(image,self.angle)
			self._cache[self.toHash()] = image
			return image

	def getRawImage(self):
		self.updateImage()
		return self.getRawImageByData(self._cache,self.toDict())

	@ staticmethod
	def displayFromData(displaySurf,pos,data,_cache):
		rawImage = Image.getRawImageByData(_cache,data)
		Image.displayImage(displaySurf,pos,rawImage)
		

	def display(self,displaySurf,pos):
		rawImage = self.getRawImage()

		self.displayImage(displaySurf,pos,rawImage)
	
	@ staticmethod
	def displayImage(displaySurf, pos,image):
		displaySurf.blit(image, pos)

	def cutImage(self,image):
		if image.get_size() == self.cutSize:
			return image
		try:
			image.subsurface(pygame.Rect(0, 0, *self.cutSize))
			return image
		except:
			newImage = pygame.surface.Surface(self.cutSize,pygame.SRCALPHA)	
			tile_w, tile_h = image.get_size()
			target_w, target_h = self.cutSize
			for y in range(0, target_h, tile_h):
				for x in range(0, target_w, tile_w):
					newImage.blit(image, (x, y))
			return newImage