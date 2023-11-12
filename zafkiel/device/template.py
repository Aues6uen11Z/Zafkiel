import os
from functools import cached_property
from pathlib import Path

from airtest.core.cv import Template
from airtest.core.helper import G
from airtest.utils.transform import TargetPos
from numpy import ndarray

from zafkiel.config import Config
from zafkiel.ocr.keyword import Keyword


class ImageTemplate(Template):
    def __init__(
            self,
            filename: str,
            record_pos: tuple = None,
            keyword: Keyword = None,
            threshold: float = None,
            target_pos: int = TargetPos.MID,
            resolution: tuple = (1280, 720),
            rgb: bool = False,
            scale_max: int = 800,
            scale_step: float = 0.005,
            template_path: str = 'templates'
    ):

        super().__init__(filename, threshold, target_pos, record_pos, resolution, rgb, scale_max, scale_step)

        self.template_path = template_path  # under root path
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

    def _has_border(self) -> bool:
        """
        If game running in a bordered process, coordinates need to be corrected.

        Returns:
            Whether the game running in a bordered process.
        """
        actual_ratio = G.DEVICE.get_current_resolution()[0] / G.DEVICE.get_current_resolution()[1]
        template_ratio = self.resolution[0] / self.resolution[1]
        return actual_ratio != template_ratio

    def ratio(self, screen_height: float = None) -> float:
        """
        Calculate the ratio of the current screen to the template image.
        """
        if screen_height is None:
            if self._has_border():
                border = Config.BORDER[0] + Config.BORDER[2]
            else:
                border = 0
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

        if self._has_border():
            border = Config.BORDER
        else:
            border = (0, 0, 0)

        screen_width = screen_resolution[0] - border[1] * 2
        screen_height = screen_resolution[1] - border[0] - border[2]

        ratio = self.ratio(screen_height)
        x1 = screen_width / 2 + self.record_pos[0] * screen_width - self.width / 2 * ratio + border[1]
        y1 = screen_height / 2 + self.record_pos[1] * screen_width - self.height / 2 * ratio + border[0]
        x2 = screen_width / 2 + self.record_pos[0] * screen_width + self.width / 2 * ratio + border[1]
        y2 = screen_height / 2 + self.record_pos[1] * screen_width + self.height / 2 * ratio + border[0]
        return x1, y1, x2, y2
