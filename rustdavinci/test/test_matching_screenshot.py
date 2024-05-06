import cv2 
import numpy as np
import glob
import re
from matplotlib import pyplot as plt

def draw_sub_plot(image, title: str, rows: int, columns: int, index: int):
   plt.subplot(rows, columns, index)
   plt.imshow(image)
   plt.title(title), plt.xticks([]), plt.yticks([])

# assign directory
directory = "rustdavinci/opencv_template/"

#filename pattern
regex = r'(?P<width>[0-9]{2,4})x(?P<height>[0-9]{2,4})_trim.png'
# iterate over files in
# that directory
#screenshots = glob.iglob(f'{directory}/*.png')
screenshots = ['rustdavinci/opencv_template/1920x1080_trim.png']

template = {}
template['colour'] = cv2.imread('rustdavinci/opencv_template/template_colour.png', cv2.IMREAD_GRAYSCALE)
template['tools'] = cv2.imread('rustdavinci/opencv_template/template_tools.png', cv2.IMREAD_GRAYSCALE)

assert template['colour'] is not None, "colour template file could not be read, check with os.path.exists()"
assert template['tools'] is not None, "tools template file could not be read, check with os.path.exists()"

for filename in screenshots:
    match = re.search(regex, filename)
    if match:
         #
         w = int(match.group('width'))
         h = int(match.group('height'))
         img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE) 
         assert img is not None, "file could not be read, check with os.path.exists()"
         #img2 = img.copy()
         # All the 6 methods for comparison in a list
         # methods = ['cv2.TM_CCOEFF', 'cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR',
         # 'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']
         methods = ['cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF_NORMED']
         for meth in methods:
            # make copy of screenshot image to draw on with color
            result_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            for t_name, t_image in template.items():
               
               w, h = t_image.shape[::-1]
               method = eval(meth)
               # Apply template Matching
               res = cv2.matchTemplate(img,t_image,method)
               min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
               # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
               if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                  top_left = min_loc
               else:
                  top_left = max_loc

               bottom_right = (top_left[0] + w, top_left[1] + h)
               cv2.rectangle(result_img,top_left, bottom_right, (0,255,0), 2)
               
            plt.subplot(121),plt.imshow(res,cmap = 'gray')
            plt.title(f'Matching Result {min_val}, {max_val}'), plt.xticks([]), plt.yticks([])
            plt.subplot(122),plt.imshow(result_img)
            plt.title('Detected Point'), plt.xticks([]), plt.yticks([])
            plt.show()

