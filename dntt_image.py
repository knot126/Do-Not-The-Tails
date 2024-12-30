#!/usr/bin/env python3
from PIL import Image
from io import BytesIO

def resize(img, max_dem=500):
	factor = max(img.width, img.height) / max_dem
	
	if factor > 1:
		return img.resize((int(img.width / factor), int(img.height / factor)))
	
	return img

def gethue(r, g, b):
	r, g, b = r/255, g/255, b/255
	a, x = min(r, g, b), max(r, g, b)
	
	if (a == x):
		return 0
	
	if (r > g) and (r > b):
		h = (g - b)/(x - a)
	elif (g > r) and (g > b):
		h = 2.0 + (b - r)/(x - a)
	else:
		h = 4.0 + (r - g)/(x - a)
	
	return 60 * h if h >= 0.0 else 360 + (60 * h)

NAMED_STRIPES = {
	"french": {
		"stripes": (
			(0, 0, 235),
			(255, 255, 255),
			(235, 0, 0),
		),
		"horizontal": False,
	},
	"aroace": {
		"stripes": (
			(226, 140, 0),
			(236, 205, 0),
			(255, 255, 255),
			(98, 174, 220),
			(32, 56, 86),
		),
	},
	"bi": {
		"stripes": (
			(214, 2, 112),
			(214, 2, 112),
			(155, 79, 150),
			(0, 56, 168),
			(0, 56, 168),
		),
	},
	"asexual": {
		"stripes": (
			(0, 0, 0),
			(127, 127, 127),
			(255, 255, 255),
			(127, 0, 127),
		),
	},
	"pride": {
		"stripes": (
			(229, 0, 0),
			(255, 141, 0),
			(255, 238, 0),
			(2, 129, 33),
			(0, 76, 255),
			(119, 0, 136),
		),
	},
	"transgender": {
		"stripes": (
			(91, 206, 250),
			(245, 169, 184),
			(255, 255, 255),
			(245, 169, 184),
			(91, 206, 250),
		),
	},
	"pan": {
		"stripes": (
			(255, 33, 140),
			(255, 216, 0),
			(33, 177, 255),
		),
	},
	"nonbinary": {
		"stripes": (
			(255, 244, 51),
			(255, 255, 255),
			(155, 89, 208),
			(45, 45, 45),
		),
	},
	"aromantic": {
		"stripes": (
			(61, 165, 66),
			(167, 211, 121),
			(255, 255, 255),
			(169, 169, 169),
			(0, 0, 0),
		),
	},
	"lesbian": {
		"stripes": (
			(213, 45, 0),
			(255, 154, 86),
			(255, 255, 255),
			(211, 98, 164),
			(163, 2, 98),
		),
	},
	"gaymen": {
		"stripes": (
			(7, 141, 112),
			(38, 206, 170),
			(153, 232, 194),
			(255, 255, 255),
			(123, 173, 227),
			(80, 73, 203),
			(62, 26, 120),
		),
	}
}

def get_flag_name_list():
	return NAMED_STRIPES.keys()

def apply_pattern(fp, max_brightness=140, near_grey_th=25, hue_range=(20, 50), stripes="french", horizontal=None):
	img = Image.open(fp).convert("RGBA")
	img = resize(img)
	bs = bytearray(img.tobytes())
	
	if type(stripes) not in (list, tuple):
		horizontal = horizontal if horizontal != None else NAMED_STRIPES[stripes].get("horizontal", True)
		stripes = NAMED_STRIPES[stripes]["stripes"]
	
	getindex = lambda x, y, i: 4 * (y * img.width + x) + i
	
	# TODO: Maybe have the option to disable grey(lightness?) checking?
	def isneargreys(r, g, b):
		return abs(r - g) <= near_grey_th and abs(g - b) <= near_grey_th and abs(r - b) <= near_grey_th
	
	# TODO: Maybe redo this to a brightness range?
	def istoobright(r, g, b):
		return min(r, g, b) >= max_brightness
	
	def isgoodhue(r, g, b):
		hue = gethue(r, g, b)
		return (hue_range[0] <= hue <= hue_range[1]) or (360 + hue_range[0]) <= hue <= (360 + hue_range[1])
	
	def isCand(r, g, b):
		return isgoodhue(r, g, b) and not isneargreys(r,g,b) and not istoobright(r,g,b)
	
	# First and last pixel x coord where a pixel to recolour was found
	minW = img.width
	maxW = 0
	minH = img.height
	maxH = 0
	
	# Find least and greatest matching hues
	for y in range(img.height):
		for x in range(img.width):
			r, g, b = bs[getindex(x, y, 0)], bs[getindex(x, y, 1)], bs[getindex(x, y, 2)]
			
			if isCand(r, g, b):
				if x < minW:
					minW = x
				
				if x > maxW:
					maxW = x
				
				if y < minH:
					minH = y
				
				if y > maxH:
					maxH = y
	
	getBandIndexX = lambda x: min(int(((x - minW) / (maxW - minW)) * len(stripes)), len(stripes) - 1)
	getBandIndexY = lambda y: min(int(((y - minH) / (maxH - minH)) * len(stripes)), len(stripes) - 1)
	
	for y in range(minH, maxH+1):
		# for x in range(img.width):
		for x in range(minW, maxW+1):
			r, g, b = bs[getindex(x, y, 0)], bs[getindex(x, y, 1)], bs[getindex(x, y, 2)]
			
			if isCand(r, g, b):
				w = max(r, g, b)# - min(r, g, b)
				c = stripes[getBandIndexY(y) if horizontal else getBandIndexX(x)]
				
				r = (c[0] * w) // 255
				g = (c[1] * w) // 255
				b = (c[2] * w) // 255
				
				bs[getindex(x, y, 0)] = r
				bs[getindex(x, y, 1)] = g
				bs[getindex(x, y, 2)] = b
	
	img.frombytes(bs)
	b = BytesIO()
	img.save(b, "png")
	b.seek(0, 0)
	return b

if __name__ == "__main__":
	import sys, pathlib
	fp = apply_pattern(BytesIO(pathlib.Path(sys.argv[1]).read_bytes()), stripes=sys.argv[2])
	pathlib.Path(sys.argv[1] + "-output.png").write_bytes(fp.getbuffer())
