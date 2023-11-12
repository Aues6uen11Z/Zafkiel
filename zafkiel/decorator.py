from typing import Callable, Generic, TypeVar

T = TypeVar("T")


def run_once(f):
    """
    From https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/base/decorator.py
    Run a function only once, no matter how many times it has been called.

    Examples:
        @run_once
        def my_function(foo, bar):
            return foo + bar

        while 1:
            my_function()

    Examples:
        def my_function(foo, bar):
            return foo + bar

        action = run_once(my_function)
        while 1:
            action()
    """

    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)

    wrapper.has_run = False
    return wrapper


class cached_property(Generic[T]):
    """
    From https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/base/decorator.py

    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    """

    def __init__(self, func: Callable[..., T]):
        self.func = func

    def __get__(self, obj, cls) -> T:
        if obj is None:
            return self

        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def run_until_true(f):
    """
    Run a function until it returns True, no matter how many times it has been called.

    Examples:
        @run_until_true
        def my_function(a):
            print('run +1')
            return a==2

        for i in range(6):
            my_function(i)
    """

    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            result = f(*args, **kwargs)
            if result is True:
                wrapper.has_run = True
            return result

    wrapper.has_run = False
    return wrapper