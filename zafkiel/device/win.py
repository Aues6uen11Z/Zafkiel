from typing import Tuple

from airtest.core.win import Windows
from pyautogui import dragTo, moveTo
from pytweening import easeOutQuad
import win32gui


class WindowsPlatform(Windows):

    def app_is_running(self) -> bool:
        state = self.app.is_process_running()
        return state

    def stop_app(self, pid: int = None) -> bool:
        if pid:
            return self.app.connect(process=pid).kill()
        else:
            return self.app.kill()

    def swipe(self, p1: tuple, p2: tuple, duration: float = 0.6, steps: int = 5, button: str = "left"):
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
