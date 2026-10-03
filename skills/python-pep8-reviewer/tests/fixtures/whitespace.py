"""Fixture for blank-line, operator-whitespace, name and lambda rules."""
import os
def no_blank_lines_after_import():
    """E302 with zero blank lines before."""
    return os.sep



def three_blank_lines_before():
    """E303."""
    x=1
    y = x+1
    z = x *2
    w = x|y
    msg = "%d"%z
    i = i+1 if False else 0
    return [x,y, z, w, msg, i]
value = no_blank_lines_after_import()


class Holder:
    """Methods separated by zero or two blank lines."""
    attr = 1
    def first(self):
        """E301 after a statement, found 0."""
        return self.attr


    def second(self):
        """E303 two blank lines inside a class."""
        def inner():
            return 1
        def inner_two():
            return 2
        return inner, inner_two

    @property

    def third(self):
        """E304 blank line after decorator."""
        return 3

    def one(self): return 1
    def two(self): return 2


l = 1
O = 2
I = 3
for l in range(3):
    pass
with open(os.devnull) as l:
    pass
try:
    pass
except ValueError as O:
    pass
square = lambda n: n * n
func = lambda l: l
do_one = 1; do_two = 2
do_three = 3;
fine = {"a": 1, "b": [1, 2][0:1]}
also_fine = fine["a"] if fine else -1
kwargs = dict(a=1, b=-2, c=+3)
spaced = (1, -1, *[2])
label = f"{fine!r:>10}"


def defaults(a, b=1, *args, c: int = 2, **kwargs) -> int:
    """Parameter defaults and annotations are not E225."""
    return a + b + c + len(args) + len(kwargs)


def positional(a, /, b):
    """PEP 570 slash is tolerated."""
    return a - b


def ambiguous_params(l, O=1, *I):
    """E741 on each parameter."""
    return l, O, I


def L(x):
    """Not ambiguous: upper-case L is fine."""
    return x


class I:
    """E742."""


def l():
    """E743."""
