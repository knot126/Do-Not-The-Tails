#!/usr/bin/env python3
"""
Tails flagifier v2

Replaces red-orange colours on drawings of Tails with the colours of a specified
image (usually a pride flag).

This verison uses a raster texture of the flag which is scaled and then applied
to relevant pixels. This is opposed to the previous way of doing things which
drew flags with basic vector math, thus it could only handle flags with stripes.
"""

from PIL import Image
from io import BytesIO
from pathlib import Path
import json
import os

class FlagNotInNameListError(Exception):
	pass

def get_flag_dir():
	return str(Path(__file__).parent) + "/flags"

def get_flag_name_list():
	return [x.removesuffix(".png") for x in os.listdir(get_flag_dir())]

def correct_scale(img, max_dem=500):
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

def getlightness(r, g, b):
	return 0.5 * (max(r, g, b) + min(r, g, b)) * (100/255)

def getsaturation(r, g, b):
	# not actually saturation ;p
	return (max(r, g, b) - min(r, g, b)) * (100/255)

def getvalue(r, g, b):
	return max(r, g, b) * (100/255)

def flagify(fp, value_range=(0, 100), saturation_range=(40, 100), hue_range=(10, 60), flag_texture=None):
	"""
	Smartly blend an image of Tails with another texture, so that it appear to
	replace his orange fur colour. Works best with flat and cell shaded images.
	"""
	
	img = Image.open(fp).convert("RGBA")
	img = correct_scale(img)
	bs = bytearray(img.tobytes())
	
	if flag_texture not in get_flag_name_list():
		raise FlagNotInNameListError("Flag not in name list!")
	
	getindex = lambda x, y, i: 4 * (y * img.width + x) + i
	
	def isgoodvalue(r, g, b):
		return value_range[0] <= getvalue(r, g, b) <= value_range[1]
	
	def isgoodsat(r, g, b):
		return saturation_range[0] <= getsaturation(r, g, b) <= saturation_range[1]
	
	def isgoodhue(r, g, b):
		hue = gethue(r, g, b)
		return (hue_range[0] <= hue <= hue_range[1]) or (360 + hue_range[0]) <= hue <= (360 + hue_range[1])
	
	def isCand(r, g, b):
		return isgoodvalue(r,g,b) and isgoodsat(r,g,b) and isgoodhue(r, g, b)
	
	# First and last pixel x coord where a pixel to recolour was found
	minX = img.width
	maxX = 0
	minY = img.height
	maxY = 0
	
	# Find least and greatest matching hues
	for y in range(img.height):
		for x in range(img.width):
			r, g, b = bs[getindex(x, y, 0)], bs[getindex(x, y, 1)], bs[getindex(x, y, 2)]
			
			if isCand(r, g, b):
				if x < minX:
					minX = x
				
				if x > maxX:
					maxX = x
				
				if y < minY:
					minY = y
				
				if y > maxY:
					maxY = y
	
	areaWidth = maxX - minX + 1
	areaHeight = maxY - minY + 1
	
	# Load the flag, rescale it, convert to bytes
	flag_data = bytearray(Image.open(f"{get_flag_dir()}/{flag_texture}.png").convert("RGB").resize((areaWidth, areaHeight)).tobytes())
	
	# Blend flag texture and tails image :3
	for y in range(minY, maxY+1):
		for x in range(minX, maxX+1):
			r, g, b = bs[getindex(x, y, 0)], bs[getindex(x, y, 1)], bs[getindex(x, y, 2)]
			
			if isCand(r, g, b):
				w = max(r, g, b)
				i = 3 * ((y - minY) * (areaWidth) + (x - minX))
				
				r = (flag_data[i] * w) // 255
				g = (flag_data[i+1] * w) // 255
				b = (flag_data[i+2] * w) // 255
				
				bs[getindex(x, y, 0)] = r
				bs[getindex(x, y, 1)] = g
				bs[getindex(x, y, 2)] = b
	
	img.frombytes(bs)
	b = BytesIO()
	img.save(b, "png")
	b.seek(0, 0)
	return b

def _main():
	import argparse, pathlib
	
	args = argparse.ArgumentParser(
		prog="dntt_image",
		description="RoboTails image manipulation",
	)
	args.add_argument('filename')
	args.add_argument('-F', '--flag', help=", ".join(get_flag_name_list()) + ", *", default="french")
	args.add_argument('-H', '--hue', help="min,max", default="10,60")
	args.add_argument('-S', '--sat', help="min,max", default="40,100")
	args.add_argument('-V', '--val', help="min,max", default="0,100")
	args = args.parse_args()
	
	def toRange(s): return [float(x) for x in s.split(",")]
	
	flags = [args.flag] if args.flag != "*" else get_flag_name_list()
	
	for flag in flags:
		fp = flagify(
			BytesIO(pathlib.Path(args.filename).read_bytes()),
			flag_texture=flag,
			value_range=toRange(args.val),
			saturation_range=toRange(args.sat),
			hue_range=toRange(args.hue),
		)
		
		pathlib.Path(args.filename[:-4] + f"{flag.title()}.png").write_bytes(fp.getbuffer())

if __name__ == "__main__":
	_main()
