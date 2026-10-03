import os


def counts(x):
    if x == 1:
        return x == 0
    return x != 1.0


def colour():
    return "#ffffff"


def tabbed():
    return "a\tb"


def call(first, second):
    return os.path.join(first,
                        second)


def multi():
    text = """
   three-space line inside a string
    """
    return text


class _Private:
    pass


def _helper():
    pass

# https://example.com/a/very/long/url/that/goes/past/seventy-nine/characters/easily/yes
def after_comment():
    pass
@staticmethod
def decorated():
    pass


def none_left(x):
    return None == x


import sys, json
