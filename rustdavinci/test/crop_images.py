import cv2 
import glob
import re

# assign directory
directory = "rustdavinci/opencv_template/"

#filename pattern
regex = r'(?P<width>[0-9]{2,4})x(?P<height>[0-9]{2,4}).png'
# iterate over files in
# that directory
for filename in glob.iglob(f'{directory}/*.png'):
    match = re.search(regex, filename)
    if match:
        #
        w = int(match.group('width'))
        h = int(match.group('height'))
        img = cv2.imread(filename) 
        print(type(img)) 
        
        # Shape of the image for dimensions
        rows, columns, _ = img.shape
        # make sure image is size we expected
        assert columns == w + 2 and rows == h + 32, f"Unexpected image size, expected {w+2} {h+32}, got: {columns}, {rows}"

        # [rows, columns] 
        # crop first 31 rows, and last row, and outer two columns
        crop = img[31:-1, 1:-1]
        cv2.imwrite(f"rustdavinci/opencv_template/{w}x{h}_trim.png", crop)        

