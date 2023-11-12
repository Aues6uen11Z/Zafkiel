from airtest.core.helper import G

from zafkiel.device.api import API
from zafkiel.device.template import ImageTemplate as Template
from zafkiel.device.win import WindowsPlatform
from zafkiel.ocr.keyword import Keyword
from zafkiel.ocr.ocr import Ocr, Digit, DigitCounter, Duration, OcrResultButton
from zafkiel.ui.page import Page
from zafkiel.ui.switch import Switch
from zafkiel.ui.ui import UI

from zafkiel.logger import logger

__version__ = '0.0.1'

G.register_custom_device(WindowsPlatform)
