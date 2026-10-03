#!/usr/bin/env python3
"""Mechanical PEP 8 scan. Print a JSON report of findings.

Not a substitute for the judgment pass in SKILL.md. Does not score
quote style or hanging-indent style. Rule codes follow pycodestyle
(E/W), pyflakes (F403), pep8-naming (N8xx) and pydocstyle (Dxxx);
I001 is this script's own import-group check. The blank-line,
operator-whitespace, ambiguous-name and lambda checks are ports of
pycodestyle's logical-line checks and skip what flake8 ignores by
default (E226, E704).

Exit codes: 0 no findings, 1 findings, 2 no Python files to scan.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import keyword
import re
import sys
import tokenize
from pathlib import Path

FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
DEF_NODES = FUNC_NODES + (ast.ClassDef,)

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "site-packages",
    "__pycache__",
    "build",
    "dist",
}

# Compound statements whose body must not share the header line (E701).
COMPOUND_KEYWORDS = {
    "if",
    "elif",
    "else",
    "for",
    "while",
    "try",
    "except",
    "finally",
    "with",
    "def",
    "class",
    "async",
}

# Names pep8-naming accepts despite mixed case (unittest API).
NAMING_IGNORE = {
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "setUpModule",
    "tearDownModule",
    "asyncSetUp",
    "asyncTearDown",
    "setUpTestData",
    "failureException",
    "longMessage",
    "maxDiff",
}

# Implicit classmethods and metaclass bases, as in pep8-naming.
CLASS_METHODS = {"__new__", "__init_subclass__", "__class_getitem__"}
METACLASS_BASES = {"type", "ABCMeta"}

# Statements a definition may sit inside and still count as top level.
# pep8-naming looks through these when tagging methods ...
NAMING_CONTAINERS = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith,
    ast.Try,
)
# ... and pydocstyle also looks into except, else and match arms.
DOC_CONTAINERS = NAMING_CONTAINERS + (ast.ExceptHandler,)
if hasattr(ast, "Match"):  # Python 3.10+
    DOC_CONTAINERS += (ast.Match, ast.match_case)
if hasattr(ast, "TryStar"):  # Python 3.11+
    NAMING_CONTAINERS += (ast.TryStar,)
    DOC_CONTAINERS += (ast.TryStar,)
# pycodestyle lets imports follow these without raising E402.
IMPORT_GUARDS = (ast.If, ast.With, ast.Try) + (
    (ast.TryStar,) if hasattr(ast, "TryStar") else ()
)

# Dunder methods pydocstyle treats as ordinary public methods.
VARIADIC_MAGIC = {"__init__", "__call__", "__new__"}
PROPERTY_DECORATORS = {"property", "cached_property"}

# Imperative verbs and non-imperative openers, from pydocstyle's lists.
IMPERATIVE_VERBS = frozenset("""
accept access add adjust aggregate allow append apply archive assert
assign attempt authenticate authorize break build cache calculate call
cancel capture change check clean clear close collect combine commit
compare compute configure confirm connect construct control convert
copy count create customize declare decode decorate define delegate
delete deprecate derive describe detect determine display download
drop dump emit empty enable encapsulate encode end ensure enumerate
establish evaluate examine execute exit expand expect export extend
extract feed fetch fill filter finalize find fire fix flag force
format forward generate get give go group handle help hold identify
implement import indicate init initialise initialize initiate input
insert instantiate intercept invoke iterate join keep launch list
listen load log look make manage manipulate map mark match merge mock
modify monitor move normalize note obtain open output override
overwrite package pad parse partial pass perform persist pick plot
poll populate post prepare print process produce provide publish pull
put query raise read record refer refresh register reload remove
rename render replace reply report represent request require reset
resolve retrieve return roll rollback round run sample save scan
search select send serialise serialize serve set show simulate source
specify split start step stop store strip submit subscribe sum swap
sync synchronise synchronize take tear test time transform translate
transmit truncate try turn tweak update upload use validate verify
view wait walk wrap write yield
""".split())
IMPERATIVE_BLACKLIST = frozenset("""
a action always an api base basic business calculation callback
collection common constructor convenience convenient current currently
custom data default deprecated description dict dictionary does dummy
example factory false final formula function generic handler helper
here hook implementation importantly internal it main method module
new number optional placeholder reference result same schema setup
should simple some special sql standard static string subclasses that
the these this true unique unit utility what wrapper
""".split())

# pycodestyle's logical-line vocabulary.
TOP_LEVEL_RE = re.compile(r"^(async\s+def\s+|def\s+|class\s+|@)")
DEF_RE = re.compile(r"^(async\s+def|def)\b")
DOCSTRING_RE = re.compile(r"u?r?[\"']")
LAMBDA_RE = re.compile(r"\blambda\b")
SKIP_TOKENS = frozenset(
    {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}
)
SKIP_COMMENTS = SKIP_TOKENS | {tokenize.COMMENT, tokenize.ERRORTOKEN}
FSTRING_START = getattr(tokenize, "FSTRING_START", -1)
FSTRING_END = getattr(tokenize, "FSTRING_END", -1)
TSTRING_START = getattr(tokenize, "TSTRING_START", -1)
TSTRING_END = getattr(tokenize, "TSTRING_END", -1)
STRING_MIDDLE = {
    getattr(tokenize, "FSTRING_MIDDLE", -1),
    getattr(tokenize, "TSTRING_MIDDLE", -1),
}
WS_NEEDED = frozenset({
    "**=", "*=", "/=", "//=", "+=", "-=", "!=", "<", ">", "%=", "^=",
    "&=", "|=", "==", "<=", ">=", "<<=", ">>=", "=", "and", "in", "is",
    "or", "->", ":=",
})
UNARY = frozenset({">>", "**", "*", "+", "-"})
ARITHMETIC = frozenset({"**", "*", "/", "//", "+", "-", "@"})
WS_OPTIONAL = ARITHMETIC | {"^", "&", "|", "<<", ">>", "%"}
KEYWORDS = frozenset(keyword.kwlist + ["print"]) - {"False", "None", "True"}
AMBIGUOUS = ("l", "O", "I")
is_soft_keyword = getattr(keyword, "issoftkeyword", lambda word: False)

# Fallback for Python < 3.10, which lacks sys.stdlib_module_names.
STDLIB_FALLBACK = frozenset("""
abc argparse array ast asyncio atexit base64 binascii bisect builtins
bz2 calendar cmath codecs collections concurrent configparser contextlib
copy csv ctypes dataclasses datetime decimal difflib dis email enum
errno faulthandler fnmatch fractions functools gc getpass gettext glob
gzip hashlib heapq hmac html http imaplib importlib inspect io ipaddress
itertools json keyword linecache locale logging lzma mailbox math
mimetypes multiprocessing numbers operator os pathlib pdb pickle
pkgutil platform plistlib pprint profile pstats queue random re
reprlib sched secrets select selectors shelve shlex shutil signal
site smtplib socket socketserver sqlite3 ssl stat statistics string
stringprep struct subprocess sys sysconfig tarfile tempfile textwrap
threading time timeit tkinter token tokenize tomllib trace traceback
tracemalloc types typing unicodedata unittest urllib uuid venv warnings
wave weakref webbrowser xml xmlrpc zipfile zipimport zlib zoneinfo
""".split())

DUNDER = re.compile(r"^__[a-z0-9_]+__$")
INDENT = re.compile(r"([ \t]*)")
DOC_OPENING = re.compile(r"""[uUrRbB]*(\"\"\"|'''|"|')""")
NON_WORD = re.compile(r"[\W_]+")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def iter_py_files(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Return (python files, missing paths) for the given arguments."""
    files: list[Path] = []
    missing: list[Path] = []
    for path in paths:
        if not path.exists():
            missing.append(path)
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            for candidate in sorted(path.rglob("*.py")):
                if any(part in SKIP_DIRS for part in candidate.parts):
                    continue
                files.append(candidate)
    return files, missing


def item(path: Path, line: int, code: str, message: str) -> dict:
    """Build one finding record."""
    return {"path": str(path), "line": line, "code": code, "message": message}


def iter_nodes(node: ast.AST, parents: tuple):
    """Yield (child, ancestors) pairs for every node below ``node``."""
    for child in ast.iter_child_nodes(node):
        yield child, parents
        yield from iter_nodes(child, parents + (child,))


def decorator_name(node: ast.AST) -> str | None:
    """Return the last dotted name of a decorator expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return None


def is_mixed_case(name: str) -> bool:
    """Return True for mixedCase names, as pep8-naming defines them."""
    return name.lower() != name and name.lstrip("_")[:1].islower()


def is_lone_chunk(line: str, limit: int, multiline: bool) -> bool:
    """Mirror pycodestyle: a lone long URL in a comment or string.

    A single long chunk is exempt only inside a multi-line string;
    a ``#`` followed by one chunk is exempt anywhere.
    """
    chunks = line.split()
    lone = (len(chunks) == 1 and multiline) or (
        len(chunks) == 2 and chunks[0] == "#"
    )
    return lone and len(line) - len(chunks[-1]) < limit - 7


def multiline_string_rows(text: str) -> set[int]:
    """Return line numbers covered by multi-line string tokens."""
    rows: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                rows.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        pass
    return rows


def node_source(lines: list[str], node: ast.AST) -> str:
    """Return the source text covered by ``node``."""
    start, end = node.lineno - 1, node.end_lineno - 1
    first = lines[start].encode("utf-8")
    if start == end:
        return first[node.col_offset:node.end_col_offset].decode("utf-8")
    last = lines[end].encode("utf-8")[: node.end_col_offset].decode("utf-8")
    parts = [first[node.col_offset:].decode("utf-8")]
    parts.extend(lines[start + 1:end])
    parts.append(last)
    return "\n".join(parts)


# ----------------------------------------------------------------------
# Physical lines
# ----------------------------------------------------------------------


def physical_findings(path: Path, text: str, limit: int) -> list[dict]:
    """Check one physical line at a time."""
    findings = []
    lines = text.splitlines(keepends=True)
    if text and not text.endswith(("\n", "\r")):
        findings.append(
            item(path, len(lines) or 1, "W292", "no newline at end of file")
        )
    multiline = multiline_string_rows(text)
    indent_char = None
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        indent = INDENT.match(line).group(1)
        if indent_char is None and indent:
            indent_char = indent[0]
        if indent_char and any(char != indent_char for char in indent):
            findings.append(
                item(path, number, "E101",
                     "indentation contains mixed spaces and tabs")
            )
        if "\t" in indent:
            findings.append(
                item(path, number, "W191",
                     "indentation contains a tab; use 4 spaces")
            )
        if line.strip() and line.rstrip(" \t\x0c") != line:
            findings.append(item(path, number, "W291", "trailing whitespace"))
        if line and not line.strip(" \t\x0c"):
            findings.append(
                item(path, number, "W293", "blank line contains whitespace")
            )
        if len(line) > limit and not is_lone_chunk(
            line, limit, number in multiline
        ):
            findings.append(
                item(path, number, "E501",
                     f"line is {len(line)} chars; limit is {limit}")
            )
    return findings


# ----------------------------------------------------------------------
# Tokens
# ----------------------------------------------------------------------


def logical_lines(tokens: list[tokenize.TokenInfo]) -> list[list]:
    """Group tokens into logical lines, dropping layout-only tokens."""
    skip = {
        tokenize.NL,
        tokenize.COMMENT,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
    groups, current = [], []
    for tok in tokens:
        if tok.type == tokenize.NEWLINE:
            if current:
                groups.append(current)
            current = []
        elif tok.type not in skip:
            current.append(tok)
    if current:
        groups.append(current)
    return groups


def token_findings(path: Path, text: str, doc_limit: int) -> list[dict]:
    """Check comments, indents, compound lines and doc line length."""
    findings = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return findings
    lines = text.splitlines()
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        row, col = tok.start
        before = lines[row - 1][:col]
        gap = len(before) - len(before.rstrip())
        if before.strip() and gap < 2:
            findings.append(
                item(path, row, "E261",
                     "at least two spaces required before inline comment")
            )
        elif not before.strip():
            findings.extend(doc_length(path, tok, doc_limit))
    for group in logical_lines(tokens):
        first = group[0]
        row = first.start[0]
        indent = INDENT.match(lines[row - 1]).group(1)
        if "\t" not in indent and len(indent) % 4:
            findings.append(
                item(path, row, "E111",
                     f"indent is {len(indent)}, not a multiple of 4")
            )
        if first.type == tokenize.NAME and first.string in COMPOUND_KEYWORDS:
            findings.extend(compound_colon(path, group))
        if len(group) == 1 and first.type == tokenize.STRING:
            findings.extend(doc_length(path, first, doc_limit))
    return findings


def doc_length(path: Path, tok: tokenize.TokenInfo, limit: int) -> list:
    """W505: comment or docstring lines over the doc line limit."""
    found = []
    physical = tok.line.splitlines()
    for offset, line in enumerate(physical):
        row = tok.start[0] + offset
        if row == 1 and line.startswith("#!"):
            return []
        chunks = line.split()
        lone_url = len(chunks) == 1 and offset + 1 < len(physical)
        if tok.type == tokenize.COMMENT:
            lone_url = len(chunks) == 2
        if lone_url and len(line) - len(chunks[-1]) < 72:
            continue
        if len(line) > limit:
            found.append(
                item(path, row, "W505",
                     f"doc line is {len(line)} chars; limit is {limit}")
            )
    return found


def compound_colon(path: Path, group: list) -> list[dict]:
    """E701: body on the same line as a compound statement header.

    One-line ``def`` bodies are E704, which pycodestyle ignores by
    default, so they are skipped here as well.
    """
    if group[0].string in ("def", "async"):
        return []
    depth = 0
    for index, tok in enumerate(group):
        if tok.type == tokenize.OP and tok.string in "([{":
            depth += 1
        elif tok.type == tokenize.OP and tok.string in ")]}":
            depth -= 1
        elif tok.type == tokenize.OP and tok.string == ":" and depth == 0:
            if index + 1 < len(group):
                return [
                    item(path, tok.start[0], "E701",
                         "multiple statements on one line (colon)")
                ]
            return []
    return []


# ----------------------------------------------------------------------
# Syntax tree: imports, comparisons, blank lines
# ----------------------------------------------------------------------


def ast_findings(path: Path, tree: ast.Module, text: str) -> list[dict]:
    """Run every check that needs the parsed syntax tree."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                findings.append(
                    item(path, node.lineno, "F403",
                         "wildcard import; import names explicitly")
                )
        elif isinstance(node, ast.Import) and len(node.names) > 1:
            findings.append(
                item(path, node.lineno, "E401",
                     "multiple imports on one line")
            )
        elif isinstance(node, ast.Compare):
            findings.extend(compare_findings(path, node))
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(
                item(path, node.lineno, "E722",
                     "bare 'except:'; name the exception")
            )
    findings.extend(imports_not_at_top(path, tree))
    findings.extend(import_groups(path, tree))
    findings.extend(naming_findings(path, tree))
    findings.extend(docstring_findings(path, tree, text))
    return findings


def is_singleton(node: ast.AST, values: tuple) -> bool:
    """Return True when node is the literal None, True or False."""
    return isinstance(node, ast.Constant) and any(
        node.value is value for value in values
    )


def compare_findings(path: Path, node: ast.Compare) -> list[dict]:
    """E711 / E712 on either side of == or !=."""
    found = []
    left = node.left
    for op, right in zip(node.ops, node.comparators):
        if isinstance(op, (ast.Eq, ast.NotEq)):
            if is_singleton(left, (None,)) or is_singleton(right, (None,)):
                found.append(
                    item(path, node.lineno, "E711",
                         "compare to None with 'is' or 'is not'")
                )
            elif is_singleton(left, (True, False)) or is_singleton(
                right, (True, False)
            ):
                found.append(
                    item(path, node.lineno, "E712",
                         "do not compare to True or False with ==")
                )
        left = right
    return found


def imports_not_at_top(path: Path, tree: ast.Module) -> list[dict]:
    """E402: module-level import after other code."""
    found = []
    seen_code = False
    for index, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if seen_code:
                found.append(
                    item(path, node.lineno, "E402",
                         "module level import not at top of file")
                )
            continue
        is_docstring = (
            index == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        is_dunder = isinstance(node, ast.Assign) and all(
            isinstance(t, ast.Name) and DUNDER.match(t.id)
            for t in node.targets
        )
        guard = isinstance(node, IMPORT_GUARDS)
        if not (is_docstring or is_dunder or guard):
            seen_code = True
    return found


def import_groups(path: Path, tree: ast.Module) -> list[dict]:
    """I001: stdlib, then third party, then local imports."""
    stdlib = getattr(sys, "stdlib_module_names", STDLIB_FALLBACK)
    imports = [
        n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
    ]
    last = -1
    for node in imports:
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            root = (node.module or "").split(".")[0]
            rank = 2 if node.level or not root else None
        else:
            root = node.names[0].name.split(".")[0]
            rank = None
        if rank is None:
            rank = 0 if root in stdlib else 1
        if rank < last:
            return [
                item(path, node.lineno, "I001",
                     "import out of order; stdlib, third party, then local")
            ]
        last = rank
    return []


# ----------------------------------------------------------------------
# Logical lines (ports of pycodestyle checks)
# ----------------------------------------------------------------------


def expand_indent(line: str) -> int:
    """Return the indentation width; tabs expand to multiples of 8."""
    line = line.rstrip("\n\r")
    if "\t" not in line:
        return len(line) - len(line.lstrip())
    result = 0
    for char in line:
        if char == "\t":
            result = result // 8 * 8 + 8
        elif char == " ":
            result += 1
        else:
            break
    return result


def mute_string(text: str) -> str:
    """Replace string contents with x's so syntax inside is ignored."""
    start = text.index(text[-1]) + 1
    end = len(text) - 1
    if text[-3:] in ('"""', "'''"):
        start += 2
        end -= 2
    return text[:start] + "x" * (end - start) + text[end:]


def build_logical_line(tokens: list, lines: list[str]) -> tuple:
    """Join a logical line's tokens into one string (pycodestyle style).

    Return (logical line, start position); the position is None when
    the tokens hold no code or comment.
    """
    logical: list[str] = []
    first = None
    prev_row = prev_col = None
    for tok in tokens:
        if tok.type in SKIP_TOKENS:
            continue
        if first is None:
            first = tok.start
        if tok.type == tokenize.COMMENT:
            continue
        text, end = tok.string, tok.end
        if tok.type == tokenize.STRING:
            text = mute_string(text)
        elif tok.type in STRING_MIDDLE:
            braces = text.count("{") + text.count("}")
            text = "x" * (len(text) + braces)
            end = (end[0], end[1] + braces)
        if prev_row:
            start_row, start_col = tok.start
            if prev_row != start_row:
                prev_line = lines[prev_row - 1]
                prev_text = prev_line[prev_col - 1:prev_col]
                if prev_text == "," or (
                    prev_text not in "{[(" and text not in "}])"
                ):
                    text = " " + text
            elif prev_col != start_col:
                text = tok.line[prev_col:start_col] + text
        logical.append(text)
        prev_row, prev_col = end
    return "".join(logical), first


def logical_findings(path: Path, text: str) -> list[dict]:
    """Drive the logical-line checks over the token stream."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return []
    lines = text.splitlines(True)
    state = {
        "blank_lines": 0,
        "blank_before": 0,
        "previous_logical": "",
        "previous_indent_level": 0,
        "previous_unindented": "",
    }
    findings: list[dict] = []
    parens = 0
    current: list = []
    for tok in tokens:
        if tok.start[0] > len(lines):
            break  # ENDMARKER and trailing DEDENTs sit past the last line
        current.append(tok)
        if tok.type == tokenize.OP:
            if tok.string in "([{":
                parens += 1
            elif tok.string in "}])":
                parens -= 1
        elif not parens and tok.type in (tokenize.NEWLINE, tokenize.NL):
            if tok.type == tokenize.NEWLINE:
                findings.extend(check_logical(path, current, lines, state))
                state["blank_before"] = 0
            elif len(current) == 1:
                state["blank_lines"] += 1
            else:
                findings.extend(check_logical(path, current, lines, state))
            current = []
    if current:
        findings.extend(check_logical(path, current, lines, state))
    return findings


def check_logical(path: Path, tokens: list, lines: list[str], state: dict):
    """Run the per-logical-line checks and update the running state."""
    logical, first = build_logical_line(tokens, lines)
    if first is None:
        return []
    start_row, start_col = first
    indent_level = expand_indent(lines[start_row - 1][:start_col])
    if state["blank_before"] < state["blank_lines"]:
        state["blank_before"] = state["blank_lines"]
    line_number = min(tokens[-1].end[0], len(lines))
    found = blank_lines_check(
        path, logical, indent_level, line_number, lines, state, start_row
    )
    found.extend(whitespace_check(path, tokens))
    found.extend(ambiguous_check(path, tokens))
    found.extend(statement_checks(path, logical, tokens, start_row))
    if logical:
        state["previous_indent_level"] = indent_level
        state["previous_logical"] = logical
        if not indent_level:
            state["previous_unindented"] = logical
    state["blank_lines"] = 0
    return found


def is_one_liner(logical: str, indent_level: int, lines, line_number) -> bool:
    """Return True for a one-line def in a group of one-liners."""
    if not TOP_LEVEL_RE.match(logical):
        return False
    line_idx = line_number - 1
    prev_indent = expand_indent(lines[line_idx - 1]) if line_idx >= 1 else 0
    if prev_indent > indent_level:
        return False
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line.startswith("@") and TOP_LEVEL_RE.match(line):
            break
        line_idx += 1
    else:
        return False
    next_idx = line_idx + 1
    while next_idx < len(lines):
        if lines[next_idx].strip():
            break
        next_idx += 1
    else:
        return True
    return expand_indent(lines[next_idx]) <= indent_level


def blank_lines_check(
    path: Path, logical: str, indent_level: int, line_number: int,
    lines: list[str], state: dict, row: int,
) -> list[dict]:
    """E301-E306: blank lines around definitions and decorators."""
    blank_lines = state["blank_lines"]
    blank_before = state["blank_before"]
    previous = state["previous_logical"]
    if not previous and blank_before < 2:
        return []
    if previous.startswith("@"):
        if blank_lines:
            return [
                item(path, row, "E304",
                     "blank lines found after function decorator")
            ]
        return []
    if blank_lines > 2 or (indent_level and blank_lines == 2):
        return [
            item(path, row, "E303", f"too many blank lines ({blank_lines})")
        ]
    if TOP_LEVEL_RE.match(logical):
        if blank_before == 0 and is_one_liner(
            logical, indent_level, lines, line_number
        ):
            return []
        if indent_level:
            if (
                blank_before == 1
                or state["previous_indent_level"] < indent_level
                or DOCSTRING_RE.match(previous)
            ):
                return []
            ancestor_level = indent_level
            nested = None
            for line in lines[line_number - 2::-1]:
                if line.strip() and expand_indent(line) < ancestor_level:
                    ancestor_level = expand_indent(line)
                    nested = DEF_RE.match(line.lstrip())
                    if nested or ancestor_level == 0:
                        break
            if nested:
                return [
                    item(path, row, "E306",
                         "expected 1 blank line before a nested "
                         "definition, found 0")
                ]
            return [item(path, row, "E301", "expected 1 blank line, found 0")]
        if blank_before != 2:
            return [
                item(path, row, "E302",
                     f"expected 2 blank lines, found {blank_before}")
            ]
        return []
    if (
        logical
        and not indent_level
        and blank_before != 2
        and state["previous_unindented"].startswith(("def ", "class "))
    ):
        return [
            item(path, row, "E305",
                 f"expected 2 blank lines after class or function "
                 f"definition, found {blank_before}")
        ]
    return []


def whitespace_check(path: Path, tokens: list) -> list[dict]:
    """E225, E227, E228, E231: whitespace around operators and commas.

    E226 (arithmetic operators without spaces) is skipped because
    flake8 ignores it by default and PEP 8 allows ``x*x + y*y``.
    """
    found = []
    need_space: object = False
    prev_type = tokenize.OP
    prev_text = prev_end = None
    brace_stack: list[str] = []
    for tok in tokens:
        token_type, text, start, end, line = tok
        if token_type == tokenize.OP and text in {"[", "(", "{"}:
            brace_stack.append(text)
        elif token_type == FSTRING_START:
            brace_stack.append("f")
        elif token_type == TSTRING_START:
            brace_stack.append("t")
        elif token_type == tokenize.NAME and text == "lambda":
            brace_stack.append("l")
        elif brace_stack:
            if token_type == tokenize.OP and text in {"]", ")", "}"}:
                brace_stack.pop()
            elif token_type in (FSTRING_END, TSTRING_END):
                brace_stack.pop()
            elif (
                brace_stack[-1] == "l"
                and token_type == tokenize.OP
                and text == ":"
            ):
                brace_stack.pop()
        if token_type in SKIP_COMMENTS:
            continue
        if token_type == tokenize.OP and text in {",", ";", ":"}:
            next_char = line[end[1]:end[1] + 1]
            if next_char not in {" ", "\t", "\xa0"} and (
                next_char not in "\r\n"
            ):
                if text == ":" and brace_stack[-1:] == ["["]:
                    pass
                elif text == ":" and brace_stack[-2:] in (
                    ["f", "{"], ["t", "{"]
                ):
                    pass
                elif text == "," and next_char in ")]":
                    pass
                else:
                    found.append(
                        item(path, start[0], "E231",
                             f"missing whitespace after '{text}'")
                    )
        if need_space:
            if start != prev_end:
                if need_space is not True and not need_space[1]:
                    found.append(
                        item(path, need_space[0][0], "E225",
                             "missing whitespace around operator")
                    )
                need_space = False
            elif (prev_text == "/" and text in {",", ")", ":"}) or (
                prev_text == ")" and text == ":"
            ):
                pass
            else:
                if need_space is True or need_space[1]:
                    found.append(
                        item(path, prev_end[0], "E225",
                             "missing whitespace around operator")
                    )
                elif prev_text != "**":
                    if prev_text == "%":
                        found.append(
                            item(path, need_space[0][0], "E228",
                                 "missing whitespace around modulo "
                                 "operator")
                        )
                    elif prev_text not in ARITHMETIC:
                        found.append(
                            item(path, need_space[0][0], "E227",
                                 "missing whitespace around bitwise or "
                                 "shift operator")
                        )
                need_space = False
        elif (
            token_type in (tokenize.OP, tokenize.NAME)
            and prev_end is not None
        ):
            if text == "=" and (
                brace_stack[-1:] in (["l"], ["("])
                or brace_stack[-2:] in (["f", "{"], ["t", "{"])
            ):
                pass
            elif text in WS_NEEDED:
                need_space = True
            elif text in UNARY:
                if (prev_type == tokenize.OP and prev_text in "}])") or (
                    prev_type != tokenize.OP
                    and prev_text not in KEYWORDS
                    and not is_soft_keyword(prev_text)
                ):
                    need_space = None
            elif text in WS_OPTIONAL:
                need_space = None
            if need_space is None:
                need_space = (prev_end, start != prev_end)
            elif need_space and start == prev_end:
                found.append(
                    item(path, prev_end[0], "E225",
                         "missing whitespace around operator")
                )
                need_space = False
        prev_type = token_type
        prev_text = text
        prev_end = end
    return found


def ambiguous_check(path: Path, tokens: list) -> list[dict]:
    """E741-E743: names l, O and I that look like digits."""
    found = []
    func_depth = None
    seen_colon = False
    brace_depth = 0
    prev_text = tokens[0].string
    prev_start = tokens[0].start
    for index in range(1, len(tokens)):
        token_type, text, start, end, line = tokens[index]
        ident = pos = None
        if prev_text in {"def", "lambda"}:
            func_depth = brace_depth
            seen_colon = False
        elif (
            func_depth is not None
            and text == ":"
            and brace_depth == func_depth
        ):
            seen_colon = True
        if text and text in "([{":
            brace_depth += 1
        elif text and text in ")]}":
            brace_depth -= 1
        if text == ":=" or (text == "=" and brace_depth == 0):
            if prev_text in AMBIGUOUS:
                ident, pos = prev_text, prev_start
        if prev_text in ("as", "for", "global", "nonlocal"):
            if text in AMBIGUOUS:
                ident, pos = text, start
        if (
            func_depth is not None
            and not seen_colon
            and index < len(tokens) - 1
            and tokens[index + 1].string in ":,=)"
            and prev_text in {"lambda", ",", "*", "**", "("}
            and text in AMBIGUOUS
        ):
            ident, pos = text, start
        if prev_text == "class" and text in AMBIGUOUS:
            found.append(
                item(path, start[0], "E742",
                     f"ambiguous class definition '{text}'")
            )
        if prev_text == "def" and text in AMBIGUOUS:
            found.append(
                item(path, start[0], "E743",
                     f"ambiguous function definition '{text}'")
            )
        if ident:
            found.append(
                item(path, pos[0], "E741",
                     f"ambiguous variable name '{ident}'")
            )
        prev_text = text
        prev_start = start
    return found


def statement_checks(path: Path, logical: str, tokens: list, row: int):
    """E731 lambda assignment; E702/E703 semicolons."""
    found = []
    last_char = len(logical) - 1
    colon = logical.find(":")
    prev_found = 0
    counts = {char: 0 for char in "{}[]()"}
    while -1 < colon < last_char:
        for char in logical[prev_found:colon]:
            if char in counts:
                counts[char] += 1
        if (
            counts["{"] <= counts["}"]
            and counts["["] <= counts["]"]
            and counts["("] <= counts[")"]
            and logical[colon + 1] != "="
        ):
            lambda_kw = LAMBDA_RE.search(logical, 0, colon)
            if lambda_kw:
                before = logical[: lambda_kw.start()].rstrip()
                if before[-1:] == "=" and before[:-1].strip().isidentifier():
                    found.append(
                        item(path, row, "E731",
                             "do not assign a lambda expression, use a def")
                    )
                break
        prev_found = colon
        colon = logical.find(":", colon + 1)
    code_tokens = [t for t in tokens if t.type not in SKIP_COMMENTS]
    for index, tok in enumerate(code_tokens):
        if tok.type == tokenize.OP and tok.string == ";":
            if index == len(code_tokens) - 1:
                found.append(
                    item(path, tok.start[0], "E703",
                         "statement ends with a semicolon")
                )
            else:
                found.append(
                    item(path, tok.start[0], "E702",
                         "multiple statements on one line (semicolon)")
                )
    return found


# ----------------------------------------------------------------------
# Naming (pep8-naming semantics)
# ----------------------------------------------------------------------


def class_functions(node: ast.AST):
    """Yield functions defined in a class body, through if/try/with."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, NAMING_CONTAINERS):
            yield from class_functions(child)
        elif isinstance(child, FUNC_NODES):
            yield child


def method_kinds(tree: ast.Module) -> dict:
    """Map each method to 'method', 'classmethod' or 'staticmethod'."""
    kinds = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
        bases |= {b.attr for b in node.bases if isinstance(b, ast.Attribute)}
        metaclass = bool(bases & METACLASS_BASES)
        late = {}
        for child in ast.iter_child_nodes(node):
            if (
                isinstance(child, ast.Assign)
                and isinstance(child.value, ast.Call)
                and isinstance(child.value.func, ast.Name)
                and child.value.func.id in ("classmethod", "staticmethod")
                and len(child.value.args) == 1
                and isinstance(child.value.args[0], ast.Name)
            ):
                late[child.value.args[0].id] = child.value.func.id
        for func in class_functions(node):
            kind = "method"
            if func.name in CLASS_METHODS or metaclass:
                kind = "classmethod"
            if func.name in late:
                kind = late[func.name]
            else:
                for decorator in func.decorator_list:
                    name = decorator_name(decorator)
                    if name in ("classmethod", "staticmethod"):
                        kind = name
                        break
            kinds[func] = kind
    return kinds


def global_names(func: ast.AST) -> set[str]:
    """Return names declared ``global`` inside ``func``."""
    names = set()
    stack = list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Global):
            names.update(node.names)
        if not isinstance(node, DEF_NODES):
            stack.extend(ast.iter_child_nodes(node))
    return names


def extract_names(target: ast.AST):
    """Yield the plain names bound by an assignment target."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            if isinstance(element, ast.Starred):
                yield from extract_names(element.value)
            else:
                yield from extract_names(element)
    elif isinstance(target, ast.ExceptHandler) and target.name:
        yield target.name


def is_namedtuple_call(node: ast.AST) -> bool:
    """Return True for ``namedtuple(...)`` calls, which make classes."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(
        func, "id", None
    )
    return name == "namedtuple"


def naming_findings(path: Path, tree: ast.Module) -> list[dict]:
    """N801-N806, N815, N816, N818: class, function, variable names."""
    findings = []
    kinds = method_kinds(tree)
    for node, parents in iter_nodes(tree, (tree,)):
        if isinstance(node, ast.ClassDef):
            findings.extend(class_name_findings(path, node, parents))
        elif isinstance(node, FUNC_NODES):
            findings.extend(function_name_findings(path, node, kinds))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            if is_namedtuple_call(node.value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [
                node.target
            ]
            for target in targets:
                findings.extend(variable_findings(path, target, parents))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            findings.extend(variable_findings(path, node.target, parents))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for entry in node.items:
                if entry.optional_vars is not None:
                    findings.extend(
                        variable_findings(path, entry.optional_vars, parents)
                    )
        elif isinstance(node, ast.ExceptHandler) and node.name:
            findings.extend(variable_findings(path, node, parents))
        elif isinstance(
            node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            for generator in node.generators:
                findings.extend(
                    variable_findings(path, generator.target, parents)
                )
    return findings


def superclass_names(name: str, parents: tuple, seen=None) -> set[str]:
    """Collect base-class names reachable in the same module."""
    seen = seen if seen is not None else set()
    for parent in parents:
        for node in getattr(parent, "body", []):
            if isinstance(node, ast.ClassDef) and node.name == name:
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id not in seen:
                        seen.add(base.id)
                        superclass_names(base.id, parents, seen)
                return seen
    return seen


def class_name_findings(path: Path, node: ast.ClassDef, parents) -> list:
    """N801 CapWords class names, N818 Error suffix on exceptions."""
    if node.name in NAMING_IGNORE:
        return []
    found = []
    bare = node.name.strip("_")
    if bare and (not bare[0].isupper() or "_" in bare):
        found.append(
            item(path, node.lineno, "N801",
                 f"class {node.name} should be CapWords")
        )
    if "Exception" in superclass_names(node.name, parents) and (
        not bare.endswith("Error")
    ):
        found.append(
            item(path, node.lineno, "N818",
                 f"exception {node.name} should end with 'Error'")
        )
    return found


def function_name_findings(path: Path, node: ast.AST, kinds: dict) -> list:
    """N802 snake_case, N803 argument names, N804/N805 self and cls."""
    found = []
    name = node.name
    if name not in NAMING_IGNORE and name != name.lower() and not (
        DUNDER.match(name)
    ):
        found.append(
            item(path, node.lineno, "N802",
                 f"function {name} should be snake_case")
        )
    args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    kind = kinds.get(node)
    if args and args[0].arg not in NAMING_IGNORE:
        first = args[0].arg
        if kind == "method" and first != "self":
            found.append(
                item(path, args[0].lineno, "N805",
                     "first argument of a method should be named 'self'")
            )
        elif kind == "classmethod" and first != "cls":
            found.append(
                item(path, args[0].lineno, "N804",
                     "first argument of a classmethod should be 'cls'")
            )
    for extra in (node.args.vararg, node.args.kwarg):
        if extra is not None:
            args.append(extra)
    for arg in args:
        if arg.arg.lower() != arg.arg and arg.arg not in NAMING_IGNORE:
            found.append(
                item(path, arg.lineno, "N803",
                     f"argument {arg.arg} should be lowercase")
            )
    return found


def variable_findings(path: Path, target: ast.AST, parents) -> list:
    """N806 / N815 / N816: variable names by scope."""
    scope = None
    for parent in reversed(parents):
        if isinstance(parent, (ast.ClassDef,) + FUNC_NODES):
            scope = parent
            break
    found = []
    for name in extract_names(target):
        if name in NAMING_IGNORE:
            continue
        if isinstance(scope, ast.ClassDef):
            if is_mixed_case(name):
                found.append(
                    item(path, target.lineno, "N815",
                         f"variable {name} in class scope should not "
                         f"be mixedCase")
                )
        elif scope is None:
            if is_mixed_case(name):
                found.append(
                    item(path, target.lineno, "N816",
                         f"variable {name} in global scope should not "
                         f"be mixedCase")
                )
        elif name.lower() != name and name not in global_names(scope):
            found.append(
                item(path, target.lineno, "N806",
                     f"variable {name} in function should be lowercase")
            )
    return found


# ----------------------------------------------------------------------
# Docstrings (PEP 257 via pydocstyle's pep257 convention)
# ----------------------------------------------------------------------


def docstring_node(node: ast.AST) -> ast.Constant | None:
    """Return the docstring constant of a module, class or function."""
    body = getattr(node, "body", [])
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value
    return None


def dunder_all(tree: ast.Module) -> set[str] | None:
    """Return the names listed in a literal ``__all__``, else None."""
    names: set[str] | None = None
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets, value = [node.target], node.value
        if not any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in targets
        ):
            continue
        if not isinstance(value, (ast.List, ast.Tuple)) or not all(
            isinstance(e, ast.Constant) and isinstance(e.value, str)
            for e in value.elts
        ):
            return None
        listed = {e.value for e in value.elts}
        names = listed if names is None else names | listed
    return names


def module_is_public(path: Path) -> bool:
    """Return True unless the module or a parent package is private."""
    for part in path.with_suffix("").parts:
        if part.startswith("_") and not DUNDER.match(part):
            return False
    return True


def main_only_script(tree: ast.Module) -> bool:
    """Return True when a module only imports and runs ``__main__``."""
    has_main = False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.If) and "__main__" in ast.dump(node.test):
            has_main = True
            continue
        return False
    return has_main


def body_definitions(node: ast.AST):
    """Yield definitions in a body, looking through if/try/with/for."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, DOC_CONTAINERS):
            yield from body_definitions(child)
        elif isinstance(child, DEF_NODES):
            yield child


def docstring_findings(path: Path, tree: ast.Module, text: str) -> list:
    """D1xx missing docstrings and D2xx-D4xx docstring form."""
    findings = []
    lines = text.splitlines()
    exported = dunder_all(tree)
    doc = docstring_node(tree)
    if doc is None:
        if module_is_public(path) and not main_only_script(tree):
            package = path.name == "__init__.py"
            findings.append(
                item(path, 1, "D104" if package else "D100",
                     "missing docstring in public "
                     + ("package" if package else "module"))
            )
    else:
        findings.extend(docstring_form(path, doc, lines, None))

    def is_exported(name: str) -> bool:
        if exported is not None:
            return name in exported
        return not name.startswith("_")

    def visit(node: ast.AST, public: bool, in_class: bool) -> None:
        doc = docstring_node(node)
        is_class = isinstance(node, ast.ClassDef)
        if doc is None and public:
            findings.extend(missing_docstring(path, node, in_class))
        elif doc is not None:
            findings.extend(
                docstring_form(path, doc, lines, None if is_class else node)
            )
        for child in body_definitions(node):
            child_public = public and child_is_public(child, is_class)
            visit(child, child_public, is_class)

    for node in body_definitions(tree):
        visit(node, is_exported(node.name), False)
    return findings


def child_is_public(node: ast.AST, in_class: bool) -> bool:
    """Decide whether a nested definition counts as public."""
    if not in_class:
        return False
    name = node.name
    if isinstance(node, ast.ClassDef):
        return not name.startswith("_")
    for decorator in node.decorator_list:
        if (
            isinstance(decorator, ast.Attribute)
            and isinstance(decorator.value, ast.Name)
            and decorator.value.id == name
        ):
            return False
    return not name.startswith("_") or name in VARIADIC_MAGIC or bool(
        DUNDER.match(name)
    )


def missing_docstring(path: Path, node: ast.AST, in_class: bool) -> list:
    """D101-D107 for a public definition without a docstring."""
    name = node.name
    decorators = {decorator_name(d) for d in node.decorator_list}
    if isinstance(node, ast.ClassDef):
        code = "D106" if in_class else "D101"
        what = "public nested class" if in_class else "public class"
    elif in_class and name == "__init__":
        code, what = "D107", "__init__"
    elif in_class and DUNDER.match(name) and name not in VARIADIC_MAGIC:
        code, what = "D105", "magic method"
    elif "overload" in decorators:
        return []
    elif not in_class:
        code, what = "D103", "public function"
    else:
        code, what = "D102", "public method"
    return [item(path, node.lineno, code, f"missing docstring in {what}")]


def docstring_form(
    path: Path, doc: ast.Constant, lines: list[str], func: ast.AST | None
) -> list[dict]:
    """D200-D419: shape of a docstring that exists."""
    row = doc.lineno
    value = doc.value
    raw = node_source(lines, doc)
    if not value.strip():
        return [item(path, row, "D419", "docstring is empty")]
    found = []
    opening = DOC_OPENING.match(raw)
    quotes = opening.group(1) if opening else '"""'
    if quotes != '"""' and not (quotes == "'''" and '"""' in value):
        found.append(
            item(path, row, "D300",
                 f'use """triple double quotes""" (found {quotes}-quotes)')
        )
    physical = value.split("\n")
    non_blank = [line for line in physical if line.strip()]
    if len(physical) > 1 and len(non_blank) == 1:
        found.append(
            item(path, row, "D200",
                 "one-line docstring should fit on one line with quotes")
        )
    stripped = value.strip().split("\n")
    if len(stripped) > 1:
        blanks = 0
        for line in stripped[1:]:
            if line.strip():
                break
            blanks += 1
        if blanks != 1:
            found.append(
                item(path, row, "D205",
                     f"1 blank line required between summary line and "
                     f"description (found {blanks})")
            )
    if len(non_blank) > 1 and raw.split("\n")[-1].strip() not in (
        '"""', "'''"
    ):
        found.append(
            item(path, row, "D209",
                 "multi-line docstring closing quotes should be on a "
                 "separate line")
        )
    summary = stripped[0].strip()
    if not summary.endswith("."):
        found.append(
            item(path, row, "D400",
                 f"first line should end with a period (not '{summary[-1]}')")
        )
    if func is not None and not is_test_or_property(func):
        found.extend(imperative_mood(path, row, summary))
    return found


def is_test_or_property(func: ast.AST) -> bool:
    """Return True for test functions and properties (D401 exempt)."""
    if func.name.startswith("test") or func.name == "runTest":
        return True
    return any(
        decorator_name(d) in PROPERTY_DECORATORS for d in func.decorator_list
    )


def imperative_candidates(word: str) -> list[str]:
    """Return possible base verbs for an inflected word."""
    forms = []
    if word.endswith("ies"):
        forms.append(word[:-3] + "y")
    if word.endswith("es"):
        forms.append(word[:-2])
    if word.endswith("s"):
        forms.append(word[:-1])
    if word.endswith("ied"):
        forms.append(word[:-3] + "y")
    for suffix in ("ing", "ed"):
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            forms.extend([stem, stem + "e"])
            if len(stem) > 2 and stem[-1] == stem[-2]:
                forms.append(stem[:-1])
    return forms


def imperative_mood(path: Path, row: int, summary: str) -> list[dict]:
    """D401: first word of a function docstring must be imperative."""
    words = summary.split()
    if not words:
        return []
    first = NON_WORD.sub("", words[0])
    word = first.lower()
    if not word:
        return []
    if word in IMPERATIVE_BLACKLIST:
        return [
            item(path, row, "D401",
                 f"first line should be in imperative mood; try "
                 f"rephrasing (found '{first}')")
        ]
    if word in IMPERATIVE_VERBS:
        return []
    for base in imperative_candidates(word):
        if base in IMPERATIVE_VERBS:
            return [
                item(path, row, "D401",
                     f"first line should be in imperative mood (perhaps "
                     f"'{base.capitalize()}', not '{first}')")
            ]
    return []


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------


def review_file(path: Path, limit: int, doc_limit: int) -> list[dict]:
    """Run every check on one file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [item(path, 1, "E902", f"could not read file: {exc}")]
    findings = physical_findings(path, text, limit)
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        findings.append(
            item(path, exc.lineno or 1, "E999", f"syntax error: {exc.msg}")
        )
        return findings
    findings.extend(token_findings(path, text, doc_limit))
    findings.extend(logical_findings(path, text))
    findings.extend(ast_findings(path, tree, text))
    return findings


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, scan, print JSON and return the exit code."""
    parser = argparse.ArgumentParser(description="Mechanical PEP 8 scan")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--line-length", type=int, default=79)
    parser.add_argument(
        "--doc-length",
        type=int,
        default=72,
        help="limit for comment and docstring lines (W505)",
    )
    args = parser.parse_args(argv)
    files, missing = iter_py_files(args.paths)
    findings = [item(p, 1, "E902", "path not found") for p in missing]
    if not files:
        report = {"files": 0, "findings": findings, "error": "no Python files"}
        print(json.dumps(report, indent=2))
        return 2
    for path in files:
        findings.extend(review_file(path, args.line_length, args.doc_length))
    findings.sort(key=lambda row: (row["path"], row["line"], row["code"]))
    report = {
        "files": len(files),
        "line_length": args.line_length,
        "doc_length": args.doc_length,
        "findings": findings,
    }
    print(json.dumps(report, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
