import cv2
import numpy as np
from PIL import Image


def random_rectangle_point(center, h, w, n=3):
    """
    From https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/base/utils/utils.py
    Choose a random point in an area.

    Args:
        center: coordinate of the area center
        h: height of the area
        w: width of the area
        n: The amount of numbers in simulation. Default to 3.

    Returns:
        tuple(int): (x, y)
    """
    CONST_ERROR = 10
    upper_left_x = center[0] - max(0, int(w / 2 - CONST_ERROR))
    upper_left_y = center[1] - max(0, int(h / 2 - CONST_ERROR))
    bottom_right_x = center[0] + max(0, int(w / 2 - CONST_ERROR))
    bottom_right_y = center[1] + max(0, int(h / 2 - CONST_ERROR))
    x = random_normal_distribution_int(upper_left_x, bottom_right_x, n)
    y = random_normal_distribution_int(upper_left_y, bottom_right_y, n)
    return x, y


def random_normal_distribution_int(a, b, n=3):
    """
    From https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/base/utils/utils.py
    Generate a normal distribution int within the interval. Use the average value of several random numbers to
    simulate normal distribution.

    Args:
        a (int): The minimum of the interval.
        b (int): The maximum of the interval.
        n (int): The amount of numbers in simulation. Default to 3.

    Returns:
        int
    """
    if a < b:
        output = np.mean(np.random.randint(a, b, size=n))
        return int(output.round())
    else:
        return b


def crop(image, area):
    """
    From https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/base/utils/utils.py

    Crop image like pillow, when using opencv / numpy.
    Provides a black background if cropping outside of image.

    Args:
        image: Image to be cropped, usually a screenshot.
        area: Upper left and lower right corner coordinate of the area to be cropped.

    Returns:
        cropped image
    """
    x1, y1, x2, y2 = map(int, map(round, area))
    h, w = image.shape[:2]
    border = np.maximum((0 - y1, y2 - h, 0 - x1, x2 - w), 0)
    x1, y1, x2, y2 = np.maximum((x1, y1, x2, y2), 0)
    image = image[y1:y2, x1:x2]
    if sum(border) > 0:
        image = cv2.copyMakeBorder(image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
    return image


def is_color_similar(template, screen, threshold=0.9):
    """
    Check if a template image and a screenshot have similar colors.

    Args:
        template: The template image as a numpy array.
        screen: The screenshot as a numpy array.
        threshold: The threshold for color similarity, a float between 0 and 1. Default is 0.9.

    Returns:
        True if the template image and the screenshot have similar colors, False otherwise.
    """
    # Convert the template image and the screenshot to the HSV color space
    template_hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    screen_hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

    # Calculate the color histograms of the template image and the screenshot
    template_hist = cv2.calcHist([template_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
    screen_hist = cv2.calcHist([screen_hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])

    # Normalize the histograms
    cv2.normalize(template_hist, template_hist, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(screen_hist, screen_hist, 0, 1, cv2.NORM_MINMAX)

    # Calculate the histogram similarity
    similarity = cv2.compareHist(template_hist, screen_hist, cv2.HISTCMP_CORREL)

    # Check if the histogram similarity is above the threshold
    return similarity >= threshold


def color_exists(image, color):
    """
    Check if a specific color exists in the image.

    Args:
        image: cv2 image.
        color: RGB color tuple.

    Returns:
        True if the color exists in the image, False otherwise.
    """

    # covert to PIL image
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image)

    pixels = image.getdata()
    for pixel in pixels:
        if pixel == color:
            return True

    return False
