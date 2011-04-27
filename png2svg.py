#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import Image

from StringIO import StringIO        

def rgba_image_to_svg(im):
    s = StringIO()
    s.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="%d" height="%d">\n""" % im.size)

    width, height = im.size
    for x in range(width):
        for y in range(height):
            rgba = im.getpixel((x, y))
            s.write("""  <rect x="%d" y="%d" width="1" height="1" style="fill:rgb%s; fill-opacity:%.3f; stroke:none;" />\n""" % (x, y, rgba[0:3], float(rgba[3])/255))
    s.write("""</svg>\n""")
    return s.getvalue()

def png_to_svg(filename):
    try:
        im = Image.open(filename)
    except IOError, e:
        sys.stderr.write('%s: Could not open as image file\n' % filename)
        sys.exit(1)
    im_rgba = im.convert('RGBA')
    
    print rgba_image_to_svg(im_rgba)
    


if __name__ == "__main__":
    assert len(sys.argv) == 2, "Usage: %s [FILE]"
    png_to_svg(sys.argv[1])
