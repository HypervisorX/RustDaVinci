#!/usr/bin/env python3

# pip install scikit-image
# pip install scipy

import numpy as np
from PIL import Image
from skimage import color

def CIE76DeltaE2(Lab1,Lab2):
    """Returns the square of the CIE76 Delta-E colour distance between 2 lab colours"""
    return (Lab2[0]-Lab1[0])*(Lab2[0]-Lab1[0]) + (Lab2[1]-Lab1[1])*(Lab2[1]-Lab1[1]) + (Lab2[2]-Lab1[2])*(Lab2[2]-Lab1[2])

def NearestPaletteIndex(Lab,palLab):
    """Return index of entry in palette that is nearest the given colour"""
    NearestIndex = 0
    NearestDist   = CIE76DeltaE2(Lab,palLab[0,0])
    for e in range(1,palLab.shape[0]):
        dist = CIE76DeltaE2(Lab,palLab[e,0])
        if dist < NearestDist:
            NearestDist = dist
            NearestIndex = e
    return NearestIndex

palette = (
        0, 0, 0,    115, 116, 115,  192, 192, 192,  255, 255, 255,
        52, 33, 22, 101, 65, 41,    255, 134, 52,   255, 178, 126,
        52, 45, 22, 101, 90, 41,    255, 215, 52,   255, 230, 126,
        46, 51, 22, 90, 102, 41,    214, 255, 52,   231, 255, 126,
        33, 51, 22, 66, 102, 41,    132, 255, 52,   178, 255, 126,
        22, 51, 22, 41, 102, 41,    52, 255, 52,    129, 255, 126,
        22, 51, 33, 41, 102, 66,    52, 255, 132,   126, 255, 178,
        22, 51, 46, 41, 102, 90,    52, 255, 214,   126, 255, 228,
        22, 45, 52, 41, 90, 101,    52, 215, 255,   126, 230, 255,
        22, 33, 52, 41, 65, 101,    52, 134, 255,   126, 178, 255,
        22, 20, 52, 41, 41, 101,    52, 51, 255,    129, 127, 255,
        33, 20, 52, 66, 41, 101,    132, 51, 255,   178, 127, 255,
        46, 20, 52, 90, 41, 101,    214, 51, 255,   231, 127, 255,
        52, 20, 46, 101, 41, 90,    255, 51, 214,   255, 127, 228,
        52, 20, 33, 101, 41, 66,    255, 51, 132,   255, 127, 178,
        52, 20, 22, 101, 41, 41,    255, 51, 52,    255, 127, 126,
) + (2, 2, 2) * 176

# Load the source image as numpy array and convert to Lab colorspace
imnp = np.array(Image.open('C:\\Users\\Alexander\\Downloads\\aaa.png').convert('RGB'))
imLab = color.rgb2lab(imnp)
h,w = imLab.shape[:2]

# Load palette as numpy array, truncate unused palette entries, and convert to Lab colourspace
palnp = np.array(palette,dtype=np.uint8).reshape(256,1,3)[:80,:]
palLab = color.rgb2lab(palnp)

# Make numpy array for output image
resnp = np.empty((h,w), dtype=np.uint8)

# Iterate over pixels, replacing each with the nearest palette entry
for y in range(0, h):
    for x in range(0, w):
        resnp[y, x] = NearestPaletteIndex(imLab[y,x], palLab)

# Create output image from indices, whack a palette in and save
resim = Image.fromarray(resnp, mode='P')
resim.putpalette(palette)
#resim.save('result.png')
resim.show()
