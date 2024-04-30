import cv2 
import numpy as np
import glob
import re
import os
from sys import path
from matplotlib import pyplot as plt
from PyQt5.QtCore import QSettings
#add parent directory to path for importing lib modules etc
path.insert(0, os.path.join(path[0], ".."))
from lib.rustDaVinci import rustDaVinci
from ui.settings.settings import Settings

class ScreenshotDrawer:
   def __init__(self):
      self.rustDaVinci = rustDaVinci(self)
      # TODO: find less hacky way to make QSettings work so that the rustDaVinci lib works properly with this test
      self.rustDaVinci.settings = QSettings("screenshot.ini", QSettings.IniFormat)
      
      

   def draw_screenshot(self, screenshot_path):
      ctrl_area = self.rustDaVinci.locate_control_area_opencv(screenshot_path)
      img = cv2.imread(screenshot_path)
      # write calculated area to settings to where rustDaVinci lib is expecting it
      self.rustDaVinci.settings.setValue("ctrl_x", str(ctrl_area[0]))
      self.rustDaVinci.settings.setValue("ctrl_y", str(ctrl_area[1]))
      self.rustDaVinci.settings.setValue("ctrl_w", str(ctrl_area[2]))
      self.rustDaVinci.settings.setValue("ctrl_h", str(ctrl_area[3]))

      # call after updating settings object to recalculate values
      self.rustDaVinci.calculate_ctrl_tools_positioning()
      

      #draw control area bounding box
      topleft = (ctrl_area[0], ctrl_area[1])
      #coordinates of top left + width/height
      bottom_right = (ctrl_area[0]+ctrl_area[2], ctrl_area[1]+ctrl_area[3])
      cv2.rectangle(img, topleft, bottom_right, (0,255,0), 2)

      plt.xlim 
      plt.ylim
      # plot all the point based locations
      self.plot_point_series(self.rustDaVinci.ctrl_brush)
      self.plot_point_series(self.rustDaVinci.ctrl_opacity)
      self.plot_point_series(self.rustDaVinci.ctrl_size)
      self.plot_point_series(self.rustDaVinci.ctrl_color)

      #update and remove
      plt.plot(self.rustDaVinci.ctrl_update[0], self.rustDaVinci.ctrl_update[1], 'x')
      plt.plot(self.rustDaVinci.ctrl_remove[0], self.rustDaVinci.ctrl_remove[1], 'x')
      
      #set x/y limit to zoom into area of screenshot that matters
      plt.xlim(ctrl_area[0]-50, ctrl_area[0]+ctrl_area[2]+10)
      #limit on Y axis is max, then min
      plt.ylim(ctrl_area[1]+ctrl_area[3]+10,ctrl_area[1]-50)
      plt.imshow(img)
      plt.show()

   def plot_point_series(self, series, marker='x'):
      for point in series:
         plt.plot(point[0], point[1], marker)

   def test_methods(self):
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

drawer = ScreenshotDrawer()
drawer.draw_screenshot("opencv_template/rust_example_screenshot_before_10y_update.png")
input("Press [enter] to continue.")