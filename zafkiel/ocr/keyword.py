import re
from dataclasses import dataclass
from functools import cached_property
from typing import ClassVar

from zafkiel.config import Config
from zafkiel.exception import ScriptError

REGEX_PUNCTUATION = re.compile(r'[ ,.\'"“”，。:：!！?？·•\-—/\\\n\t()\[\]（）「」『』【】《》［］]')


def parse_name(n):
    n = REGEX_PUNCTUATION.sub('', str(n)).lower()
    return n


@dataclass
class Keyword:
    cn: str = ''
    cht: str = ''
    en: str = ''
    jp: str = ''
    # id: int   # To be considered
    name: str = ''

    """
    Instance attributes and methods
    TODO: Error handling for missing attributes
    """

    @cached_property
    def ch(self) -> str:
        return self.cn

    @cached_property
    def cn_parsed(self) -> str:
        return parse_name(self.cn)

    @cached_property
    def en_parsed(self) -> str:
        return parse_name(self.en)

    @cached_property
    def jp_parsed(self) -> str:
        return parse_name(self.jp)

    @cached_property
    def cht_parsed(self) -> str:
        return parse_name(self.cht)

    def __str__(self):
        keyword_list = []
        for keyword in [self.cn, self.cht, self.en, self.jp]:
            if keyword != '':
                keyword_list.append(keyword)
        return f"{self.__class__.__name__}({self.name})->{'/'.join(keyword_list)}"

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)

    def __bool__(self):
        return True

    def keywords_to_find(self, lang: str = None, ignore_punctuation: bool = True):
        if lang is None:
            lang = 'cn'

        # TODO: fix this refer to SRC
        if lang == 'cn':
            if ignore_punctuation:
                return [self.cn_parsed]
            else:
                return [self.cn]
        elif lang == 'en':
            if ignore_punctuation:
                return [self.en_parsed]
            else:
                return [self.en]
        elif lang == 'jp':
            if ignore_punctuation:
                return [self.jp_parsed]
            else:
                return [self.jp]
        elif lang == 'cht':
            if ignore_punctuation:
                return [self.cht_parsed]
            else:
                return [self.cht]
        else:
            if ignore_punctuation:
                return [
                    self.cn_parsed,
                    self.en_parsed,
                    self.jp_parsed,
                    self.cht_parsed,
                ]
            else:
                return [
                    self.cn,
                    self.en,
                    self.jp,
                    self.cht,
                ]

    """
    Class attributes and methods

    Note that dataclasses inherited `Keyword` must override `instances` attribute,
    or `instances` will still be a class attribute of base class.
    ```
    @dataclass
    class DungeonNav(Keyword):
        instances: ClassVar = {}
    ```
    """
    # Key: instance name. Value: instance object.
    instances: ClassVar = {}

    def __post_init__(self):
        self.__class__.instances[self.name] = self

    @classmethod
    def _compare(cls, name, keyword):
        return name == keyword

    @classmethod
    def find(cls, name, lang: str = None, ignore_punctuation: bool = True):
        """
        Args:
            name: Name in any server or instance id.
            lang: Lang to find from. None to search the names from current server only.
            ignore_punctuation: True to remove punctuations and turn into lowercase before searching.

        Returns:
            Keyword instance.

        Raises:
            ScriptError: If nothing found.
        """
        # Already a keyword
        if isinstance(name, Keyword):
            return name

        # Probably a variable name
        if isinstance(name, str) and '_' in name:
            for instance in cls.instances.values():
                if name == instance.name:
                    return instance
        # Probably an in-game name
        if ignore_punctuation:
            name = parse_name(name)
        else:
            name = str(name)
        instance: Keyword
        for instance in cls.instances.values():
            for keyword in instance.keywords_to_find(
                    lang=lang, ignore_punctuation=ignore_punctuation):
                if cls._compare(name, keyword):
                    return instance

        # Not found
        raise ScriptError(f'Cannot find a {cls.__name__} instance that matches "{name}"')
