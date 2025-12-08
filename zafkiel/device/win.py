import time
from typing import Tuple

from airtest import aircv
from airtest.core.win.win import Windows, require_app
from airtest.utils.snippet import get_absolute_coordinate
import mss
import numpy
from pyautogui import dragTo, moveTo
from pytweening import easeOutQuad
import win32api
import win32gui
import win32con


class WindowsPlatform(Windows):
    @require_app
    def is_foreground(self):
        """
        Check if the window has focus and is visible at its center point

        Uses two-stage detection:
        1. Check if window has input focus (fast check)
        2. Verify center point is not covered by other windows

        Returns:
            bool: True if the window has focus and is visible, False otherwise
        """
        try:
            target_hwnd = self._top_window.handle

            # Stage 1: Check if window has input focus
            if win32gui.GetForegroundWindow() != target_hwnd:
                return False

            # Stage 2: Verify center point is not covered by other windows
            rect = win32gui.GetWindowRect(target_hwnd)
            center_x = (rect[0] + rect[2]) // 2
            center_y = (rect[1] + rect[3]) // 2

            point_hwnd = win32gui.WindowFromPoint((center_x, center_y))

            # Check if the point belongs to target window or its child
            current_hwnd = point_hwnd
            while current_hwnd:
                if current_hwnd == target_hwnd:
                    return True
                try:
                    parent = win32gui.GetParent(current_hwnd)
                    if parent == 0:
                        break
                    current_hwnd = parent
                except Exception:
                    break

            return False
        except Exception:
            return False

    @require_app
    def set_foreground(self):
        """
        Bring window to top of Z-order and set input focus
        """
        import win32api
        import win32process

        hwnd = self._top_window.handle

        # Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Get current foreground window for thread attachment
        current_fg = win32gui.GetForegroundWindow()
        current_thread = win32api.GetCurrentThreadId()

        # Attach to foreground thread if different
        if current_fg and current_fg != hwnd:
            try:
                fg_thread, _ = win32process.GetWindowThreadProcessId(current_fg)
                if fg_thread != current_thread:
                    win32process.AttachThreadInput(current_thread, fg_thread, True)
            except Exception:
                pass

        # HWND_TOPMOST trick: force window to top of Z-order
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
        )
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
        )

        # Set foreground window to gain input focus
        win32gui.SetForegroundWindow(hwnd)

        # Detach thread input
        if current_fg and current_fg != hwnd:
            try:
                fg_thread, _ = win32process.GetWindowThreadProcessId(current_fg)
                if fg_thread != current_thread:
                    win32process.AttachThreadInput(current_thread, fg_thread, False)
            except Exception:
                pass

    def app_is_running(self) -> bool:
        state = self.app.is_process_running()
        return state

    def stop_app(self, pid: int = None) -> bool:
        if pid:
            return self.app.connect(process=pid).kill()
        else:
            return self.app.kill()

    def swipe(
        self,
        p1: tuple,
        p2: tuple,
        duration: float = 0.6,
        steps: int = 5,
        button: str = "left",
    ):
        """
        Perform swipe (mouse press and mouse release)

        Args:
            p1: Start point
            p2: End point
            duration: Time interval to perform this action
            steps: It is useless here
            button: Mouse button to press, 'left', 'right' or 'middle', default is 'left'

        Returns:
            None
        """
        from_x, from_y = self._action_pos(p1)
        to_x, to_y = self._action_pos(p2)

        moveTo(from_x, from_y)
        dragTo(to_x, to_y, duration=duration, tween=easeOutQuad, button=button)

    def real_resolution(self) -> Tuple[int, int]:
        """
        The real window resolution not affected by the border

        Returns:
            width, height
        """
        return win32gui.GetClientRect(self.app.window().handle)[-2:]

    def snapshot(self, filename=None, quality=10, max_size=None):
        """
        Take a screenshot and save it in ST.LOG_DIR folder

        Args:
            filename: name of the file to give to the screenshot, {time}.jpg by default
            quality: The image quality, integer in range [1, 99]
            max_size: the maximum size of the picture, e.g 1200

        Returns:
            display the screenshot

        """
        if self.app:
            rect = self.get_rect()
            monitor = {
                "top": rect.top,
                "left": rect.left,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            }
        else:
            monitor = self.screen.monitors[0]
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            screen = numpy.array(sct_img, dtype=numpy.uint8)[..., :3]
            if filename:
                aircv.imwrite(filename, screen, quality, max_size=max_size)
            return screen

    def touch(self, pos, **kwargs):
        """
        Perform mouse click action

        References:
            https://pywinauto.readthedocs.io/en/latest/code/pywinauto.mouse.html

        Args:
            pos: coordinates where to click
            **kwargs: optional arguments

        Returns:
            None

        """
        duration = kwargs.get("duration", 0.01)
        right_click = kwargs.get("right_click", False)
        button = "right" if right_click else "left"
        steps = kwargs.get("steps", 1)
        offset = kwargs.get("offset", 0)

        start = win32api.GetCursorPos()
        ori_end = get_absolute_coordinate(pos, self)
        end = self._action_pos(ori_end)
        start_x, start_y = start[0], start[1]
        end_x, end_y = end[0], end[1]

        interval = float(duration) / steps
        time.sleep(interval)

        for i in range(1, steps):
            x = int(start_x + (end_x - start_x) * i / steps)
            y = int(start_y + (end_y - start_y) * i / steps)
            self.mouse.move(coords=(x, y))
            time.sleep(interval)

        self.mouse.move(coords=(end_x, end_y))

        for i in range(1, offset + 1):
            self.mouse.move(coords=(end_x + i, end_y + i))
            time.sleep(0.01)

        for i in range(offset):
            self.mouse.move(coords=(end_x + offset - i, end_y + offset - i))
            time.sleep(0.01)

        self.mouse.press(button=button, coords=(end_x, end_y))
        time.sleep(duration)
        self.mouse.release(button=button, coords=(end_x, end_y))
        return ori_end
