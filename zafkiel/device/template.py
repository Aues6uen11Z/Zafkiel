import os
import types
from functools import cached_property
from pathlib import Path
from typing import Optional, Tuple

import cv2
from airtest.core.cv import Template, MATCHING_METHODS
from airtest.core.error import InvalidMatchingMethodError
from airtest.core.helper import G, logwrap
from airtest.utils.transform import TargetPos
from numpy import ndarray

from zafkiel.config import Config
from zafkiel.ocr.keyword import Keyword


class ImageTemplate(Template):
    def __init__(
            self,
            filename: str,
            record_pos: Optional[Tuple[float, float]] = None,
            keyword: Optional[Keyword] = None,
            resolution: Tuple[int, int] = (1280, 720),
            rgb: bool = False,
            local_search: bool = True,
            ocr_mode: int = 0,
            template_path: str = 'templates',
            threshold: Optional[float] = None,
            target_pos: int = TargetPos.MID,
            scale_max: int = 800,
            scale_step: float = 0.005
    ):
        """
        Args:
            local_search: True if you only want to search for template image at the corresponding positions on the screen,
                otherwise it will search the entire screen.
            ocr_mode: Ocr match rules, one of 0/1/2, which means `OCR_EQUAL`, `OCR_CONTAINS`, `OCR_SIMILAR`.
        """

        super().__init__(filename, threshold, target_pos, record_pos, resolution, rgb, scale_max, scale_step)

        self.template_path = template_path  # under root path
        self.local_search = local_search
        self.ocr_mode = ocr_mode
        self.keyword = keyword
        if self.keyword is not None and self.keyword.name == '':
            """
            Please note that due to the __post_init__ method of the Keyword class running before this 'name' assignment, 
            its 'instances' dictionary will get a dictionary item with an empty string key.
            This means that each instance of the Keyword class that omits the 'name' parameter will be constantly 
            overwritten. If you want to use Keyword().instances for special purposes, you must initialize 'name'.
            """
            self.keyword.name = self.name

    @cached_property
    def filepath(self) -> str:
        if self._filepath:
            return self._filepath
        for dir_name in G.BASEDIR:
            filepath = os.path.join(dir_name, self.template_path, self.filename)
            if os.path.isfile(filepath):
                self._filepath = filepath
                return self._filepath
        return self.filename

    @cached_property
    def name(self) -> str:
        return Path(self.filename).stem

    @cached_property
    def image(self) -> ndarray:
        return self._imread()

    @cached_property
    def height(self) -> int:
        return self.image.shape[0]

    @cached_property
    def width(self) -> int:
        return self.image.shape[1]

    @cached_property
    def border(self) -> tuple[int, int, int]:
        """
        If running in a bordered window, coordinates need to be corrected.

        Returns:
            Top, left and bottom boundary pixel values on the current screen.
        """
        real_resolution = G.DEVICE.real_resolution()
        screenshot_resolution = G.DEVICE.get_current_resolution()

        border_other = (screenshot_resolution[0] - real_resolution[0]) / 2
        border_top = screenshot_resolution[1] - real_resolution[1] - border_other

        return border_top, border_other, border_other

    def ratio(self, screen_height: float = None) -> float:
        """
        Calculate the ratio of the current screen to the template image.
        """
        if screen_height is None:
            border = self.border[0] + self.border[2]
            screen_height = G.DEVICE.get_current_resolution()[1] - border

        return screen_height / self.resolution[1]

    @cached_property
    def area(self) -> tuple:
        """
        Calculate the area of the template image on the current screen.

        Returns:
            Upper left and lower right corner coordinate.
        """
        screen_resolution = G.DEVICE.get_current_resolution()

        screen_width = screen_resolution[0] - self.border[1] * 2
        screen_height = screen_resolution[1] - self.border[0] - self.border[2]

        ratio = self.ratio(screen_height)
        x1 = screen_width / 2 + self.record_pos[0] * screen_width - self.width / 2 * ratio + self.border[1]
        y1 = screen_height / 2 + self.record_pos[1] * screen_width - self.height / 2 * ratio + self.border[0]
        x2 = screen_width / 2 + self.record_pos[0] * screen_width + self.width / 2 * ratio + self.border[1]
        y2 = screen_height / 2 + self.record_pos[1] * screen_width + self.height / 2 * ratio + self.border[0]
        return x1, y1, x2, y2

    def match_in(self, screen, local_search=True):
        revise_coord = (0, 0)
        if local_search:
            # search area is a little larger than the template image area
            x1, y1, x2, y2 = map(int, self.area)
            width_increase = (x2 - x1) * 0.2
            height_increase = (y2 - y1) * 0.2
            x1 = int(max(x1 - width_increase, 0))
            y1 = int(max(y1 - height_increase, 0))
            x2 = int(min(x2 + width_increase, screen.shape[1]))
            y2 = int(min(y2 + height_increase, screen.shape[0]))

            revise_coord = x1, y1
            screen = screen[y1:y2, x1:x2]

        screen_resolution = G.DEVICE.get_current_resolution()
        screen_width = screen_resolution[0] - self.border[1] * 2
        screen_height = screen_resolution[1] - self.border[0] - self.border[2]

        match_result = self._cv_match(screen, (screen_width, screen_height))
        G.LOGGING.debug("match result: %s", match_result)
        if not match_result:
            return None
        focus_pos = TargetPos().getXY(match_result, self.target_pos)

        if local_search:
            focus_pos = focus_pos[0] + revise_coord[0], focus_pos[1] + revise_coord[1]

        return focus_pos

    @logwrap
    def _cv_match(self, screen, screen_resolution):
        ori_image = self.image
        image = self._resize_image(ori_image, screen_resolution, Config.ST.RESIZE_METHOD)
        ret = None
        for method in Config.ST.CVSTRATEGY:
            # get function definition and execute:
            func = MATCHING_METHODS.get(method, None)
            if func is None:
                raise InvalidMatchingMethodError(
                    "Undefined method in CVSTRATEGY: '%s', try 'kaze'/'brisk'/'akaze'/'orb'/'surf'/'sift'/'brief' instead." % method)
            else:
                if method in ["mstpl", "gmstpl"]:
                    ret = self._try_match(func, ori_image, screen, threshold=self.threshold, rgb=self.rgb,
                                          record_pos=self.record_pos,
                                          resolution=self.resolution, scale_max=self.scale_max,
                                          scale_step=self.scale_step)
                else:
                    ret = self._try_match(func, image, screen, threshold=self.threshold, rgb=self.rgb)
            if ret:
                break
        return ret

    def _resize_image(self, image, screen_resolution, resize_method):
        """
        Scale the template image to the current screen resolution.
        """
        if not self.resolution:
            return image

        if tuple(self.resolution) == tuple(screen_resolution) or resize_method is None:
            return image
        if isinstance(resize_method, types.MethodType):
            resize_method = resize_method.__func__

        # default to using cocos_min_strategy:
        h, w = image.shape[:2]
        w_re, h_re = resize_method(w, h, self.resolution, screen_resolution)
        w_re, h_re = max(1, w_re), max(1, h_re)
        G.LOGGING.debug("resize: (%s, %s)->(%s, %s), resolution: %s=>%s" % (
                        w, h, w_re, h_re, self.resolution, screen_resolution))

        image = cv2.resize(image, (w_re, h_re))
        return image
