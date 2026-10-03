import functools
from typing import overload

__all__ = ["Listed", "listed", "Exported"]


def listed():
    pass


def not_listed():
    pass


class Listed:

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Listed"

    def __call__(self):
        return 1

    def __new__(cls, *args):
        return super().__new__(cls)

    def method(self):
        pass

    def _private(self):
        pass

    @property
    def prop(self):
        """Returns the value."""
        return self.value

    @prop.setter
    def prop(self, value):
        self.value = value

    @overload
    def over(self, x: int) -> int: ...

    @overload
    def over(self, x: str) -> str: ...

    def over(self, x):
        return x

    class Inner:

        def inner_method(self):
            pass

    class _Hidden:
        pass

    @staticmethod
    @functools.lru_cache
    def decorated():
        pass


class Exported:
    '''Uses single quotes.'''

    def one(self):
        """
        One-liner spread over lines.
        """

    def two(self):
        """Summary without a blank line after it
        details follow here."""

    def three(self):
        """Summary without period"""

    def four(self):
        """Returns something.

        Longer text.
        """

    def five(self):
        """This method does things."""

    def test_six(self):
        """Returns in a test are fine."""

    def seven(self):
        "Single double quotes."

    def eight(self):
        r"""Raw docstring is fine\d."""

    def nine(self):
        """Helper that does things."""

    def ten(self):
        """Initializes the thing."""

    def eleven(self):
        """Access the thing."""

    def twelve(self):
        """Process data."""

    def thirteen(self):
        """Running the loop."""

    def fourteen(self):
        """Created the thing."""

    def fifteen(self):
        """Applies the rule."""

    def sixteen(self):
        """    Leading spaces then text."""

    def seventeen(self):
        """Summary line.


        Two blanks after summary.
        """

    def eighteen(self):
        """Ends with other punctuation!"""

    def nineteen(self):
        """Has a very long docstring line that goes on and on past seventy two chars."""

    def twenty(self):
        """Summary.

        https://example.com/a/very/long/url/that/goes/on/and/on/past/seventy/two/characters
        """

    def twentyone(self):
        """'Quoted' first word."""


if True:
    def in_if():
        pass


def outer():
    def inner():
        pass

    class InFunc:
        def m(self):
            pass
    return inner, InFunc


# a comment line that is quite long and keeps going past the seventy two limit
x = 1  # inline comment that is long and keeps going past the seventy-two limit yes
