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

def apply_pattern(fp, max_brightness=140, near_grey_th=25, hue_range=(20, 50)):
	img = Image.open(fp).convert("RGBA")
	img = resize(img)
	bs = bytearray(img.tobytes())
	
	COLOURS = [
		(0, 0, 235),
		(255, 255, 255),
		(235, 0, 0),
	]
	
	getindex = lambda x, y, i: 4 * (y * img.width + x) + i
	
	def isneargreys(r, g, b):
		return abs(r - g) <= near_grey_th and abs(g - b) <= near_grey_th and abs(r - b) <= near_grey_th
	
	def istoobright(r, g, b):
		return min(r, g, b) >= max_brightness
	
	def isCand(r, g, b):
		hue = gethue(r, g, b)
		return (hue_range[0] <= hue <= hue_range[1]) and not isneargreys(r,g,b) and not istoobright(r,g,b)
	
	# First and last pixel x coord where a pixel to recolour was found
	minW = img.width
	maxW = 0
	
	# Find least and greatest matching hues
	for y in range(img.height):
		for x in range(img.width):
			r, g, b = bs[getindex(x, y, 0)], bs[getindex(x, y, 1)], bs[getindex(x, y, 2)]
			
			if isCand(r, g, b):
				if x < minW:
					minW = x
				
				if x > maxW:
					maxW = x
	
	getcindex = lambda x: min(int(((x - minW) / (maxW - minW)) * len(COLOURS)), len(COLOURS) - 1)
	
	for y in range(img.height):
		# for x in range(img.width):
		for x in range(minW, maxW):
			r, g, b = bs[getindex(x, y, 0)], bs[getindex(x, y, 1)], bs[getindex(x, y, 2)]
			
			if isCand(r, g, b):
				w = max(r, g, b) - min(r, g, b)
				c = COLOURS[getcindex(x)]
				
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
	fp = apply_pattern(BytesIO(pathlib.Path(sys.argv[1]).read_bytes()))
	pathlib.Path(sys.argv[1] + "-output.png").write_bytes(fp.getbuffer())
