#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import operator
from collections import deque
from StringIO import StringIO
from optparse import OptionParser

import Image



logging.basicConfig()
log = logging.getLogger('png2svg')



def add_tuple(a, b):
    return tuple(map(operator.add, a, b))

def sub_tuple(a, b):
    return tuple(map(operator.sub, a, b))

def neg_tuple(a):
    return tuple(map(operator.neg, a))

def direction(edge):
    return sub_tuple(edge[1], edge[0])

def magnitude(a):
    return int(pow(pow(a[0], 2) + pow(a[1], 2), .5))

def normalize(a):
    mag = magnitude(a)
    assert mag > 0, "Cannot normalize a zero-length vector"
    return tuple(map(operator.div, a, [mag]*len(a)))
    
                           

def svg_header(width, height):
    return """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="%d" height="%d"
     xmlns="http://www.w3.org/2000/svg" version="1.1">
""" % (width, height)

def rgba_image_to_svg_pixels(im, opaque=None):
    s = StringIO()
    s.write(svg_header(*im.size))

    width, height = im.size
    for x in range(width):
        for y in range(height):
            here = (x, y)
            rgba = im.getpixel(here)
            if opaque and not rgba[3]:
                continue
            s.write("""  <rect x="%d" y="%d" width="1" height="1" style="fill:rgb%s; fill-opacity:%.3f; stroke:none;" />\n""" % (x, y, rgba[0:3], float(rgba[3]) / 255))
    s.write("""</svg>\n""")
    return s.getvalue()


def joined_edges(assorted_edges):
    pieces = []
    piece = []
    directions = deque([
        (0, 1),
        (1, 0),
        (0, -1),
        (-1, 0),
        ])
    while assorted_edges:
        if not piece:
            piece.append(assorted_edges.pop())
        current_direction = normalize(direction(piece[-1]))
        while current_direction != directions[2]:
            directions.rotate()
        for i in range(1, 4):
            next_end = add_tuple(piece[-1][1], directions[i])
            next_edge = (piece[-1][1], next_end)
            if next_edge in assorted_edges:
                assorted_edges.remove(next_edge)
                if i == 2:
                    # same direction
                    piece[-1] = (piece[-1][0], next_edge[1])
                else:
                    piece.append(next_edge)
                if piece[0][0] == piece[-1][1]:
                    if normalize(direction(piece[0])) == normalize(direction(piece[-1])):
                        piece[-1] = (piece[-1][0], piece.pop(0)[1])
                        # same direction
                    pieces.append(piece)
                    piece = []
                break
        else:
            raise Exception, "Failed to find connecting edge"
    return pieces


def rgba_image_to_svg_contiguous(im, opaque=None):

    # collect contiguous pixel groups
    
    adjacent = ((1, 0), (0, 1), (-1, 0), (0, -1))
    visited = Image.new("1", im.size, 0)
    
    color_pixel_lists = {}

    width, height = im.size
    for x in range(width):
        for y in range(height):
            here = (x, y)
            if visited.getpixel(here):
                continue
            rgba = im.getpixel((x, y))
            if opaque and not rgba[3]:
                continue
            piece = []
            queue = [here]
            visited.putpixel(here, 1)
            while queue:
                here = queue.pop()
                for offset in adjacent:
                    neighbour = add_tuple(here, offset)
                    if not (0 <= neighbour[0] < width) or not (0 <= neighbour[1] < height):
                        continue
                    if visited.getpixel(neighbour):
                        continue
                    neighbour_rgba = im.getpixel(neighbour)
                    if neighbour_rgba != rgba:
                        continue
                    queue.append(neighbour)
                    visited.putpixel(neighbour, 1)
                piece.append(here)

            if not rgba in color_pixel_lists:
                color_pixel_lists[rgba] = []
            color_pixel_lists[rgba].append(piece)

    del adjacent
    del visited

    # calculate clockwise edges of pixel groups

    edges = {
        (-1, 0):((0, 0), (0, 1)),
        (0, 1):((0, 1), (1, 1)),
        (1, 0):((1, 1), (1, 0)),
        (0, -1):((1, 0), (0, 0)),
        }
            
    color_edge_lists = {}

    for rgba, pieces in color_pixel_lists.items():
        for piece_pixel_list in pieces:
            edge_set = set([])
            for coord in piece_pixel_list:
                for offset, (start_offset, end_offset) in edges.items():
                    neighbour = add_tuple(coord, offset)
                    start = add_tuple(coord, start_offset)
                    end = add_tuple(coord, end_offset)
                    edge = (start, end)
                    if neighbour in piece_pixel_list:
                        continue
                    edge_set.add(edge)
            if not rgba in color_edge_lists:
                color_edge_lists[rgba] = []
            color_edge_lists[rgba].append(edge_set)

    del color_pixel_lists
    del edges

    # join edges of pixel groups

    color_joined_pieces = {}

    for color, pieces in color_edge_lists.items():
        color_joined_pieces[color] = []
        for assorted_edges in pieces:
            color_joined_pieces[color].append(joined_edges(assorted_edges))

    s = StringIO()
    s.write(svg_header(*im.size))

    for color, shapes in color_joined_pieces.items():
        for shape in shapes:
            s.write(""" <path d=" """)
            for sub_shape in shape:
                here = sub_shape.pop(0)[0]
                s.write(""" M %d,%d """ % here)
                for edge in sub_shape:
                    here = edge[0]
                    s.write(""" L %d,%d """ % here)
                s.write(""" Z """)
            s.write(""" " style="fill:rgb%s; fill-opacity:%.3f; stroke:none;" />\n""" % (color[0:3], float(color[3]) / 255))
            
    s.write("""</svg>\n""")
    return s.getvalue()
    
                
        


def png_to_svg(filename, contiguous=None, opaque=None):
    try:
        im = Image.open(filename)
    except IOError, e:
        sys.stderr.write('%s: Could not open as image file\n' % filename)
        sys.exit(1)
    im_rgba = im.convert('RGBA')
    
    if contiguous:
        return rgba_image_to_svg_contiguous(im_rgba, opaque)
    else:
        return rgba_image_to_svg_pixels(im_rgba, opaque)
    


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", dest="verbosity", help="Print verbose information for debugging", default=None)
    parser.add_option("-q", "--quiet", action="store_false", dest="verbosity", help="Suppress warnings", default=None)
    parser.add_option("-p", "--pixels", action="store_false", dest="contiguous", help="Generate a separate shape for each pixel; do not group pixels into contiguous areas of the same colour", default=True)
    parser.add_option("-o", "--opaque", action="store_true", dest="opaque", help="Opaque only; do not create shapes for fully transparent pixels. ", default=None)
    
    (options, args) = parser.parse_args()
    
    if options.verbosity == True:
        log.setLevel(logging.DEBUG)
    elif options.verbosity == False:
        log.setLevel(logging.ERROR)

    assert len(args) == 1, "Usage: %s [FILE]"
    print png_to_svg(args[0], contiguous=options.contiguous, opaque=options.opaque)
