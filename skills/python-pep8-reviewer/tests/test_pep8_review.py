"""Tests for scripts/pep8_review.py.

Run with ``python3 -m pytest tests`` from the skill directory. The
flake8 cross-check tests are skipped when flake8, pep8-naming and
flake8-docstrings are not installed.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "pep8_review.py"

spec = importlib.util.spec_from_file_location("pep8_review", SCRIPT)
pep8_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pep8_review)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def scan(tmp_path: Path, source: str, name: str = "mod.py", **limits):
    """Write ``source`` to a file and return (line, code) findings.

    Sources are dedented unless ``dedent=False``; dedenting would
    erase whitespace-only lines that some tests need to keep.
    """
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if limits.get("dedent", True):
        source = textwrap.dedent(source).lstrip("\n")
    path.write_text(source, encoding="utf-8")
    limit = limits.get("limit", 79)
    doc_limit = limits.get("doc_limit", 72)
    findings = pep8_review.review_file(path, limit, doc_limit)
    return sorted((f["line"], f["code"]) for f in findings)


def codes(findings) -> set[str]:
    """Return the set of codes in a findings list."""
    return {code for _, code in findings}


def flake8_available() -> bool:
    """Return True when flake8 with the needed plugins is installed."""
    if shutil.which("flake8") is None:
        return False
    out = subprocess.run(
        ["flake8", "--version"], capture_output=True, text=True
    ).stdout
    return "pep8-naming" in out and "flake8-docstrings" in out


# Codes the script implements and flake8 (with plugins) also reports.
SHARED_CODES = {
    "W191", "W291", "W292", "W293", "W505",
    "E101", "E111", "E261", "E302", "E401", "E402", "E501", "E701",
    "E711", "E712", "E722", "F403", "E999",
    "N801", "N802", "N803", "N804", "N805", "N806", "N815", "N816", "N818",
    "D100", "D101", "D102", "D103", "D104", "D105", "D106", "D107",
    "D200", "D205", "D209", "D300", "D400", "D401", "D419",
}


def flake8_findings(path: Path, limit: int = 79) -> set[tuple[int, str]]:
    """Run flake8 on ``path``; return the shared (line, code) pairs."""
    out = subprocess.run(
        [
            "flake8",
            f"--max-line-length={limit}",
            "--max-doc-length=72",
            "--select=E,W,F403,N,D",
            str(path),
        ],
        capture_output=True,
        text=True,
    ).stdout
    found = set()
    for line in out.splitlines():
        match = re.match(r".+?:(\d+):\d+: (\w+)", line)
        if match and match.group(2) in SHARED_CODES:
            found.add((int(match.group(1)), match.group(2)))
    return found


# ----------------------------------------------------------------------
# Docstrings: missing (D1xx)
# ----------------------------------------------------------------------


def test_missing_module_docstring(tmp_path):
    """Check missing module docstring."""
    assert scan(tmp_path, "x = 1\n") == [(1, "D100")]


def test_missing_package_docstring(tmp_path):
    """Check missing package docstring."""
    result = scan(tmp_path, "", name="pkg/__init__.py")
    assert result == [(1, "D104")]


def test_private_module_needs_no_docstring(tmp_path):
    """Check private module needs no docstring."""
    assert scan(tmp_path, "x = 1\n", name="_private.py") == []
    assert scan(tmp_path, "x = 1\n", name="_pkg/mod.py") == []


def test_main_only_script_needs_no_module_docstring(tmp_path):
    """Check main only script needs no module docstring."""
    source = '''
    import sys

    if __name__ == "__main__":
        sys.exit(0)
    '''
    assert scan(tmp_path, source) == []


def test_missing_function_and_class_docstrings(tmp_path):
    """Check missing function and class docstrings."""
    source = '''
    """Module."""


    def public():
        pass


    def _private():
        pass


    class Public:

        def method(self):
            pass

        def _hidden(self):
            pass

        def __init__(self):
            pass

        def __repr__(self):
            return ""

        def __call__(self):
            return 1

        class Nested:
            pass

        class _Secret:
            pass


    class _Private:

        def method(self):
            pass
    '''
    assert scan(tmp_path, source) == [
        (4, "D103"),
        (12, "D101"),
        (14, "D102"),
        (20, "D107"),
        (23, "D105"),
        (26, "D102"),
        (29, "D106"),
    ]


def test_dunder_all_controls_publicity(tmp_path):
    """Check dunder all controls publicity."""
    source = '''
    """Module."""

    __all__ = ["listed"]


    def listed():
        pass


    def unlisted():
        pass
    '''
    assert scan(tmp_path, source) == [(6, "D103")]


def test_overload_setter_and_nested_scopes_are_exempt(tmp_path):
    """Check overload setter and nested scopes are exempt."""
    source = '''
    """Module."""

    from typing import overload


    class Holder:
        """Class."""

        @overload
        def value(self, x: int) -> int: ...

        @overload
        def value(self, x: str) -> str: ...

        def value(self, x):
            return x

        @property
        def prop(self):
            """Return the value."""
            return 1

        @prop.setter
        def prop(self, value):
            pass

        @overload
        def __init__(self, x: int) -> None: ...

        def __init__(self, x):
            pass


    def outer():
        """Outer."""
        def inner():
            pass

        class Local:
            def method(self):
                pass
        return inner, Local
    '''
    # overloads skip D102, but an overloaded __init__ still needs D107
    assert scan(tmp_path, source) == [
        (15, "D102"),
        (28, "D107"),
        (30, "D107"),
    ]


def test_definitions_inside_try_and_if_are_still_top_level(tmp_path):
    """Check definitions inside try and if are still top level."""
    source = '''
    """Module."""

    try:
        from socks import Proxy
    except ImportError:

        def Proxy(*args):
            raise RuntimeError("no socks")

    if True:
        def guarded():
            pass
    '''
    assert scan(tmp_path, source) == [
        (7, "D103"),
        (7, "N802"),
        (11, "D103"),
    ]


# ----------------------------------------------------------------------
# Docstrings: form (D2xx-D4xx, W505)
# ----------------------------------------------------------------------


def test_docstring_form_rules(tmp_path):
    """Check docstring form rules."""
    source = """
    '''Module uses single quotes.'''


    def one_liner_spread():
        \"\"\"
        One line over three.
        \"\"\"


    def no_blank_after_summary():
        \"\"\"Summary
        details on the next line.\"\"\"


    def no_period():
        \"\"\"Summary without period\"\"\"


    def two_blanks():
        \"\"\"Summary.


        Body.
        \"\"\"


    def empty():
        \"\"\"   \"\"\"


    def single_quote_chars():
        "Single double quotes."


    def fine():
        \"\"\"Return quickly.

        Body line.
        \"\"\"
    """
    assert scan(tmp_path, source) == [
        (1, "D300"),
        (5, "D200"),
        (11, "D205"),
        (11, "D209"),
        (11, "D400"),
        (16, "D400"),
        (20, "D205"),
        (28, "D419"),
        (32, "D300"),
    ]


def test_triple_single_quotes_allowed_when_body_has_triple_double(tmp_path):
    """Check that triple single quotes may wrap triple doubles."""
    source = """
    '''Module about \"\"\" quotes.'''
    """
    assert scan(tmp_path, source) == []


@pytest.mark.parametrize(
    "summary, expected",
    [
        ("Returns the value.", "D401"),
        ("Initializes the thing.", "D401"),
        ("Running the loop.", "D401"),
        ("Created the thing.", "D401"),
        ("Applies the rule.", "D401"),
        ("This function does things.", "D401"),
        ("Helper for things.", "D401"),
        ("Return the value.", None),
        ("Access the thing.", None),
        ("Process data.", None),
        ("Pass through.", None),
        ("Status of the thing.", None),
        ("'Quoted' first word.", None),
    ],
)
def test_imperative_mood(tmp_path, summary, expected):
    """Check imperative mood."""
    source = f'''
    """Module."""


    def func():
        """{summary}"""
    '''
    result = codes(scan(tmp_path, source))
    assert ("D401" in result) == (expected == "D401")


def test_imperative_mood_exempts_tests_properties_and_classes(tmp_path):
    """Check imperative mood exempts tests properties and classes."""
    source = '''
    """Module."""


    class Thing:
        """Returns are fine on classes."""

        @property
        def value(self):
            """Returns the value."""
            return 1

        def test_it(self):
            """Returns in tests are fine."""
    '''
    assert scan(tmp_path, source) == []


def test_doc_line_length(tmp_path):
    """Check doc line length."""
    long_text = "word " * 14 + "end"
    long_url = "https://example.com/" + "x" * 60
    source = f'''
    """Module."""

    # {long_text}
    # {long_url}
    y = 1  # {long_text[:66]}


    def func():
        """Summary.

        {long_text}
        {long_url}
        """
    '''
    # comment-only lines and docstring lines count; inline comments and
    # lone URLs do not
    result = scan(tmp_path, source)
    assert result == [(3, "W505"), (11, "W505")]
    assert scan(tmp_path, source, doc_limit=100) == []


# ----------------------------------------------------------------------
# Naming (N8xx)
# ----------------------------------------------------------------------


def test_class_and_function_names(tmp_path):
    """Check class and function names."""
    source = '''
    """Module."""


    class bad_class:
        """Doc."""


    class _Private:
        """Allowed with a leading underscore."""


    class BadException(Exception):
        """Doc."""


    class Derived(BadException):
        """Doc."""


    class FineError(Exception):
        """Doc."""


    class NotLiteral(ValueError):
        """Doc."""


    def BadFunc():
        """Doc."""


    def __dunder_ok__():
        """Doc."""
    '''
    assert scan(tmp_path, source) == [
        (4, "N801"),
        (12, "N818"),
        (16, "N818"),
        (28, "N802"),
    ]


def test_argument_names_and_self_cls(tmp_path):
    """Check argument names and self cls."""
    source = '''
    """Module."""


    class Meta(type):
        """Metaclass: every method is a classmethod."""

        def __new__(mcs, name, bases, ns):
            """Doc."""
            return super().__new__(mcs, name, bases, ns)

        def method(cls):
            """Doc."""
            return cls


    class Widget:
        """Doc."""

        def __new__(klass, *args):
            """Doc."""
            return super().__new__(klass)

        def method(this, badArg, *Args, **KwArgs):
            """Doc."""
            return this, badArg, Args, KwArgs

        @classmethod
        def make(klass):
            """Doc."""
            return klass()

        @classmethod
        def ok(cls):
            """Doc."""
            return cls()

        @staticmethod
        def static(anything):
            """Doc."""
            return anything

        def late(x):
            """Doc."""
            return x

        late = staticmethod(late)

        if True:
            def in_block(self_ok):
                """Doc."""
                return self_ok

        def outer(self):
            """Doc."""
            def inner(notself):
                return notself
            return inner

        def no_args():
            """Doc."""

        def kwonly(*, key):
            """Doc."""
            return key

        def star_first(*args):
            """Doc."""
            return args

        def setUp(self):
            """Doc."""


    def function(self, ArgName):
        """Doc."""
        return self, ArgName
    '''
    assert scan(tmp_path, source) == [
        (7, "N804"),
        (19, "N804"),
        (23, "N803"),
        (23, "N803"),
        (23, "N803"),
        (23, "N805"),
        (28, "N804"),
        (49, "N805"),
        (62, "N805"),
        (74, "N803"),
    ]


def test_variable_names_by_scope(tmp_path):
    """Check variable names by scope."""
    source = '''
    """Module."""

    from collections import namedtuple
    from typing import NamedTuple, TypeVar

    GLOBAL_OK = 1
    mixedGlobal = 2
    _privateMixed = 3
    Point = namedtuple("Point", "x y")
    T = TypeVar("T")


    class Widget:
        """Doc."""

        classAttr = 1
        CONSTANT = 2
        snake_attr = 3

        def method(self):
            """Doc."""
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
            """Doc."""
            global SOME_GLOBAL
            SOME_GLOBAL = 1


    class TypedTuple(NamedTuple):
        """Doc."""

        fieldName: int
    '''
    assert scan(tmp_path, source) == [
        (7, "N816"),
        (8, "N816"),
        (16, "N815"),
        (22, "N806"),
        (24, "N806"),
        (26, "N806"),
        (30, "N806"),
        (32, "N806"),
        (33, "N806"),
        (35, "N806"),
        (36, "N806"),
        (48, "N815"),
    ]


# ----------------------------------------------------------------------
# Regressions from the first review round
# ----------------------------------------------------------------------


def test_no_false_positives_on_valid_code(tmp_path):
    """Check no false positives on valid code."""
    source = '''
    """Module."""

    import os


    class _Private:
        """Doc."""


    def counts(x):
        """Doc."""
        if x == 1:
            return x == 0
        return x != 1.0


    def colour():
        """Doc."""
        return "#ffffff"


    def call(first, second):
        """Doc."""
        return os.path.join(first,
                            second)


    def multi():
        """Doc."""
        text = """
       three-space line inside a string
        """
        return text


    result = max(1,
                 2)
    '''
    assert scan(tmp_path, source) == []


def test_compare_and_except_rules(tmp_path):
    """Check compare and except rules."""
    source = '''
    """Module."""


    def check(x):
        """Doc."""
        try:
            pass
        except:
            pass
        return None == x or x == None or x == True or False != x
    '''
    assert scan(tmp_path, source) == [
        (8, "E722"),
        (10, "E711"),
        (10, "E711"),
        (10, "E712"),
        (10, "E712"),
    ]


def test_layout_rules(tmp_path):
    """Check layout rules."""
    source = (
        'from os import *\n'
        'import sys, json\n'
        'import requests\n'
        'import os\n'
        'class bad_class:\n'
        '\tpass\n'
        'def func(x):\n'
        '    y = 1 # bad comment   \n'
        '    \n'
        '    if x: return y\n'
        'import late\n'
        '# https://example.com/a/very/long/url/that/is/exempt/from/'
        'the/length/rule\n'
        '@staticmethod\n'
        'def decorated():\n'
        '    return "%s" % ("a" * 90)\n'
        'class Other_Name: pass'
    )
    result = scan(tmp_path, source, dedent=False)
    assert result == [
        (1, "D100"),
        (1, "F403"),
        (2, "E401"),
        (4, "I001"),
        (5, "D101"),
        (5, "E302"),
        (5, "N801"),
        (6, "W191"),
        (7, "D103"),
        (7, "E302"),
        (8, "E101"),
        (8, "E261"),
        (8, "W291"),
        (9, "E101"),
        (9, "W293"),
        (10, "E101"),
        (10, "E701"),
        (11, "E402"),
        (13, "E302"),
        (14, "D103"),
        (15, "E101"),
        (16, "D101"),
        (16, "E302"),
        (16, "E701"),
        (16, "N801"),
        (16, "W292"),
    ]


def test_def_one_liners_are_not_e701(tmp_path):
    """Check def one liners are not e701."""
    source = '''
    """Module."""

    from typing import overload


    @overload
    def f(x: int) -> int: ...


    @overload
    def f(x: str) -> str: ...


    def f(x):
        """Doc."""
        return x
    '''
    assert scan(tmp_path, source) == []


# ----------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------


def run_cli(*args: str) -> tuple[int, dict]:
    """Run the script and return (exit code, parsed JSON report)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )
    return proc.returncode, json.loads(proc.stdout)


def test_cli_exit_codes_and_skips(tmp_path):
    """Check cli exit codes and skips."""
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "skip.py").write_text("def BadName(): pass\n")
    (tmp_path / "clean.py").write_text('"""Clean."""\n')
    (tmp_path / "dirty.py").write_text("x == None\n")

    code, report = run_cli(str(tmp_path / "clean.py"))
    assert (code, report["files"], report["findings"]) == (0, 1, [])

    code, report = run_cli(str(tmp_path))
    assert code == 1 and report["files"] == 2
    assert {f["code"] for f in report["findings"]} == {"D100", "E711"}

    code, report = run_cli(str(tmp_path / "notes.txt"))
    assert code == 2 and report["error"] == "no Python files"

    code, report = run_cli(str(tmp_path / "missing.py"), str(tmp_path))
    assert code == 1
    missing = [f for f in report["findings"] if f["code"] == "E902"]
    assert [Path(f["path"]).name for f in missing] == ["missing.py"]


def test_cli_limits(tmp_path):
    """Check cli limits."""
    (tmp_path / "long.py").write_text('"""Doc."""\n\nx = "%s"\n' % ("a" * 80))
    code, report = run_cli(str(tmp_path / "long.py"))
    assert [f["code"] for f in report["findings"]] == ["E501"]
    code, report = run_cli("--line-length", "100", str(tmp_path / "long.py"))
    assert (code, report["findings"]) == (0, [])


def test_syntax_error_and_unreadable_file(tmp_path):
    """Check syntax error and unreadable file."""
    (tmp_path / "broken.py").write_text("def f(:\n")
    (tmp_path / "binary.py").write_bytes(b"\xff\xfe")
    _, report = run_cli(str(tmp_path))
    by_file = {Path(f["path"]).name: f["code"] for f in report["findings"]}
    assert by_file == {"broken.py": "E999", "binary.py": "E902"}


def test_script_passes_its_own_scan():
    """Check script passes its own scan."""
    code, report = run_cli(str(SCRIPT))
    assert (code, report["findings"]) == (0, [])


# ----------------------------------------------------------------------
# Cross-check against flake8 + pep8-naming + flake8-docstrings
# ----------------------------------------------------------------------

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.py"))


@pytest.mark.skipif(not flake8_available(), reason="flake8 plugins missing")
@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_matches_flake8_on_fixture(fixture):
    """Check matches flake8 on fixture."""
    ours = {
        (f["line"], f["code"])
        for f in pep8_review.review_file(fixture, 79, 72)
        if f["code"] in SHARED_CODES
    }
    assert ours == flake8_findings(fixture)


@pytest.mark.skipif(not flake8_available(), reason="flake8 plugins missing")
def test_matches_flake8_on_itself():
    """Check matches flake8 on itself."""
    ours = {
        (f["line"], f["code"])
        for f in pep8_review.review_file(SCRIPT, 79, 72)
        if f["code"] in SHARED_CODES
    }
    assert ours == flake8_findings(SCRIPT) == set()
