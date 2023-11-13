"""
This OCR module is from https://github.com/LmeSzinc/StarRailCopilot/tree/master/module/ocr,
only modified to fit the project and:
delete some methods
add Ocr.ocr_match_keyword()
"""
from zafkiel.ocr.keyword import Keyword
from zafkiel.ocr.ocr import Ocr, Digit, DigitCounter, Duration, OcrResultButton
