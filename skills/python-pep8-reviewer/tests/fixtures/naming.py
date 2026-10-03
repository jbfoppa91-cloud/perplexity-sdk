"""Naming probe."""
import abc
from collections import namedtuple
from typing import NamedTuple, TypeVar

GLOBAL_OK = 1
mixedGlobal = 2
_privateMixed = 3
Point = namedtuple("Point", "x y")
T = TypeVar("T")
CONFIG = {"KeyName": 1}


class MyError(Exception):
    """Fine."""


class BadException(Exception):
    """N818."""


class Derived(BadException):
    """N818 via same-module parent."""


class NotCaught(ValueError):
    """Not flagged: base is not literally Exception."""


class Meta(type):
    """Metaclass."""

    def __new__(mcs, name, bases, ns):
        return super().__new__(mcs, name, bases, ns)

    def method(cls):
        return cls


class Widget(abc.ABC):
    """Class scope."""

    classAttr = 1
    CONSTANT = 2
    snake_attr = 3

    def __new__(klass, *args):
        return super().__new__(klass)

    def __init_subclass__(klass, **kwargs):
        super().__init_subclass__(**kwargs)

    def method(this, badArg, Other, *Args, **KwArgs):
        LocalVar = 1
        local_ok = 2
        for Item in range(3):
            pass
        with open("x") as FileHandle:
            pass
        try:
            pass
        except ValueError as Err:
            pass
        squares = [Sq for Sq in range(3)]
        (Walrus := 1)
        Pt = namedtuple("Pt", "a b")
        Named: int = 5
        a, (b, BadC) = 1, (2, 3)
        return LocalVar, local_ok, squares, Pt, Named, BadC, Walrus

    def uses_global(self):
        global SOME_GLOBAL
        SOME_GLOBAL = 1

    @classmethod
    def make(klass):
        return klass()

    @classmethod
    def ok(cls):
        return cls()

    @staticmethod
    def static(anything):
        return anything

    def late(x):
        return x

    late = staticmethod(late)

    if True:
        def in_block(self_ok):
            return self_ok

    def outer(self):
        def inner(notself):
            return notself
        return inner

    @property
    def prop(self):
        return 1

    def no_args():
        pass

    def kwonly(*, key):
        return key

    def star_first(*args):
        return args

    def setUp(self):
        pass


def function(self, ArgName):
    MixedLocal = 1
    return MixedLocal


class TypedTuple(NamedTuple):
    fieldName: int


lambda BadLambdaArg: BadLambdaArg
