import re
import time
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Optional

from pponnxcr.predict_system import BoxedResult

from zafkiel.logger import logger
from zafkiel.config import Config
from zafkiel.decorator import cached_property
from zafkiel.device.template import ImageTemplate
from zafkiel.exception import ScriptError
from zafkiel.ocr.keyword import Keyword
from zafkiel.ocr.models import TextSystem, OCR_MODEL
from zafkiel.ocr.utils import merge_buttons, corner2area, area_pad
from zafkiel.utils import crop

OCR_EQUAL = 0
OCR_CONTAINS = 1
OCR_SIMILAR = 2


class OcrResultButton:
    def __init__(self, boxed_result: BoxedResult, matched_keyword: Optional[Keyword]):
        """
        Args:
            boxed_result: BoxedResult from ppocr-onnx
            matched_keyword: Keyword object or None
        """
        self.area = boxed_result.box
        self.search = area_pad(self.area, pad=-20)
        # self.button = boxed_result.box

        if matched_keyword is not None:
            self.matched_keyword = matched_keyword
            self.name = str(matched_keyword)
        else:
            self.matched_keyword = None
            self.name = boxed_result.text

        self.text = boxed_result.text
        self.score = boxed_result.score

    @property
    def is_keyword_matched(self) -> bool:
        return self.matched_keyword is not None

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)

    def __bool__(self):
        return True


class Ocr:
    # Merge results with box distance <= thres
    merge_thres_x = 0
    merge_thres_y = 0

    def __init__(self, button: ImageTemplate, lang=None, name=None):
        """
        Args:
            button:
            lang: If None, use in-game language
            name: If None, use button.name
        """
        if lang is None:
            lang = 'cn'
        if name is None:
            name = button.name

        self.button: ImageTemplate = button
        self.lang: str = lang
        self.name: str = name

    @cached_property
    def model(self) -> TextSystem:
        return OCR_MODEL.get_by_lang(self.lang)

    @staticmethod
    def pre_process(image):
        """
        To be overridden.
        """
        return image

    @staticmethod
    def after_process(result):
        """
        To be overridden.
        """
        return result

    def format_result(self, result) -> str:
        """
        To be overridden.
        """
        return result

    def ocr_single_line(self, image):
        # pre process
        start_time = time.time()
        image = crop(image, self.button.area)
        image = self.pre_process(image)
        # ocr
        result, _ = self.model.ocr_single_line(image)
        # after proces
        result = self.after_process(result)
        result = self.format_result(result)

        cost_time = time.time() - start_time
        logger.debug(f'OCR <{self.name}> cost {cost_time:.2f}s: {result}')
        return result

    def filter_detected(self, result: BoxedResult) -> bool:
        """
        Return False to drop result.
        To be overridden.
        """
        return True

    def detect_and_ocr(self, image, direct_ocr=False) -> list[BoxedResult]:
        """
        Args:
            image:
            direct_ocr: True to ignore `button` attribute and feed the image to OCR model without cropping.

        Returns:

        """
        # pre process
        start_time = time.time()
        if not direct_ocr:
            image = crop(image, self.button.area)
        image = self.pre_process(image)
        # ocr
        results: list[BoxedResult] = self.model.detect_and_ocr(image)
        # after proces
        for result in results:
            if not direct_ocr:
                result.box += self.button.area[:2]
            result.box = tuple(corner2area(result.box))

        results = [result for result in results if self.filter_detected(result)]
        results = merge_buttons(results, thres_x=self.merge_thres_x, thres_y=self.merge_thres_y)
        for result in results:
            result.text = self.after_process(result.text)

        cost_time = time.time() - start_time
        logger.debug(f"OCR <{self.name}> cost {cost_time:.2f}s: {', '.join([result.text for result in results])}")
        return results

    @staticmethod
    def _match_result(
            result: str,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True,
            ignore_digit=True):
        """
        Args:
            result (str):
            keyword_classes: A list of `Keyword` class or classes inherited `Keyword`

        Returns:
            If matched, return `Keyword` object or objects inherited `Keyword`
            If not match, return None
        """
        if not isinstance(keyword_classes, list):
            keyword_classes = [keyword_classes]

        # Digits will be considered as the index of keyword
        if ignore_digit:
            if result.isdigit():
                return None

        # Try in current lang
        for keyword_class in keyword_classes:
            try:
                matched = keyword_class.find(
                    result,
                    lang=lang,
                    ignore_punctuation=ignore_punctuation
                )
                return matched
            except ScriptError:
                continue

        return None

    def matched_single_line(
            self,
            image,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True
    ):
        """
        Args:
            image: Image to detect
            keyword_classes: `Keyword` class or classes inherited `Keyword`, or a list of them.
            lang:
            ignore_punctuation:

        Returns:
            If matched, return `Keyword` object or objects inherited `Keyword`
            If not match, return None
        """
        result = self.ocr_single_line(image)

        result = self._match_result(
            result,
            keyword_classes=keyword_classes,
            lang=lang,
            ignore_punctuation=ignore_punctuation,
        )

        logger.debug(f'<{self.name}> matched: {str(result)}')
        return result

    def _product_button(
            self,
            boxed_result: BoxedResult,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True,
            ignore_digit=True
    ) -> OcrResultButton:
        if not isinstance(keyword_classes, list):
            keyword_classes = [keyword_classes]

        matched_keyword = self._match_result(
            boxed_result.text,
            keyword_classes=keyword_classes,
            lang=lang,
            ignore_punctuation=ignore_punctuation,
            ignore_digit=ignore_digit,
        )
        button = OcrResultButton(boxed_result, matched_keyword)
        return button

    def matched_ocr(self, image, keyword_classes, direct_ocr=False) -> list[OcrResultButton]:
        """
        Match all instances of 'keyword_classes' on the screen.

        Args:
            image: Screenshot
            keyword_classes: `Keyword` class or classes inherited `Keyword`, or a list of them.
            direct_ocr: True to ignore `button` attribute and feed the image to OCR model without cropping.

        Returns:
            List of matched OcrResultButton.
            OCR result which didn't matched known keywords will be dropped.
        """
        results = self.detect_and_ocr(image, direct_ocr=direct_ocr)
        results = [self._product_button(result, keyword_classes) for result in results]
        results = [result for result in results if result.is_keyword_matched]

        if results:
            logger.debug(f"<{self.name}> matched: {', '.join([str(result) for result in results])}")
        # else:
        #     logger.debug(f"<{self.name}> matching failed")
        return results

    def ocr_match_keyword(self, image, keyword_instance, direct_ocr=False, mode: int = OCR_EQUAL, threshold=0.75) \
            -> list[OcrResultButton]:
        """
        Match a specified keyword instance on the screen.

        Args:
            image: Screenshot
            keyword_instance: Instance of `Keyword` class or its subclass.
            direct_ocr: True to ignore `button` attribute and feed the image to OCR model without cropping.
            mode: Match rules, one of `OCR_EQUAL`, `OCR_CONTAINS`, `OCR_SIMILAR`.
            threshold: Similarity threshold, default 0.75, only work when mode is OCR_SIMILAR.

        Returns:
            List of matched OcrResultButton or empty list.
        """
        boxed_results = self.detect_and_ocr(image, direct_ocr=direct_ocr)
        final_results = []
        for boxed_result in boxed_results:
            for keyword in keyword_instance.keywords_to_find():
                if mode == OCR_EQUAL and boxed_result.text != keyword:
                    continue
                elif mode == OCR_CONTAINS and keyword not in boxed_result.text:
                    continue
                elif mode == OCR_SIMILAR:
                    similarity = SequenceMatcher(None, boxed_result.text, keyword).ratio()
                    if similarity < threshold:
                        continue
                button = OcrResultButton(boxed_result, keyword_instance)
                final_results.append(button)

        if final_results:
            logger.debug(f"<{self.name}> matched: {', '.join([str(result) for result in final_results])}")
        # else:
        #     logger.debug(f"<{self.name}> matching failed")
        return final_results


class Digit(Ocr):
    def __init__(self, button: ImageTemplate, lang='en', name=None):
        super().__init__(button, lang=lang, name=name)

    def format_result(self, result) -> int:
        """
        Returns:
            int:
        """
        result = super().after_process(result)
        # logger.attr(name=self.name, text=str(result))

        res = re.search(r'(\d+)', result)
        if res:
            return int(res.group(1))
        else:
            # logger.warning(f'No digit found in {result}')
            return 0


class DigitCounter(Ocr):
    def __init__(self, button: ImageTemplate, lang='en', name=None):
        super().__init__(button, lang=lang, name=name)

    def format_result(self, result) -> tuple[int, int, int]:
        """
        Do OCR on a counter, such as `14/15`, and returns 14, 1, 15

        Returns:
            int:
        """
        result = super().after_process(result)
        # logger.attr(name=self.name, text=str(result))

        res = re.search(r'(\d+)/(\d+)', result)
        if res:
            groups = [int(s) for s in res.groups()]
            current, total = int(groups[0]), int(groups[1])
            # current = min(current, total)
            return current, total - current, total
        else:
            # logger.warning(f'No digit counter found in {result}')
            return 0, 0, 0


class Duration(Ocr):
    @classmethod
    def timedelta_regex(cls, lang):
        regex_str = {
            'cn': r'^(?P<prefix>.*?)'
                  r'((?P<days>\d{1,2})\s*天\s*)?'
                  r'((?P<hours>\d{1,2})\s*小时\s*)?'
                  r'((?P<minutes>\d{1,2})\s*分钟\s*)?'
                  r'((?P<seconds>\d{1,2})\s*秒)?'
                  r'(?P<suffix>[^天时钟秒]*?)$',
            'en': r'^(?P<prefix>.*?)'
                  r'((?P<days>\d{1,2})\s*d\s*)?'
                  r'((?P<hours>\d{1,2})\s*h\s*)?'
                  r'((?P<minutes>\d{1,2})\s*m\s*)?'
                  r'((?P<seconds>\d{1,2})\s*s)?'
                  r'(?P<suffix>[^dhms]*?)$'
        }[lang]
        return re.compile(regex_str)

    def after_process(self, result):
        result = super().after_process(result)
        result = result.strip('.,。，')
        result = result.replace('Oh', '0h').replace('oh', '0h')
        return result

    def format_result(self, result: str) -> timedelta:
        """
        Do OCR on a duration, such as `18d 2h 13m 30s`, `2h`, `13m 30s`, `9s`

        Returns:
            timedelta:
        """
        matched = self.timedelta_regex(self.lang).search(result)
        if not matched:
            return timedelta()
        days = self._sanitize_number(matched.group('days'))
        hours = self._sanitize_number(matched.group('hours'))
        minutes = self._sanitize_number(matched.group('minutes'))
        seconds = self._sanitize_number(matched.group('seconds'))
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @staticmethod
    def _sanitize_number(number) -> int:
        if number is None:
            return 0
        return int(number)
