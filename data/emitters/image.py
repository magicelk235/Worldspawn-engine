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
	# point size for text mode; -1 leaves the font at its own default
	fontSize:int = -1
	resetGif:bool = True

	def __post_init__(self):
		# This is the key the image cache is stored under, so it has to stay
		# hashable. Sizes and colours are tuples everywhere in the engine, but
		# JSON has no tuple: anything that has been through a save file or a
		# host's delta arrives as a list and would make the whole record
		# unhashable, taking the sprite down with it.
		for field in ("scaleSize","cutSize","color"):
			value = getattr(self,field)
			if isinstance(value,list):
				object.__setattr__(self,field,tuple(value))

	def toDict(self) -> dict[str,any]:
		return dict(self.__dict__)

	def load(self,image:"Image"):
		for key in list(self.__dict__.keys()):
			image.setAttr(key, self.__dict__[key])

class Image(AttributeAccessor):
	# every distinct look ever rendered used to stay here forever. A label
	# that shows a number makes a new one every time the number changes, so
	# the clock, the coordinates and every stack count leaked a surface per
	# update. Kept as a least recently used cache instead: world textures are
	# asked for on every frame and stay, one-off text falls out.
	_cache = {}
	_cacheLimit = 2048
	_keyFields = ("path","text","fontSize","scaleSize","cutSize","flipX","flipY",
				  "color","angle","factoredSize")
	def __init__(self,imageData:ImageData,owner=None):
		self.oldPath:str = None
		self.textMode:bool = False
		self.image:GIFPygame = None
		# whoever the image belongs to, so image data can point at one of its
		# attributes with "@name" and follow it: "@directionX.value" mirrors
		# the frame as the sprite turns around
		self.owner = owner
		self.setImageData(imageData)

	@ property
	def size(self):
		return self.getRawImage().get_size()

	@ staticmethod
	def measure(imageData:"ImageData") -> tuple[int,int]:
		"""Size the art in this data will cover, before any sprite owns it.

		A widget has to build its hitbox before the sprite exists, and the
		hitbox is what gets clicked, so it has to agree with the pixels. Fields
		that follow an owner attribute ("@name") have nobody to follow from
		here and measure at the value the field declares.
		"""
		return Image(imageData).size

	def setImageData(self,imageData:ImageData):
		self.imageData = imageData
		self.loadImage()

	def resolveDynamicFields(self):
		for key,value in self.imageData.__dict__.items():
			if type(value) != str or not value.startswith("@"):
				continue
			# with no owner there is nothing to follow, and the name would
			# reach the transforms as a piece of text. Measuring happens
			# before a sprite owns its data, so this is a normal state rather
			# than a broken one: fall back on what the field declares.
			if self.owner == None:
				fields = type(self.imageData).__dataclass_fields__
				self.setAttr(key,fields[key].default)
			else:
				self.setAttr(key,self.owner.getAttr(value[1:]))

	def toDict(self):
		data = self.imageData.toDict()
		for key,value in list(data.items()):
			if type(value) == str and value.startswith("@"):
				data[key] = self.getAttr(key)
		return data|{"image.frame":self.image.frame}

	def cacheKey(self):
		# a tuple of the fields that decide the pixels; building and hashing
		# one is a fraction of the cost of stringifying a dict, and this runs
		# twice per sprite per frame
		return tuple(getattr(self,field) for field in self._keyFields) + (self.image.frame,)

	def loadImage(self):
		self.imageData.load(self)
		self.resolveDynamicFields()
		self.textMode = self.text != None
		if self.textMode or self.image == None or self.path != self.oldPath:
			self.image = GIFPygame(self.frames)
			self.oldPath = self.path
		if self.scaleSize == -1:
			self.scaleSize = self.image.get_size()
		if self.cutSize == -1:
			# no cut asked for: match whatever the scale produced, so cutting
			# stays opt-in. Defaulting to the raw size instead would tile a
			# scaled down texture back up to the size of its own file.
			self.cutSize = self.scaleSize

	@ property
	def frames(self):
		if self.textMode:
			font = AssetsLoader.get("fonts",self.path)
			# rendered white so the colour field can tint it like any other
			# texture, in the one place colour is applied
			return [[font.render(self.text,self.fontSize),1]]
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
		self.resolveDynamicFields()
		cache = Image._cache
		key = self.cacheKey()
		frame = cache.pop(key,None)
		if frame == None:
			frame = self.currentFrame
			frame = pygame.transform.scale(frame,self.scaleSize)
			frame = self.cutImage(frame)
			frame = pygame.transform.scale_by(frame,self.factoredSize)
			frame.fill(self.color,special_flags=pygame.BLEND_RGBA_MULT)
			frame = pygame.transform.flip(frame,self.flipX,self.flipY)
			frame = pygame.transform.rotate(frame,self.angle)
			while len(cache) >= self._cacheLimit:
				del cache[next(iter(cache))]
		cache[key] = frame
		return frame

	def display(self,displaySurf,pos):
		displaySurf.blit(self.getRawImage(), pos)

	def cutImage(self,image):
		if image.get_size() == self.cutSize:
			return image
		try:
			# a crop, so a strip texture can show a piece of itself rather
			# than being squeezed whole into the target size
			return image.subsurface(pygame.Rect(0, 0, *self.cutSize)).copy()
		except ValueError:
			newImage = pygame.surface.Surface(self.cutSize,pygame.SRCALPHA)
			tile_w, tile_h = image.get_size()
			target_w, target_h = self.cutSize
			for y in range(0, target_h, tile_h):
				for x in range(0, target_w, tile_w):
					newImage.blit(image, (x, y))
			return newImage
