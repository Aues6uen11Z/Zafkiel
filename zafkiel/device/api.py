import os
import time
from typing import Type, Callable

from airtest.core.api import snapshot, connect_device, init_device, set_current, shell, start_app, \
    clear_app, install, uninstall, wake, home, double_click, pinch, keyevent, text, sleep, find_all, \
    get_clipboard, set_clipboard, device
from airtest.core.cv import try_log_screen
from airtest.core.error import TargetNotFoundError
from airtest.core.helper import G, logwrap, delay_after_operation, set_logdir
from airtest.core.settings import Settings as ST
from airtest.utils.compat import script_log_dir
from pywinauto.findwindows import ElementNotFoundError

from zafkiel.device.cv import loop_find
from zafkiel.device.template import ImageTemplate as Template
from zafkiel.logger import logger
from zafkiel.exception import NotRunningError, ScriptError
from zafkiel.ocr.ocr import Ocr
from zafkiel.timer import Timer
from zafkiel.utils import random_rectangle_point


class API:
    """
    Device Setup APIs
    """

    @staticmethod
    def init_device(platform="Android", uuid=None, **kwargs):
        return init_device(platform, uuid, **kwargs)

    @staticmethod
    def connect_device(uri):
        return connect_device(uri)

    @staticmethod
    def device():
        return device()

    @staticmethod
    def set_current(idx):
        set_current(idx)

    @staticmethod
    def auto_setup(
            basedir: str = None,
            devices: list = None,
            firing_time: int = 30,
            logdir: bool = None,
            project_root: str = None,
            compress: int = None
    ):
        """
        Auto setup running env and try to connect device if no device is connected.

        Args:
            basedir: basedir of script, __file__ is also acceptable.
            devices: connect_device uri in list.
            firing_time: Game starts taking time, this value should be set larger in old machine.
            logdir: log dir for script report, default is None for no log, set to ``True`` for ``<basedir>/log``.
            project_root: Project root dir for `using` api.
            compress: The compression rate of the screenshot image, integer in range [1, 99], default is 10

        Examples:
            auto_setup(__file__)
            auto_setup(__file__, devices=["Android://127.0.0.1:5037/SJE5T17B17"],
            ...        logdir=True, project_root=r"D:\\test\\logs", compress=90)
        """
        if basedir:
            if os.path.isfile(basedir):
                basedir = os.path.dirname(basedir)
            if basedir not in G.BASEDIR:
                G.BASEDIR.append(basedir)
        if devices:
            startup_time = Timer(firing_time).start()
            for dev in devices:
                while not startup_time.reached():
                    try:
                        connect_device(dev)
                        break
                    except ElementNotFoundError:
                        time.sleep(3)
                if startup_time.reached():
                    raise NotRunningError(dev)
        if logdir:
            logdir = script_log_dir(basedir, logdir)
            set_logdir(logdir)
        if project_root:
            ST.PROJECT_ROOT = project_root
        if compress:
            ST.SNAPSHOT_QUALITY = compress

    """
    Device Operations
    """

    @staticmethod
    def app_is_running() -> bool:
        """
        Platforms:
            Windows

        Returns:
            Whether app is running
        """
        return G.DEVICE.app_is_running()

    @staticmethod
    def stop_app(package=None):
        """
        Stop the target application on device

        Return:
            Has the Windows application stopped, on Android and iOS no return.

        Platforms:
            Android, iOS, Windows

        Example:
            stop_app("com.netease.cloudmusic")
            stop_app()  # only test on Windows
        """
        return G.DEVICE.stop_app(package)

    @staticmethod
    @logwrap
    def touch(
            v: Template or tuple,
            times: int = 1,
            blind: bool = False,
            interval: float = 0.05,
            ocr_mode: int = 0,
            cls: Type[Ocr] = Ocr,
            **kwargs
    ) -> tuple:
        """
        Perform the touch action on the device screen

        Args:
            v: Target to touch, either a ``ImageTemplate`` instance or absolute coordinates (x, y).
            times: How many touches to be performed
            blind: Whether to recognize Template, sometimes we only need to click without caring about the image.
            interval: Time interval between two touches.
            ocr_mode: Ocr match rules, one of `OCR_EQUAL`, `OCR_CONTAINS`, `OCR_SIMILAR`.
            cls: "Ocr" class or its subclass
            **kwargs: Platform specific `kwargs`, please refer to corresponding docs.

        Returns:
            Final position to be clicked, e.g. (100, 100)

        Platforms:
            Android, Windows, iOS

        Examples:
            Click absolute coordinates:
                touch((100, 100))
            Click 2 times:
                touch((100, 100), times=2)
            Under Android and Windows platforms, you can set the click duration:
                touch((100, 100), duration=2)
            Right click(Windows):
                touch((100, 100), right_click=True)
        """
        if isinstance(v, Template):
            if blind:
                center_pos = (v.area[2] + v.area[0]) / 2, (v.area[3] + v.area[1]) / 2
            else:
                center_pos = loop_find(v, timeout=ST.FIND_TIMEOUT, cls=cls, ocr_mode=ocr_mode)

            h = v.height * v.ratio()
            w = v.width * v.ratio()  # actual height and width of target in screen
            pos = random_rectangle_point(center_pos, h, w)
        else:
            try_log_screen()
            pos = v
        for _ in range(times):
            G.DEVICE.touch(pos, **kwargs)
            time.sleep(interval)
        delay_after_operation()
        return pos

    @logwrap
    def find_click(
            self,
            rec_template: Template,
            touch_template: Template = None,
            times: int = 1,
            timeout: float = 1,
            blind: bool = False,
            ocr_mode: int = 0,
            cls: Type[Ocr] = Ocr
    ) -> bool:
        """
        Find the template image and click it or another image area.

        Args:
            rec_template: "Template" instance to be found.
            touch_template: "ImageTemplate" instance to be clicked, defaults to None which means click rec_template.
            times: How many touches to be performed.
            timeout: Time interval to wait for the match.
            blind: Whether to recognize Template, same as parameter of touch().
            ocr_mode: Ocr match rules, one of `OCR_EQUAL`, `OCR_CONTAINS`, `OCR_SIMILAR`.
            cls: "Ocr" class or its subclass

        Returns:
            bool: Whether the target image appear and click it.
        """
        try:
            pos = self.wait(rec_template, timeout=timeout, ocr_mode=ocr_mode, cls=cls)
            h = rec_template.height * rec_template.ratio()
            w = rec_template.width * rec_template.ratio()  # actual height and width of target in screen
            pos = random_rectangle_point(pos, h, w)
        except TargetNotFoundError:
            return False

        if touch_template:
            self.touch(touch_template, times, blind, ocr_mode=ocr_mode, cls=cls)
            logger.info((f"Click{pos} {times} times" if times > 1 else f"Click{pos}") + f" @{touch_template.name}")
        else:
            self.touch(pos, times)
            logger.info((f"Click{pos} {times} times" if times > 1 else f"Click{pos}") + f" @{rec_template.name}")
        return True

    @staticmethod
    @logwrap
    def exists(v: Template, timeout: float = 0, ocr_mode: int = 0, cls: Type[Ocr] = Ocr) -> bool or tuple:
        """
        Check whether given target exists on device screen

        Args:
            v: target to be checked
            timeout: time limit, default is 0 which means loop_find will only search once
            ocr_mode: Ocr match rules, one of `OCR_EQUAL`, `OCR_CONTAINS`, `OCR_SIMILAR`.
            cls: "Ocr" class or its subclass

        Returns:
            False if target is not found, otherwise returns the coordinates of the target

        Platforms:
            Android, Windows, iOS

        Examples:
            if exists(ImageTemplate(r"tpl1606822430589.png")):
                touch(ImageTemplate(r"tpl1606822430589.png"))

            Since ``exists()`` will return the coordinates,
            we can directly click on this return value to reduce one image search:

            pos = exists(ImageTemplate(r"tpl1606822430589.png"))
            if pos:
                touch(pos)
        """
        try:
            pos = loop_find(v, timeout=timeout, ocr_mode=ocr_mode, cls=cls)
        except TargetNotFoundError:
            return False
        else:
            return pos

    @staticmethod
    @logwrap
    def wait(
            v: Template,
            timeout: float = None,
            interval: float = 0.5,
            interval_func: Callable = None,
            ocr_mode: int = 0,
            cls: Type[Ocr] = Ocr
    ) -> tuple:
        """
        Wait to match the Template on the device screen

        Args:
            v: target object to wait for, Template instance
            timeout: time interval to wait for the match, default is None which is ``ST.FIND_TIMEOUT``
            interval: time interval in seconds to attempt to find a match
            interval_func: called after each unsuccessful attempt to find the corresponding match
            ocr_mode: Ocr match rules, one of `OCR_EQUAL`, `OCR_CONTAINS`, `OCR_SIMILAR`.
            cls: "Ocr" class or its subclass

        Raises:
            TargetNotFoundError: raised if target is not found after the time limit expired

        Returns:
            coordinates of the matched target

        Platforms:
            Android, Windows, iOS

        Examples:
            wait(Template(r"tpl1606821804906.png"))  # timeout after ST.FIND_TIMEOUT
            # find Template every 3 seconds, timeout after 120 seconds
            wait(Template(r"tpl1606821804906.png"), timeout=120, interval=3)

            You can specify a callback function every time the search target fails::

            def notfound():
                print("No target found")
            wait(Template(r"tpl1607510661400.png"), interval_func=notfound)
        """
        if timeout is None:
            timeout = ST.FIND_TIMEOUT
        pos = loop_find(v, timeout=timeout, interval=interval, interval_func=interval_func, ocr_mode=ocr_mode, cls=cls)

        return pos

    @staticmethod
    def swipe(
            v1: Template or tuple,
            v2: Template or tuple = None,
            vector: tuple = None,
            blind1: bool = False,
            blind2: bool = False,
            **kwargs
    ) -> tuple:
        """
        Perform the swipe action on the device screen.

        There are two ways of assigning the parameters
            * ``swipe(v1, v2=Template(...))``   # swipe from v1 to v2
            * ``swipe(v1, vector=(x, y))``      # swipe starts at v1 and moves along the vector.

        Args:
            v1: the start point of swipe, either a Template instance or absolute coordinates (x, y)
            v2: the end point of swipe, either a Template instance or absolute coordinates (x, y)
            vector: a vector coordinates of swipe action, either absolute coordinates (x, y) or percentage of
                    screen e.g.(0.5, 0.5)
            blind1: Whether to recognize Template1, same as parameter of touch().
            blind2: Whether to recognize Template2, same as parameter of touch().
            **kwargs: platform specific `kwargs`, please refer to corresponding docs

        Raises:
            general exception when not enough parameters to perform swap action have been provided

        Returns:
            Origin position and target position

        Platforms:
            Android, Windows, iOS

        Examples:
            swipe(Template(r"tpl1606814865574.png"), vector=[-0.0316, -0.3311])
            swipe((100, 100), (200, 200))

            Custom swiping duration and number of steps(Android and iOS)::

            # swiping lasts for 1 second, divided into 6 steps
            swipe((100, 100), (200, 200), duration=1, steps=6)
        """
        if isinstance(v1, Template):
            if blind1:
                pos1 = (v1.area[2] + v1.area[0]) / 2, (v1.area[3] + v1.area[1]) / 2
            else:
                pos1 = loop_find(v1, timeout=ST.FIND_TIMEOUT)
        else:
            try_log_screen()
            pos1 = v1

        if v2:
            if isinstance(v2, Template):
                if blind2:
                    pos2 = (v2.area[2] + v2.area[0]) / 2, (v2.area[3] + v2.area[1]) / 2
                else:
                    pos2 = loop_find(v2, timeout=ST.FIND_TIMEOUT_TMP)
            else:
                pos2 = v2
        elif vector:
            if vector[0] <= 1 and vector[1] <= 1:
                w, h = G.DEVICE.get_current_resolution()
                vector = (int(vector[0] * w), int(vector[1] * h))
            pos2 = (pos1[0] + vector[0], pos1[1] + vector[1])
        else:
            raise ScriptError("no enough params for swipe")

        G.DEVICE.swipe(pos1, pos2, **kwargs)
        delay_after_operation()
        logger.info(f"Swipe {pos1} -> {pos2}")
        return pos1, pos2

    @staticmethod
    def screenshot():
        """
        Returns:
            Screenshot image
        """
        return G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)

    @staticmethod
    def snapshot(filename=None, msg="", quality=None, max_size=None):
        """
        Returns:
            {"screen": filename, "resolution": resolution of the screen} or None
        """
        return snapshot(filename, msg, quality, max_size)

    @staticmethod
    def shell(cmd):
        return shell(cmd)

    @staticmethod
    def start_app(package, activity=None):
        start_app(package, activity)

    @staticmethod
    def clear_app(package):
        clear_app(package)

    @staticmethod
    def install(filepath, **kwargs):
        return install(filepath, **kwargs)

    @staticmethod
    def uninstall(package):
        return uninstall(package)

    @staticmethod
    def wake():
        wake()

    @staticmethod
    def home():
        home()

    @staticmethod
    def double_click(v):
        return double_click(v)

    @staticmethod
    def pinch(in_or_out='in', center=None, percent=0.5):
        pinch(in_or_out, center, percent)

    @staticmethod
    def key_event(keyname, **kwargs):
        keyevent(keyname, **kwargs)

    @staticmethod
    def text(txt, enter=True, **kwargs):
        text(txt, enter, **kwargs)

    @staticmethod
    def sleep(secs=1.0):
        sleep(secs)

    @staticmethod
    def find_all(v):
        return find_all(v)

    @staticmethod
    def get_clipboard(*args, **kwargs):
        return get_clipboard(*args, **kwargs)

    @staticmethod
    def set_clipboard(content, *args, **kwargs):
        set_clipboard(content, *args, **kwargs)
