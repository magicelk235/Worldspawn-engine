from data.common.attributeAccessor import AttributeAccessor
from data.spatial.rect import DisplayType
from data.buffers.assetsLoader import AssetsLoader
from dataclasses import dataclass
import pygame
from gif_pygame import GIFPygame
@ dataclass(frozen=True)
class ImageData(AttributeAccessor):
	path:str = None
	scaleSize:int|tuple = -1
	cutSize:int|tuple = -1
	flipX:bool = False
	flipY:bool = False
	color:tuple = (255,255,255,255)
	angle:float = 0
	factoredSize:int = 1
	renderOrder:int = 4
	text:str = None
	resetGif:bool = True

	def toDict(self) -> dict[str,any]:
		return dict(self.__dict__)

	def load(self,image:"Image"):
		for key in list(self.__dict__.keys()):
			image.setAttr(key, self.__dict__[key])

class Image(AttributeAccessor):
	_cache = {}
	def __init__(self,imageData:ImageData):
		self.oldPath:str = None
		self.textMode:bool = False
		self.image:GIFPygame = None
		self.setImageData(imageData)

	@ property
	def size(self):
		return self.getRawImage().get_size()

	def setImageData(self,imageData:ImageData):
		self.imageData = imageData
		self.loadImage()

	def toDict(self):
		return self.imageData.toDict()|{"image.frame":self.image.frame}

	def toHash(self):
		return str(self.toDict())

	def loadImage(self):
		self.imageData.load(self)
		self.textMode = self.text != None
		if self.textMode or self.image == None or self.path != self.oldPath:
			self.image = GIFPygame(self.frames)
			self.oldPath = self.path
		if self.cutSize == -1:
			self.cutSize = self.image.get_size()
		if self.scaleSize == -1:
			self.scaleSize = self.image.get_size()

	@ property
	def frames(self):
		if self.textMode:
			font = AssetsLoader.get("fonts",self.path)
			image = font.render(str(self.text),True,(255,255,255))
			return [[image,1]]
		return AssetsLoader.get("textures",self.path)

	@ property
	def currentFrame(self):
		return self.image.get_current_surface()

	def getAlignmentOffset(self,targetPoint,basePoint=DisplayType.topLeft):
		tempRect = self.getRawImage().get_rect(**{basePoint.value:(0,0)})
		base = pygame.math.Vector2(tempRect.topleft)
		target = pygame.math.Vector2(AttributeAccessor.getAttr(tempRect,targetPoint.value))
		offset = target - base
		return offset

	def getRawImage(self):
		key = self.toHash()
		if key not in self._cache:
			frame = self.currentFrame
			frame = pygame.transform.scale(frame,self.scaleSize)
			frame = self.cutImage(frame)
			frame = pygame.transform.scale_by(frame,self.factoredSize)
			frame.fill(self.color,special_flags=pygame.BLEND_RGBA_MULT)
			frame = pygame.transform.flip(frame,self.flipX,self.flipY)
			frame = pygame.transform.rotate(frame,self.angle)
			self._cache[key] = frame
		return self._cache[key]

	def display(self,displaySurf,pos):
		displaySurf.blit(self.getRawImage(), pos)

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
