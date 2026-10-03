"""Module."""

if True:
    def in_if():
        """No period"""


class Holder:
    """Class."""

    if True:
        def in_class_if(self):
            pass

        def in_class_if_doc(self):
            """No period"""

    def outer(self):
        """Outer."""
        def inner():
            """Returns bad mood and no period"""
        return inner


def wrapper():
    """Wrap."""
    class Local:
        def method(self):
            """no period and lowercase"""
    return Local


def empty_doc():
    """   """


def concat():
    """Part one. """ """Part two."""
