from __future__ import annotations
import traceback

from zafkiel.device.template import ImageTemplate as Template
from zafkiel.ui.switch import Switch


class Page:
    """
    Main code comes from https://github.com/LmeSzinc/StarRailCopilot/blob/master/tasks/base/page.py
    """

    # Key: str, page name like "page_main"
    # Value: Page, page instance
    all_pages = {}

    @classmethod
    def clear_connection(cls):
        for page in cls.all_pages.values():
            page.parent = None

    @classmethod
    def init_connection(cls, destination: Page):
        """Initialize an A* path finding among pages.

        Args:
            destination:
        """
        cls.clear_connection()

        visited = [destination]
        visited = set(visited)
        while True:
            new = visited.copy()
            for page in visited:
                for link in cls.iter_pages():
                    if link in visited:
                        continue
                    if page in link.links:
                        link.parent = page
                        new.add(link)
            if len(new) == len(visited):
                break
            visited = new

    @classmethod
    def iter_pages(cls, start_page: Page = None):
        pages = list(cls.all_pages.values())
        if start_page is not None and start_page in pages:
            # Move start_page to the front of the list
            pages.remove(start_page)
            pages.insert(0, start_page)
            cls.all_pages = {page.name: page for page in pages}
        return cls.all_pages.values()

    @classmethod
    def iter_check_buttons(cls):
        for page in cls.all_pages.values():
            yield page.check_button

    def __init__(self, check_button: Template, switch: Switch = None):
        self.check_button = check_button
        self.switch = switch
        self.links = {}
        (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
        self.name = text[:text.find('=')].strip()
        self.parent = None
        Page.all_pages[self.name] = self

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    __repr__ = __str__

    def link(self, button: Template, destination: Page):
        self.links[destination] = button
