#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import QSettings, Qt, QRect, QDir
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QApplication, QLabel

from pynput import keyboard
from io import BytesIO
from PIL import Image

import urllib.request
import pyautogui
import datetime
import numpy
import time
import cv2
import os

from lib.rustPaletteData import rust_palette
from lib.captureArea import capture_area
from lib.color_functions import hex_to_rgb, rgb_to_hex
from ui.dialogs.captureDialog import CaptureAreaDialog
from ui.settings.default_settings import default_settings

# TODO: fix usage of casting boolean values from settings to use type="bool" instead of directly casting as bool("0") = TRUE

class rustDaVinci():

    def __init__(self, parent):
        """ RustDaVinci class init """
        self.parent = parent
        self.settings = QSettings()

        # PIL.Image images original/ quantized
        self.org_img_template = None
        self.org_img = None
        self.quantized_img = None
        self.palette_data = None
        self.updated_palette = None

        # Pixmaps
        self.pixmap_on_display = 0
        self.org_img_pixmap = None
        self.quantized_img_pixmap_normal = None
        self.quantized_img_pixmap_high = None

        # Booleans
        self.org_img_ok = False
        self.use_double_click = False
        self.use_hidden_colors = False

        # Keyboard interrupt variables
        self.pause_key = None
        self.skip_key = None
        self.abort_key = None
        self.paused = False
        self.skip_current_color = False
        self.abort = False

        # Painting control tools
        self.ctrl_remove = (0,0)
        self.ctrl_update = (0,0)
        self.ctrl_size = (0,0)
        self.ctrl_spacing = (0,0)
        self.ctrl_opacity = (0,0)
        self.ctrl_brush = []
        self.ctrl_color = []
        self.current_ctrl_size = None
        self.current_ctrl_brush = None
        self.current_ctrl_opacity = None
        self.current_ctrl_color = None

        # Canvas coordinates/ ratio
        self.canvas_x = 0
        self.canvas_y = 0
        self.canvas_w = 0
        self.canvas_h = 0

        # Statistics
        self.img_colors = []
        self.tot_pixels = 0
        self.pixels = 0
        self.lines = 0
        self.estimated_time = 0

        # Delays
        self.click_delay = 0
        self.line_delay = 0
        self.ctrl_area_delay = 0
        self.use_double_click = False

        self.background_color = None
        self.skip_colors = None

        # Hotkey display QLabel
        self.hotkey_label = None


        # Init functions
        if not (int(self.settings.value("ctrl_w", default_settings["ctrl_w"])) == 0 or int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))):
            self.calculate_ctrl_tools_positioning()


    def update(self):
        """ Updates pyauogui delays, booleans and paint image button"""
        self.click_delay = float(int(self.settings.value("click_delay", default_settings["click_delay"]))/1000)
        self.line_delay = float(int(self.settings.value("line_delay", default_settings["line_delay"]))/1000)
        self.ctrl_area_delay = float(int(self.settings.value("ctrl_area_delay", default_settings["ctrl_area_delay"]))/1000)
        self.use_double_click = bool(self.settings.value("double_click", default_settings["double_click"]))

        # Update the pyautogui delay
        pyautogui.PAUSE = self.click_delay

        # TODO use any on values
        if int(self.settings.value("ctrl_w", default_settings["ctrl_w"])) == 0 or int(self.settings.value("ctrl_h", default_settings["ctrl_h"])) == 0:
            self.parent.ui.paint_image_PushButton.setEnabled(False)
        elif self.org_img_ok and int(self.settings.value("ctrl_w", default_settings["ctrl_w"])) != 0 and int(self.settings.value("ctrl_h", default_settings["ctrl_h"])) != 0:
            self.parent.ui.paint_image_PushButton.setEnabled(True)


    def load_image_from_file(self):
        """ Load image from a file """
        title = "Select the image to be painted"
        fileformats = "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        folder_path = self.settings.value("folder_path", QDir.homePath())
        folder_path = os.path.dirname(os.path.abspath(folder_path))
        if not os.path.exists(folder_path):
            folder_path = QDir.homePath()

        path = QFileDialog.getOpenFileName(self.parent, title, folder_path, fileformats)[0]

        if path.endswith(('.png', '.jpg', 'jpeg', '.gif', '.bmp')):
            try:
                self.settings.setValue("folder_path", path)
                # Pixmap for original image
                self.org_img_pixmap = QPixmap(path, "1")

                # The original PIL.Image object
                self.org_img_template = Image.open(path).convert("RGBA")
                self.org_img = self.org_img_template

                self.convert_transparency()
                self.create_pixmaps()

                if bool(self.settings.value("show_preview_load", default_settings["show_preview_load"])):
                    if int(self.settings.value("quality", default_settings["quality"])) == 0:
                        self.pixmap_on_display = 1
                    else:
                        self.pixmap_on_display = 2

                    if self.parent.is_expanded:
                        self.parent.label.hide()
                    self.parent.expand_window()
                else:
                    self.pixmap_on_display = 0

                self.parent.ui.log_TextEdit.clear()
                self.parent.ui.progress_ProgressBar.setValue(0)

            except Exception as e:
                self.org_img = None
                self.org_img_ok = False
                msg = QMessageBox(self.parent)
                msg.setIcon(QMessageBox.Critical)
                msg.setText("ERROR! Could not load the selected image...")
                msg.setInformativeText(str(e))
                msg.exec_()

        self.update()


    def load_image_from_url(self):
        """ Load image from url """
        dialog = QInputDialog(self.parent)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setLabelText("Load image from URL:")
        dialog.resize(500,100)
        ok_clicked = dialog.exec_()
        url = dialog.textValue()

        if ok_clicked and url != "":
            try:
                headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}
                request = urllib.request.Request(url, None, headers)
                self.org_img_template = Image.open(urllib.request.urlopen(request)).convert("RGBA")

                # Pixmap for original image
                self.org_img_template.save("temp_url_image.png")
                self.org_img_pixmap = QPixmap("temp_url_image.png", "1")
                os.remove("temp_url_image.png")

                # The original PIL.Image object
                self.org_img = self.org_img_template

                self.convert_transparency()
                self.create_pixmaps()

                if bool(self.settings.value("show_preview_load", default_settings["show_preview_load"])):
                    if int(self.settings.value("quality", default_settings["quality"])) == 0:
                        self.pixmap_on_display = 1
                    else:
                        self.pixmap_on_display = 2

                    if self.parent.is_expanded:
                        self.parent.label.hide()
                    self.parent.expand_window()
                else:
                    self.pixmap_on_display = 0

                self.parent.ui.log_TextEdit.clear()
                self.parent.ui.progress_ProgressBar.setValue(0)

            except Exception as e:
                self.org_img = None
                self.org_img_ok = False
                msg = QMessageBox(self.parent)
                msg.setIcon(QMessageBox.Critical)
                msg.setText("ERROR! Could not load the selected image...")
                msg.setInformativeText(str(e))
                msg.exec_()

        self.update()


    def convert_transparency(self):
        """ Paste the org_img on top of an image with background color """
        background_color = rust_palette.index(hex_to_rgb(self.settings.value("background_color", default_settings["background_color"])))
        # Set transparency in image to default background
        try:
            self.org_img = self.org_img_template
            temp_org_img = Image.new("RGBA", self.org_img.size, color=rust_palette[background_color])
            temp_org_img.paste(self.org_img, (0 ,0), mask=self.org_img)
            self.org_img = temp_org_img
            self.org_img = self.org_img.convert("RGB")
        except Exception as e:
            None


    def create_pixmaps(self):
        """ Create quantized pixmaps """
        # Pixmap for quantized image of quality normal
        temp_normal = self.quantize_to_palette(self.org_img, True, 0)
        temp_normal.save("temp_normal.png")
        self.quantized_img_pixmap_normal = QPixmap("temp_normal.png")
        os.remove("temp_normal.png")

        # Pixmap for quantized image of quality high
        temp_high = self.quantize_to_palette(self.org_img, True, 1)
        temp_high.save("temp_high.png")
        self.quantized_img_pixmap_high = QPixmap("temp_high.png")
        os.remove("temp_high.png")

        self.org_img_ok = True

    def convert_img(self):
        """ Convert the image to fit the canvas and quantize the image.
        Updates:    quantized_img,
                    x_correction,
                    y_correction
        Returns:    False, if the image type is invalid.
        """
        org_img_w = self.org_img.size[0]
        org_img_h = self.org_img.size[1]

        wpercent = (self.canvas_w / float(org_img_w))
        hpercent = (self.canvas_h / float(org_img_h))

        hsize = int((float(org_img_h) * float(wpercent)))
        wsize = int((float(org_img_w) * float(hpercent)))

        x_correction = 0
        y_correction = 0

        if hsize <= self.canvas_h:
            resized_img = self.org_img.resize((self.canvas_w, hsize), Image.ANTIALIAS)
            y_correction = int((self.canvas_h - hsize)/2)
        elif wsize <= self.canvas_w:
            resized_img = self.org_img.resize((wsize, self.canvas_h), Image.ANTIALIAS)
            x_correction = int((self.canvas_w - wsize)/2)
        else:
            resized_img = self.org_img.resize((self.canvas_w, self.canvas_h), Image.ANTIALIAS)

        self.quantized_img = self.quantize_to_palette(resized_img)
        if self.quantized_img == False:
            self.org_img = None
            self.quantized_img = None
            self.org_img_ok = False
            return False

        self.canvas_x += x_correction
        self.canvas_y += y_correction
        self.canvas_w = self.quantized_img.size[0]
        self.canvas_h = self.quantized_img.size[1]
        return True


    def update_palette(self, rgb_background):
        """  """
        use_hidden_colors = self.settings.value("hidden_colors", default_settings["hidden_colors"], type="bool")
        use_brush_opacities = bool(self.settings.value("brush_opacities", default_settings["brush_opacities"]))

        background_index = rust_palette.index(rgb_background)

        if self.settings.value("skip_background_color", default_settings["skip_background_color"]):
            background_opacities = [background_index % 256, (background_index+(64*1)) % 256, (background_index+(64*2)) % 256, (background_index+(64*3)) % 256]
        else:
            background_opacities = []

        # Select the palette to be used
        self.palette_data = Image.new("P", (1, 1))
        palette = ()
        self.updated_palette = []

        # Choose how many colors in the palette
        if use_hidden_colors:
            if use_brush_opacities:
                for i, color in enumerate(rust_palette):
                    if i in background_opacities:
                        palette = palette + rgb_background
                        self.updated_palette.append(rgb_background)
                    else:
                        palette = palette + color
                        self.updated_palette.append(color)
            else:
                for i, color in enumerate(rust_palette):
                    if i == 64:
                        palette = palette + (2, 2, 2) * 192
                        break
                    if i in background_opacities:
                        palette = palette + rgb_background
                        self.updated_palette.append(rgb_background)
                    else:
                        palette = palette + color
                        self.updated_palette.append(color)
        else:
            if use_brush_opacities:
                for i, color in enumerate(rust_palette):
                    if (i >= 0 and i <= 19) or (i >= 64 and i <= 83) or (i >= 128 and i <= 147) or (i >= 192 and i <= 211):
                        if i in background_opacities:
                            palette = palette + rgb_background
                            self.updated_palette.append(rgb_background)
                        else:
                            palette = palette + color
                            self.updated_palette.append(color)
                palette = palette + (2, 2, 2) * 176
            else:
                for i, color in enumerate(rust_palette):
                    if i == 63:
                        # The following line seems to break image loading when palette size changes
                        # explaination/investigation required 
                        palette = palette + (2, 2, 2) * 192
                        break
                    if i in background_opacities:
                        palette = palette + rgb_background
                        self.updated_palette.append(rgb_background)
                    else:
                        palette = palette + color
                        self.updated_palette.append(color)


        if rgb_background in self.updated_palette:
            if use_hidden_colors:
                self.background_color = self.updated_palette.index(rgb_background) % 64
            else:
                self.background_color = self.updated_palette.index(rgb_background) % 64
        else:
            self.background_color = None

        self.palette_data.putpalette(palette)
        self.palette_data.load()


    def quantize_to_palette(self, image, pixmap = False, pixmap_q = 0):
        """ Convert an RGB, RGBA or L mode image to use a given P image's palette.
        Returns:    The quantized image
        """
        rgb = hex_to_rgb(self.settings.value("background_color", default_settings["background_color"]))
        self.update_palette(rgb)

        self.org_img = image
        self.org_img.load()

        if self.org_img.mode == "RGBA":
            self.org_img = image.convert("RGB")

        if not pixmap:
            quality = int(self.settings.value("quality", default_settings["quality"]))
            if quality == 0:
                im = image.im.convert("P", 0, self.palette_data.im)
            elif quality == 1:
                im = image.im.convert("P", 1, self.palette_data.im) # Dithering
        else:
            im = image.im.convert("P", pixmap_q, self.palette_data.im)

        try: return image._new(im)
        except AttributeError: return image._makeself(im)


    def clear_image(self):
        """ Clear the image """
        self.org_img = None
        self.quantized_img = None
        self.org_img_ok = False
        self.update()


    def locate_canvas_area(self):
        """ Locate the coordinates/ ratio of the canvas area.
        Updates:    self.canvas_x,
                    self.canvas_y,
                    self.canvas_w,
                    self.canvas_h
        """
        dialog = CaptureAreaDialog(self.parent, 0)
        ans = dialog.exec_()
        if ans == 0: return False

        self.parent.hide()
        canvas_area = capture_area()
        self.parent.show()

        if canvas_area == False:
            return False
        elif canvas_area[2] == 0 or canvas_area[3] == 0:
            msg = QMessageBox(self.parent)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Invalid coordinates and ratio. Drag & drop the top left corner of the canvas to the bottom right corner.")
            msg.exec_()
            return False

        msg = QMessageBox(self.parent)
        msg.setIcon(QMessageBox.Information)
        msg.setText("Coordinates:\n" +
                    "X =\t\t" + str(canvas_area[0]) + "\n" +
                    "Y =\t\t" + str(canvas_area[1]) + "\n" +
                    "Width =\t" + str(canvas_area[2]) + "\n" +
                    "Height =\t" + str(canvas_area[3]))
        msg.exec_()

        self.canvas_x = canvas_area[0]
        self.canvas_y = canvas_area[1]
        self.canvas_w = canvas_area[2]
        self.canvas_h = canvas_area[3]
        return True


    def locate_control_area_manually(self):
        """"""
        dialog = CaptureAreaDialog(self.parent, 1)
        ans = dialog.exec_()
        if ans == 0: return False

        self.parent.hide()
        ctrl_area = capture_area()
        self.parent.show()

        if ctrl_area == False:
            self.update()
            return False
        elif ctrl_area[2] == 0 and ctrl_area[3] == 0:
            msg = QMessageBox(self.parent)
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Invalid coordinates and ratio. Drag & drop the top left corner of the canvas to the bottom right corner.")
            msg.exec_()
            self.update()
            return False

        btn = QMessageBox.question(self.parent, None,
            "Coordinates:\n" +
            "X =\t\t" + str(ctrl_area [0]) + "\n" +
            "Y =\t\t" + str(ctrl_area [1]) + "\n" +
            "Width =\t" + str(ctrl_area [2]) + "\n" +
            "Height =\t" + str(ctrl_area [3]) + "\n\n" +
            "Would you like to update the painting controls area coordinates?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if btn == QMessageBox.Yes:
            self.parent.ui.log_TextEdit.append("Controls area position updated...")
            self.settings.setValue("ctrl_x", str(ctrl_area[0]))
            self.settings.setValue("ctrl_y", str(ctrl_area[1]))
            self.settings.setValue("ctrl_w", str(ctrl_area[2]))
            self.settings.setValue("ctrl_h", str(ctrl_area[3]))

        self.update()

    def format_coordinates(self, coordinates, name=None) -> str:
        coords = (f'{name if name else ""}Coordinates:\nX =\t\t{coordinates["x"]}\n'
            f'Y =\t\t{coordinates["y"]}\n'
            f'Width =\t{coordinates["w"]}\n'
            f'Height =\t{coordinates["h"]}\n\n')
        return coords
    
    def locate_control_area_automatically(self):
        """"""
        self.parent.hide()
        # TODO switch off using screenshot
        # ctrl_area = self.locate_control_area_opencv("opencv_template/rust_example_screenshot.png")
        ctrl_area = self.locate_control_area_opencv()
        self.parent.show()

        msg = QMessageBox(self.parent)
        if ctrl_area == False:
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Couldn't find the painting control area automatically... Please try to manually capture it instead...")
            msg.exec_()
        else:
            btn = QMessageBox.question(self.parent, None,
                (self.format_coordinates(ctrl_area['tools'], "tools") +
                self.format_coordinates(ctrl_area['colour'], "colour") +
                "Would you like to update the painting controls area coordinates?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if btn == QMessageBox.Yes:
                self.parent.ui.log_TextEdit.append("Controls area position updated...")
                self.update_detected_locations(ctrl_area)
            self.update()


    def locate_control_area_opencv(self, screenshot=None):
        """ Automatically tries to find the painting control area with opencv.
        Returns:    returns ['x'], ['y'], ['w'], ['h'] for each area
                    areas are tools and colours
                    template['colour']['x'], template['colour']['y'], ....
                    returns False, if a control area was not found
        """
        # Take screenshot if no optional screenshot was passed for testing.
        if screenshot is None:
            screenshot = pyautogui.screenshot()
        else:
            screenshot = Image.open(screenshot)
        screen_w, screen_h = screenshot.size

        image_gray = cv2.cvtColor(numpy.array(screenshot), cv2.COLOR_BGR2GRAY)

        template = {
            "colour" : {
                "img" : cv2.imread('opencv_template/template_colour.png', cv2.IMREAD_GRAYSCALE),
                "x" : 0, "y" : 0, "w" : 1, "h" : 1, "confidence": 0.0
            },
            "tools" : {
                "img" : cv2.imread('opencv_template/template_tools.png', cv2.IMREAD_GRAYSCALE),
                "x" : 0, "y" : 0, "w" : 1, "h" : 1, "confidence": 0.0
            }
        }

        assert template['colour']['img'] is not None, "colour template file could not be read, check with os.path.exists()"
        assert template['tools']['img'] is not None, "tools template file could not be read, check with os.path.exists()"

        for t_name, t_item in template.items():
            
            t_image = t_item['img']
            w, h = t_image.shape[::-1]
            #method = eval(meth)
            method = cv2.TM_CCOEFF_NORMED
            # Apply template Matching
            res = cv2.matchTemplate(image_gray,t_image,method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            # confidence on accuracy, using only normalized methods so 1.0 is 100%
            confidence = max_val
            
            # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum value and update confidence
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = min_loc
                confidence = 1-min_val
            else:
                top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)

            t_item['x'] = top_left[0]
            t_item['y'] = top_left[1]
            t_item['w'] = w
            t_item['h'] = h
            t_item['confidence'] = confidence

            # get rid of img, no longer needed
            t_item.pop('img')
            
            # minimum accuracy threshold all areas must meet
            if confidence < 0.8:
                return False
        
        return template

        """"
        tmpl = cv2.imread("opencv_template/rust_palette_template.png", cv2.IMREAD_GRAYSCALE)
        tmpl_w, tmpl_h = tmpl.shape[::-1]

        x_coord, y_coord = 0, 0
        threshold = 0.8

        for loop in range(50):
            matches = cv2.matchTemplate(image_gray, tmpl, cv2.TM_CCOEFF_NORMED)
            loc = numpy.where(matches >= threshold)

            x_list, y_list = [], []
            for point in zip(*loc[::-1]):
                x_list.append(point[0])
                y_list.append(point[1])

            if x_list:
                x_coord = int(sum(x_list) / len(x_list))
                y_coord = int(sum(y_list) / len(y_list))
                return x_coord, y_coord, tmpl_w, tmpl_h

            tmpl_w, tmpl_h = int(tmpl.shape[1]*1.035), int(tmpl.shape[0]*1.035)
            tmpl = cv2.resize(tmpl, (int(tmpl_w), int(tmpl_h)))

            if tmpl_w > screen_w or tmpl_h > screen_h or loop == 49: return False"""
    
    
    """This calculates the coordinate offsets given a starting point and width/height plus a scaling factor.
    By default the offset will be calculated as a distance from the origin, If the scaling factor is negative, 
    the offset will be calculated from the endpoint towards the origin. """
    def calculate_offset(self, origin, endpoint_distance, scaling_factor):
        if scaling_factor > 0:
            return origin + (endpoint_distance/scaling_factor)
        else:
            return origin + endpoint_distance + (endpoint_distance/scaling_factor)

    """This updates the stored settings of locations when passed the dictionary of positions"""
    def update_detected_locations(self, positions):   
        for area_name, area_value in positions.items():
            for key_name, key_value in area_value.items():
                self.settings.setValue(f"ctrl_{area_name}_{key_name}", str(key_value))

    def calculate_ctrl_tools_positioning(self):
        """ This function calculates the positioning of the different controls in the painting control area.
        The brush size, type and opacity along with all the different colors.
        Updates:    self.ctrl_remove
                    self.ctrl_update
                    self.ctrl_size
                    self.ctrl_brush
                    self.ctrl_opacity
                    self.ctrl_color
        """
        # Reset
        self.ctrl_remove = (0,0)
        self.ctrl_update = (0,0)
        self.ctrl_size = (0,0)
        self.ctrl_spacing = (0,0)
        self.ctrl_opacity = (0,0)
        self.ctrl_brush = []
        self.ctrl_color = []
        self.ctrl_tool = []
        self.ctrl_tools_x = 0
        self.ctrl_tools_y = 0
        self.ctrl_tools_w = 0
        self.ctrl_tools_h = 0
        self.ctrl_colour_x = 0
        self.ctrl_colour_y = 0
        self.ctrl_colour_w = 0
        self.ctrl_colour_h = 0

        # TODO find all ctrl_x/y/w/h references and ensure they are updated with 
        # new split locations for tools and colours

        ctrl_x = int(self.settings.value("ctrl_x", default_settings["ctrl_x"]))
        ctrl_y = int(self.settings.value("ctrl_y", default_settings["ctrl_y"]))
        ctrl_w = int(self.settings.value("ctrl_w", default_settings["ctrl_w"]))
        ctrl_h = int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))

        ctrl_colour_x = int(self.settings.value("ctrl_colour_x", default_settings["ctrl_colour_x"]))
        ctrl_colour_y = int(self.settings.value("ctrl_colour_y", default_settings["ctrl_colour_y"]))
        ctrl_colour_w = int(self.settings.value("ctrl_colour_w", default_settings["ctrl_colour_w"]))
        ctrl_colour_h = int(self.settings.value("ctrl_colour_h", default_settings["ctrl_colour_h"]))
        ctrl_tools_x = int(self.settings.value("ctrl_tools_x", default_settings["ctrl_tools_x"]))
        ctrl_tools_y = int(self.settings.value("ctrl_tools_y", default_settings["ctrl_tools_y"]))
        ctrl_tools_w = int(self.settings.value("ctrl_tools_w", default_settings["ctrl_tools_w"]))
        ctrl_tools_h = int(self.settings.value("ctrl_tools_h", default_settings["ctrl_tools_h"]))

        # Calculate the distance between two items on a row of six items (paint, eraser, dropper tools)
        first_x_coord_of_three = self.calculate_offset(ctrl_tools_x, ctrl_tools_w, 2.75)
        second_x_coord_of_three = self.calculate_offset(ctrl_tools_x, ctrl_tools_w, 2.0)
        dist_btwn_x_coords_of_three = second_x_coord_of_three - first_x_coord_of_three

        # Calculate the distance between two items on a row of seven items (Brushes)
        first_x_coord_of_seven = self.calculate_offset(ctrl_tools_x, ctrl_tools_w, 9.34)
        second_x_coord_of_seven = self.calculate_offset(ctrl_tools_x, ctrl_tools_w, 4.13)
        dist_btwn_x_coords_of_seven = second_x_coord_of_seven - first_x_coord_of_seven

        # Calculate the distance between two items on a row of four items (Colors width)
        first_x_coord_of_four = self.calculate_offset(ctrl_colour_x, ctrl_colour_w, 6.57)
        second_x_coord_of_four = self.calculate_offset(ctrl_colour_x, ctrl_colour_w, 2.61)
        dist_btwn_x_coords_of_four = second_x_coord_of_four - first_x_coord_of_four

        # Calculate the distance between two items on a column of sixteen items (New Colors height)
        # TODO multi resolution testing
        first_y_coord_of_sixteen = self.calculate_offset(ctrl_colour_y, ctrl_colour_h, 6.66)
        second_y_coord_of_sixteen = self.calculate_offset(ctrl_colour_y, ctrl_colour_h, 4.92)
        dist_btwn_y_coords_of_sixteen = second_y_coord_of_sixteen - first_y_coord_of_sixteen

        # size text box
        self.ctrl_size = (self.calculate_offset(ctrl_tools_x, ctrl_tools_w, -7.88),self.calculate_offset(ctrl_tools_y, ctrl_tools_h, -3.39))

        # spacing text box
        self.ctrl_spacing = (self.calculate_offset(ctrl_tools_x, ctrl_tools_w, -7.88),self.calculate_offset(ctrl_tools_y, ctrl_tools_h, -5.38))

        # opacity text box
        self.ctrl_opacity = (self.calculate_offset(ctrl_tools_x, ctrl_tools_w, -7.88),self.calculate_offset(ctrl_tools_y, ctrl_tools_h, -12.9))

        # TODO Set the point location of the remove & update buttons
        self.ctrl_remove = ((ctrl_x + (ctrl_w/2.7692)), (ctrl_y + (ctrl_h/19.5714)))
        self.ctrl_update = ((ctrl_x + (ctrl_w/1.5652)), (ctrl_y + (ctrl_h/19.5714)))

        # TODO update to use text boxes for brush size and opacity
        for brush in range(7):
            self.ctrl_brush.append(( first_x_coord_of_seven +
                                     (brush * dist_btwn_x_coords_of_seven),
                                     (ctrl_tools_y + (ctrl_tools_h/1.74))))

        # paint brush, eraser, dropper tools
        for tool in range(3):
            self.ctrl_tool.append((   first_x_coord_of_three +
                                         (tool * dist_btwn_x_coords_of_three),
                                         (ctrl_tools_y + (ctrl_tools_h/4.45))))

        # colors
        for row in range(16):
            for column in range(4):
                self.ctrl_color.append(  (first_x_coord_of_four + (column * dist_btwn_x_coords_of_four),
                                         (first_y_coord_of_sixteen + (row * dist_btwn_y_coords_of_sixteen))))

        # Hidden colors location
        if self.settings.value("hidden_colors", default_settings["hidden_colors"], type="bool"):
            self.ctrl_color.append((ctrl_x + (ctrl_w/18.0000), ctrl_y + (ctrl_h/2.1518)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/4.2353), ctrl_y + (ctrl_h/2.1406)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/13.0909), ctrl_y + (ctrl_h/1.8430)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.6923), ctrl_y + (ctrl_h/1.9116)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.8228), ctrl_y + (ctrl_h/1.8853)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3714), ctrl_y + (ctrl_h/1.8348)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0746), ctrl_y + (ctrl_h/1.9116)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0667), ctrl_y + (ctrl_h/1.8430)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.8947), ctrl_y + (ctrl_h/1.6440)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3333), ctrl_y + (ctrl_h/1.6181)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.2857), ctrl_y + (ctrl_h/1.6440)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0827), ctrl_y + (ctrl_h/1.6506)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0588), ctrl_y + (ctrl_h/1.6310)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0588), ctrl_y + (ctrl_h/1.6118)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.8462), ctrl_y + (ctrl_h/1.4472)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.4545), ctrl_y + (ctrl_h/1.4784)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3846), ctrl_y + (ctrl_h/1.4838)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3333), ctrl_y + (ctrl_h/1.4784)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.1803), ctrl_y + (ctrl_h/1.4523)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.1077), ctrl_y + (ctrl_h/1.4421)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0746), ctrl_y + (ctrl_h/1.4731)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/18.0000), ctrl_y + (ctrl_h/1.4679)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.7895), ctrl_y + (ctrl_h/1.4371)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/16.0000), ctrl_y + (ctrl_h/1.3258)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.8919), ctrl_y + (ctrl_h/1.3258)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.4286), ctrl_y + (ctrl_h/1.3301)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/16.0000), ctrl_y + (ctrl_h/1.2088)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.6923), ctrl_y + (ctrl_h/1.2342)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/4.0000), ctrl_y + (ctrl_h/1.2018)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.2000), ctrl_y + (ctrl_h/1.1983)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.9200), ctrl_y + (ctrl_h/1.2342)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.4845), ctrl_y + (ctrl_h/1.1844)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3714), ctrl_y + (ctrl_h/1.1844)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0746), ctrl_y + (ctrl_h/1.2053)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/16.0000), ctrl_y + (ctrl_h/1.1048)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/4.2353), ctrl_y + (ctrl_h/1.1078)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3333), ctrl_y + (ctrl_h/1.1078)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.0667), ctrl_y + (ctrl_h/1.1048)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.3488), ctrl_y + (ctrl_h/1.0327)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/3.4286), ctrl_y + (ctrl_h/1.0512)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.4694), ctrl_y + (ctrl_h/1.0327)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/2.7692), ctrl_y + (ctrl_h/1.1982)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/2.0571), ctrl_y + (ctrl_h/1.2160)))
            self.ctrl_color.append((ctrl_x + (ctrl_w/1.3211), ctrl_y + (ctrl_h/1.4784)))


    def calculate_statistics(self):
        """ Calculate what colors, how many pixels and lines for the painting
        Updates:    self.img_colors,
                    self.tot_pixels,
                    self.pixels,
                    self.lines
        """
        minimum_line_width = int(self.settings.value("minimum_line_width", default_settings["minimum_line_width"]))
        self.update_skip_colors()
        pixel_arr = self.quantized_img.load()

        self.img_colors = []
        self.tot_pixels = 0
        self.pixels = 0
        self.lines = 0

        for color in self.quantized_img.getcolors():
            if color[1] not in self.skip_colors:
                self.tot_pixels += color[0]
                self.img_colors.append(color[1])

        for color in self.img_colors:
            is_first_point_of_row = True
            is_last_point_of_row = False
            is_previous_color = False
            is_line = False
            pixels_in_line = 0

            for y in range(self.canvas_h):
                is_first_point_of_row = True
                is_last_point_of_row = False
                is_previous_color = False
                is_line = False
                pixels_in_line = 0

                for x in range(self.canvas_w):
                    if x == (self.canvas_w - 1): is_last_point_of_row = True

                    if is_first_point_of_row:
                        is_first_point_of_row = False
                        if pixel_arr[x, y] == color:
                            is_previous_color = True
                            pixels_in_line = 1
                        continue

                    if pixel_arr[x, y] == color:
                        if is_previous_color:
                            if is_last_point_of_row:
                                if pixels_in_line >= minimum_line_width: self.lines += 1
                                else:
                                    self.pixels += (pixels_in_line + 1)
                            else: is_line = True; pixels_in_line += 1
                        else:
                            if is_last_point_of_row: self.pixels += 1
                            else:
                                is_previous_color = True
                                pixels_in_line = 1
                    else:
                        if is_previous_color:
                            if is_line:
                                is_line = False

                                if is_last_point_of_row:
                                    if pixels_in_line >= minimum_line_width: self.lines += 1
                                    else:
                                        self.pixels += (pixels_in_line + 1)
                                    continue

                                if pixels_in_line >= minimum_line_width: self.lines += 1
                                else: self.pixels += (pixels_in_line + 1)
                                pixels_in_line = 0
                            else: self.pixels += 1
                            is_previous_color = False
                        else:
                            is_line = False
                            pixels_in_line = 0


    def calculate_estimated_time(self):
        """ Calculate estimated time for the painting process.
        Updates:    Estimated time for clicking and lines
                    Estimated time for only clicking
        """
        one_click_time = self.click_delay + 0.001
        one_click_time = one_click_time * 2 if self.use_double_click else one_click_time
        one_line_time = (self.line_delay * 5) + 0.0035
        set_paint_controls_time =   (len(self.img_colors) * ((2 * self.click_delay) + (2 * self.ctrl_area_delay))) + ((2 * self.click_delay) + (2 * self.ctrl_area_delay))
        est_time_lines = int((self.pixels * one_click_time) + (self.lines * one_line_time) + set_paint_controls_time)
        est_time_click = int((self.tot_pixels * one_click_time) + set_paint_controls_time)

        if not bool(self.settings.value("draw_lines", default_settings["draw_lines"])):
            self.prefer_lines = False
            self.estimated_time = est_time_click
        elif est_time_lines < est_time_click:
            self.prefer_lines = True
            self.estimated_time = est_time_lines
        else:
            self.prefer_lines = False
            self.estimated_time = est_time_click

    # TODO define click that passes on to pyautogui white handling tuple/x,y and checks for double click

    def click_pixel(self, x = 0, y = 0):
        """ Click the pixel """
        if isinstance(x, tuple):
            pyautogui.click(x[0], x[1])
            if self.use_double_click:
                pyautogui.click(x[0], x[1])
        else:
            pyautogui.click(x, y)
            if self.use_double_click:
                pyautogui.click(x, y)

    def write_value(self, value: str, x=0, y=0):
        if isinstance(x, tuple):
            x, y = x[0], x[1]
        pyautogui.click(x, y)
        pyautogui.write(value)
        pyautogui.press('return')
        time.sleep(self.ctrl_area_delay)



    def draw_line(self, point_A, point_B):
        """ Draws a line between point_A and point_B. """
        pyautogui.PAUSE = self.line_delay
        pyautogui.mouseDown(button="left", x=point_A[0], y=point_A[1])
        pyautogui.keyDown("shift")
        pyautogui.moveTo(point_B[0], point_B[1])
        pyautogui.keyUp("shift")
        pyautogui.mouseUp(button="left")
        pyautogui.PAUSE = self.click_delay


    def key_event(self, key):
        """ Key-press thread during painting. """
        try: key_str = str(key.char)
        except: key_str = str(key.name)

        if key_str == self.pause_key:       # Pause
            self.paused = not self.paused
        elif key_str == self.skip_key:      # Skip color
            self.paused = False
            self.skip_current_color = True
        elif key_str == self.abort_key:     # Abort
            self.paused = False
            self.abort = True


    def shutdown(self, listener, start_time, state = 0):
        """ Shutdown the painting process """
        self.parent.ui.load_image_PushButton.setEnabled(True)
        self.parent.ui.identify_ctrl_PushButton.setEnabled(True)
        self.parent.ui.paint_image_PushButton.setEnabled(True)
        self.parent.ui.settings_PushButton.setEnabled(True)

        listener.stop()
        elapsed_time = int(time.time() - start_time)
        self.parent.ui.log_TextEdit.append("Elapsed time: " + str(time.strftime("%H:%M:%S", time.gmtime(elapsed_time))))
        QApplication.processEvents()
        self.hotkey_label.hide()

        if state == 0: self.parent.ui.progress_ProgressBar.setValue(100)

        if bool(self.settings.value("window_topmost", default_settings["window_topmost"])):
            self.parent.setWindowFlags(self.parent.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.parent.show()
        self.parent.activateWindow()

    # TODO update to not use translation logic between old index based method and new numerical interface
    def choose_old_size(self, size: int):
        """
        translation logic to go between old size based index and new numerical/slider version.

        :param size: int
        """
        assert size in range(6), f"size index must be int 0-5, got: {size}"
        
        # TODO testing to get numbers similar to old sizes
        # numerical equivalent to old size indicies
        size_equivalent = (1,3,5,9,17,32)
        self.write_value(str(size_equivalent[size]), self.ctrl_size)

        
    # TODO update to not use translation logic between old index based method and new numerical interface
    def choose_old_opacity(self, opacity: int):
        """
        translation logic to go between old size based index and new numerical/slider version.

        :param size: int
        """
        assert opacity in range(6), f"opacity index must be int 0-5, got: {opacity}"
        
        # TODO testing to get numbers similar to old values
        # numerical equivalent to old size indicies
        opacity_equivalent = (0.10, 0.20, 0.40, 0.60, 0.80, 1.0)
        self.write_value(str(opacity_equivalent[opacity]), self.ctrl_opacity)

    def choose_painting_controls(self, size, brush, color):
        """ Choose the paint controls
        Numbers for size brush and color are the index for ctrl_(size|brush|color) """
        if self.current_ctrl_size != size:
            self.current_ctrl_size = size
            self.choose_old_size(size)
            
        if self.current_ctrl_brush != brush:
            self.current_ctrl_brush = brush
            self.click_pixel(self.ctrl_brush[brush])
            time.sleep(self.ctrl_area_delay)


        # TODO switch to new version of opacity
        if self.use_hidden_colors:
            if   color >= 0  and color < 64: self.choose_old_opacity(5)
            elif color >= 64 and color < 128: self.choose_old_opacity(4)
            elif color >= 128 and color < 192: self.choose_old_opacity(3)
            elif color >= 192 and color < 256: self.choose_old_opacity(2)
        else:
            if   color >= 0  and color < 64: self.choose_old_opacity(5)
            elif color >= 20 and color < 40: self.choose_old_opacity(4)
            elif color >= 40 and color < 60: self.choose_old_opacity(3)
            elif color >= 60 and color < 80: self.choose_old_opacity(2)
        time.sleep(self.ctrl_area_delay)

        if self.current_ctrl_color != color:
            if self.use_hidden_colors:
                self.click_pixel(self.ctrl_color[color%64])
            else:
                self.click_pixel(self.ctrl_color[color%64])
            time.sleep(self.ctrl_area_delay)


    def update_skip_colors(self):
        """ Updates the skip colors list """
        self.skip_colors = []
        temp_skip_colors = self.settings.value("skip_colors", default_settings["skip_colors"], "QStringList")
        if len(temp_skip_colors) != 0:
            for color in temp_skip_colors:
                if hex_to_rgb(color) in self.updated_palette:
                    self.skip_colors.append(self.updated_palette.index(hex_to_rgb(color)))

        skip_background_color = bool(self.settings.value("skip_background_color", default_settings["skip_background_color"]))
        if skip_background_color:
            bg_color_rgb = hex_to_rgb(self.settings.value("background_color", default_settings["background_color"]))
            use_hidden_colors = self.settings.value("hidden_colors", default_settings["hidden_colors"], type="bool")
            use_opacities = bool(self.settings.value("brush_opacities", default_settings["brush_opacities"]))

            bg_colors = []

            if bg_color_rgb in self.updated_palette:
                if use_hidden_colors:
                    if use_opacities:
                        bg_index = self.updated_palette.index(bg_color_rgb) % 64
                        bg_colors = [bg_index, bg_index+(64*1), bg_index+(64*2), bg_index+(64*3)]
                    else:
                        bg_colors = [self.updated_palette.index(bg_color_rgb) % 64]
                else:
                    # TODO fix 20/64
                    if use_opacities:
                        bg_index = self.updated_palette.index(bg_color_rgb) % 20
                        bg_colors = [bg_index, bg_index+(20*1), bg_index+(20*2), bg_index+(20*3)]
                    else:
                        bg_colors = [self.updated_palette.index(bg_color_rgb) % 64]

            self.skip_colors = self.skip_colors + bg_colors

        self.skip_colors = list(map(int, self.skip_colors))


    def start_painting(self):
        """ Start the painting """
        # Update global variables
        self.use_hidden_colors =    self.settings.value("hidden_colors", default_settings["hidden_colors"], type="bool")
        self.pause_key =            str(self.settings.value("pause_key", default_settings["pause_key"])).lower()
        self.skip_key =             str(self.settings.value("skip_key", default_settings["skip_key"])).lower()
        self.abort_key =            str(self.settings.value("abort_key", default_settings["abort_key"])).lower()

        # Update local variables
        minimum_line_width =    int(self.settings.value("minimum_line_width", default_settings["minimum_line_width"]))
        
        # TODO determing why ctrl_ values were not used here
        ctrl_x =                int(self.settings.value("ctrl_x", default_settings["ctrl_x"]))
        ctrl_y =                int(self.settings.value("ctrl_h", default_settings["ctrl_y"]))
        ctrl_w =                int(self.settings.value("ctrl_w", default_settings["ctrl_w"]))
        ctrl_h =                int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))

        brush_type =            int(self.settings.value("brush_type", default_settings["brush_type"]))
        use_brush_opacities =   bool(self.settings.value("brush_opacities", default_settings["brush_opacities"]))
        hide_preview_paint =    bool(self.settings.value("hide_preview_paint", default_settings["hide_preview_paint"]))
        update_canvas_end =     bool(self.settings.value("update_canvas_end", default_settings["update_canvas_end"]))
        window_topmost =        bool(self.settings.value("window_topmost", default_settings["window_topmost"]))
        update_canvas =         bool(self.settings.value("update_canvas", default_settings["update_canvas"]))
        show_info =             bool(self.settings.value("show_information", default_settings["show_information"]))


        self.update()                               # Update click, line, ctrl_area delay
        self.update_skip_colors()                   # Update self.skip_colors variable
        if not self.locate_canvas_area(): return    # Locate the canvas
        if not self.convert_img(): return           # Quantize the image

        # Clear the log
        self.parent.ui.progress_ProgressBar.setValue(0)
        self.parent.ui.log_TextEdit.clear()
        self.parent.ui.log_TextEdit.append("Calculating statistics...")
        QApplication.processEvents()

        self.calculate_ctrl_tools_positioning()     # Calculate the control tools positioning
        self.calculate_statistics()                 # Calculate statistics (colors, total pixels, lines)
        self.calculate_estimated_time()             # Calculate the estimated time


        # Opens a information dialog
        question = "Dimensions: \t\t\t\t" + str(self.canvas_w) + " x " + str(self.canvas_h)
        question += "\nNumber of colors:\t\t\t" + str(len(self.img_colors))
        question += "\nTotal Number of pixels to paint: \t" + str(self.tot_pixels)
        question += "\nNumber of pixels to paint:\t\t" + str(self.pixels)
        question += "\nNumber of lines:\t\t\t" + str(self.lines)
        question += "\nEst. painting time:\t\t\t" + str(time.strftime("%H:%M:%S", time.gmtime(self.estimated_time)))
        question += "\n\nWould you like to start the painting?"
        if show_info:
            btn = QMessageBox.question(self.parent, None, question, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if btn == QMessageBox.No:
                return

        # Disable mainwindow buttons while painting
        self.parent.ui.load_image_PushButton.setEnabled(False)
        self.parent.ui.identify_ctrl_PushButton.setEnabled(False)
        self.parent.ui.paint_image_PushButton.setEnabled(False)
        self.parent.ui.settings_PushButton.setEnabled(False)

        # If window_topmost setting is set, activate window always on top functionality
        if window_topmost:
            self.parent.setWindowFlags(self.parent.windowFlags() | Qt.WindowStaysOnTopHint)
            self.parent.show()

        # If hide_preview_paint and self.parent.is_expanded, close image preview
        if hide_preview_paint and self.parent.is_expanded:
            self.parent.preview_clicked()

        # Add label info about pause, skip and abort keys
        self.hotkey_label = QLabel(self.parent)
        self.hotkey_label.setGeometry(QRect(10, 425, 221, 21))
        self.hotkey_label.setText(  self.pause_key + " = Pause        " +
                                    self.skip_key + " = Skip        " +
                                    self.abort_key + " = Abort")
        self.hotkey_label.show()

        # Paint the background with the default background color
        self.choose_old_size(0) # To set focus on the rust window
        time.sleep(.5)
        self.choose_old_size(0)
        if bool(self.settings.value("paint_background", default_settings["paint_background"])) and self.background_color != None:
            self.parent.ui.log_TextEdit.append("Painting background for you...")
            self.choose_painting_controls(5, 3, self.background_color)
            x_start = self.canvas_x + 10
            x_end = self.canvas_x + self.canvas_w - 10
            loops = int((self.canvas_h - 10) / 10)
            for i in range(1, loops+1):
                self.draw_line((x_start, self.canvas_y + (10 * i)), (x_end, self.canvas_y + (10 * i)))


        # Print out the start time, estimated time and estimated finish time
        self.parent.ui.log_TextEdit.append("Start time:\t" + str((datetime.datetime.now()).time().strftime("%H:%M:%S")))
        self.parent.ui.log_TextEdit.append("Est. time:\t" + str(time.strftime("%H:%M:%S", time.gmtime(self.estimated_time))))
        self.parent.ui.log_TextEdit.append( "Est. finished:\t" + str((datetime.datetime.now() + datetime.timedelta(seconds=self.estimated_time)).time().strftime("%H:%M:%S")))
        QApplication.processEvents()


        self.paused = False
        self.abort = False
        pixel_counter = 0
        progress_percent = 0
        previous_progress_percent = None

        start_time = time.time()
        pixel_arr = self.quantized_img.load()

        # Start keyboard listener
        listener = keyboard.Listener(on_press=self.key_event)
        listener.start()

        for counter, color in enumerate(self.img_colors):
            self.skip_current_color = False
            # Print current color to the log
            color_hex = rgb_to_hex(self.updated_palette[color])
            self.parent.ui.log_TextEdit.append(
                "(" + str((counter+1)) + "/" + str((len(self.img_colors))) + ") Current color: " +
                "<span style=\" font-size:8pt; font-weight:600; color:" + str(color_hex) + ";\" >█" +
                str(color_hex) + "█</span>")

            QApplication.processEvents()

            # Choose painting controls
            self.choose_painting_controls(0, brush_type, color)

            for y in range(self.canvas_h):
                if self.skip_current_color: break

                # Calculate percentage for progress bar
                progress_percent = int(pixel_counter/int(self.tot_pixels/100))
                if progress_percent != previous_progress_percent:
                    previous_progress_percent = progress_percent
                    self.parent.ui.progress_ProgressBar.setValue(progress_percent)

                # Reset variables
                is_first_point_of_row = True
                is_last_point_of_row = False
                is_previous_color = False
                is_line = False
                pixels_in_line = 0

                for x in range(self.canvas_w):

                    while self.paused: QApplication.processEvents()
                    if self.skip_current_color: break
                    if self.abort:
                        self.parent.ui.log_TextEdit.append("Aborted...")
                        return self.shutdown(listener, start_time, 1)

                    if x == (self.canvas_w - 1):
                        is_last_point_of_row = True

                    if is_first_point_of_row and self.prefer_lines:
                        is_first_point_of_row = False
                        if pixel_arr[x, y] == color:
                            first_point = (self.canvas_x + x, self.canvas_y + y)
                            is_previous_color = True
                            pixels_in_line = 1
                        continue

                    if pixel_arr[x, y] == color:
                        if not self.prefer_lines:
                            self.click_pixel(self.canvas_x + x, self.canvas_y + y)
                            pixel_counter += 1
                            continue
                        if is_previous_color:
                            if is_last_point_of_row:
                                if pixels_in_line >= minimum_line_width:
                                    self.draw_line(first_point, (self.canvas_x + x, self.canvas_y + y))
                                    pixel_counter += pixels_in_line
                                else:
                                    for index in range(pixels_in_line):
                                        self.click_pixel(first_point[0] + index, self.canvas_y + y)
                                    self.click_pixel(self.canvas_x + x, self.canvas_y + y)
                                    pixel_counter += pixels_in_line + 1
                            else:
                                is_line = True
                                pixels_in_line += 1
                        else:
                            if is_last_point_of_row:
                                self.click_pixel(self.canvas_x + x, self.canvas_y + y)
                                pixel_counter += 1
                            else:
                                first_point = (self.canvas_x + x, self.canvas_y + y)
                                is_previous_color = True
                                pixels_in_line = 1
                    else:
                        if not self.prefer_lines: continue
                        if is_previous_color:
                            if is_line:
                                is_line = False

                                if is_last_point_of_row:
                                    if pixels_in_line >= minimum_line_width:
                                        self.draw_line(first_point, (self.canvas_x + (x-1), self.canvas_y + y))
                                        pixel_counter += pixels_in_line
                                    else:
                                        for index in range(pixels_in_line):
                                            self.click_pixel(first_point[0] + index, self.canvas_y + y)
                                        pixel_counter += pixels_in_line
                                    continue

                                if pixels_in_line >= minimum_line_width:
                                    self.draw_line(first_point, (self.canvas_x + (x-1), self.canvas_y + y))
                                    pixel_counter += pixels_in_line
                                else:
                                    for index in range(pixels_in_line):
                                        self.click_pixel(first_point[0] + index, self.canvas_y + y)
                                    pixel_counter += pixels_in_line
                                pixels_in_line = 0

                            else:
                                self.click_pixel(self.canvas_x + (x-1), self.canvas_y + y)
                                pixel_counter += 1
                            is_previous_color = False
                        else:
                            is_line = False
                            pixels_in_line = 0

            if update_canvas:
                self.click_pixel(self.ctrl_update)

        if update_canvas_end:
            self.click_pixel(self.ctrl_update)

        return self.shutdown(listener, start_time)
