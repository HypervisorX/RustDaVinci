import cv2 
import numpy as np
import re
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from modules.canvasController.canvasController import CanvasController

class PlotOnScreenshot:
   def __init__(self):
      self._canvasController = CanvasController()

   def annotate_screenshot(self, screenshot_path: Path):
      # convert string to path if given string
      screenshot_path = Path(screenshot_path) if isinstance(screenshot_path, str) else screenshot_path

      # color image for drawing on, converted from opencv standard BGR to RGB for viewing on plot.
      img = cv2.cvtColor(cv2.imread(str(screenshot_path)), cv2.COLOR_BGR2RGB)
      
      # gray image for sending to object recognition
      gray_img = np.array(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY))

      # short name for the canvasController just to save text space
      cc = self._canvasController

      # reset all saved template coordinates      
      cc.reset_canvas_template_coordinates()
      

      updated, failed = cc.update_controls_coordinates(force=True, alternative_screenshot=gray_img)
      # TODO show info in cases of failed detection and subsequent control calibration failures?
      calibrated = cc.calibrate_controls()
      
      # access private config method for testing to verify/draw locations
      config = cc._read_config()

      fig, ax = plt.subplots()
      fig.suptitle(screenshot_path.name)
      plt.imshow(img)
      for control, coordinates in config['canvas_controls_template_coordinates'].items(): 
         if coordinates is not None:
            w = coordinates[2] - coordinates[0]
            h = coordinates[3] - coordinates[1]
            
            #draw control area bounding box
            ax.add_patch(Rectangle((coordinates[0], coordinates[1]), w, h, fill=False, linestyle='--', edgecolor='green'))
            
      # plot all the center points generated from calibrate_controls
      self.plot_point_series(cc._brush_types_coord)
      self.plot_color_series(cc._colour_coord)
      self.plot_point_series(cc._tools_coord)
      
      # additional singular coordinates of buttons etc that are not part of a series
      additional_coords = [
         cc._brush_opacity_coord, 
         cc._clear_canvas_coord, 
         cc._save_to_desktop_coord, 
         cc._save_changes_continue_coord, 
         cc._undo_coord, 
         cc._redo_coord, 
         cc._reset_camera_position_coord, 
         cc._toggle_light_coord, 
         cc._toggle_chat_coord, 
         cc._brush_size_coord, 
         cc._brush_spacing_coord, 
         cc._brush_opacity_coord, 
         cc._save_changes_exit_coord, 
         cc._cancel_coord, 
         cc._colour_display_coord]

      for coord in additional_coords:
         if coord is not None:
            self.plot_point(coord)
            # TODO potentially show some error or info regarding missing coordinates
   
      if not failed:
         # All canvas control templates detected
         ax.set_title('All templates detected', color='green')
      else:
         ax.set_title(f'Failed to detect templates: {failed}', color='red')

      # Maximize the plot window, works on Windows with default backend, likely doesnt work everywhere
      plt.get_current_fig_manager().window.state('zoomed')
      plt.show(block=True)
      
   def plot_color_series(self, series, marker='x'):
      for row in series:
         self.plot_point_series(row, marker='x')

   def plot_point_series(self, series, marker='x'):
      for point in series:
         if point is not None:
             plt.plot(point[0], point[1], marker)

   def plot_point(self, point, marker='x'):
         if point is not None:
            plt.plot(point[0], point[1], marker)
      

   def test_sample_screenshots(self):
      # directory with sample screenshot images
      samples = Path("..", "screenshots", "test-images")

      #filename pattern
      regex = r'(?P<width>[0-9]{2,4})x(?P<height>[0-9]{2,4}).png'

      # png files to check if pattern matches 
      screenshots = samples.glob('*.png')
      
      # single screenshot instead of entire folder
      # screenshots = [samples / '1920x1080.png']

      for file in screenshots:
         match = re.search(regex, file.name)
         if match:
               # w/h extracted from filename
               #w = int(match.group('width'))
               #h = int(match.group('height'))
               self.annotate_screenshot(file)                  

plotter = PlotOnScreenshot()
plotter.annotate_screenshot("../screenshots/test-images/1920x1080.png")
#plotter.test_sample_screenshots()