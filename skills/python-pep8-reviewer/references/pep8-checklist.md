# PEP 8 checklist

Read this on the judgment pass. PEP 8 is the style guide; PEP 257 covers docstrings. Prefer project config over the defaults below.

## Layout

| Rule | Expect |
|---|---|
| Indent | 4 spaces. No tabs. No mixed tabs and spaces. |
| Continuation | Align with the opening delimiter, or hanging indent of 4 spaces. Do not indent the continuation argument and the closing paren on the same visual column as the first argument when that hides structure. |
| Blank lines | 2 between top-level functions and classes (E302) and after them (E305). 1 between methods (E301) and before nested defs (E306). Not more than 2 anywhere, not more than 1 inside a def (E303). None after a decorator (E304). A run of one-line defs may skip them. |
| Line length | 79 code, 72 comments and docstrings, unless the project sets another limit. URLs may run long. |
| Encoding | UTF-8. No coding cookie required on Python 3. |
| File end | Single trailing newline. No trailing whitespace. |

## Imports

Group in this order, each group separated by one blank line:

1. Standard library
2. Related third party
3. Local application

- Absolute imports preferred. Explicit relative imports are fine inside a package.
- One import per line for `import os` / `import sys`. `from x import a, b` may share a line; multiline `from` imports should use parentheses and a trailing comma.
- No `from module import *` outside a republishing `__init__.py`.
- Imports at the top of the file, after the module docstring and `__future__`. Late imports only to break a cycle or to defer a heavy optional dependency — say so in a comment.

## Whitespace

- Space after commas, colons, and semicolons. Not before.
- Space around `=` in assignments and keyword-only defaults, not inside function-call keyword arguments that are already spaced as the project formatter wants. PEP 8: no spaces around `=` when used to indicate a keyword argument or a default parameter (`def f(a=1):`, `f(a=1)`).
- Space around binary operators (E225). Assignment, augmented assignment, comparisons, `->` and `:=` always need them. Arithmetic may drop spaces to show priority (`hypot2 = x*x + y*y`), but bitwise, shift and `%` operators without spaces are flagged (E227, E228).
- Space after commas, semicolons and colons (E231), except in slices, `(3,)` and f-string format specs.
- No space immediately inside parentheses, brackets, or braces.
- Slice colons: `ham[1:9]`, `ham[lower:]`, `ham[lower:upper:step]`.
- At least two spaces before an inline comment, then `# ` with a space.

## Naming

| Kind | Form | Example |
|---|---|---|
| Module / package | short, lowercase, underscores if needed | `order_total.py` |
| Class | CapWords | `OrderTotal` |
| Exception | CapWords, `Error` suffix (N818 when it subclasses `Exception`) | `OrderError` |
| Function / method / variable | snake_case (N802, N803 arguments, N806 locals) | `order_total` |
| First method argument | `self`; `cls` on classmethods, `__new__`, `__init_subclass__` and metaclass methods (N804/N805) | `def save(self):` |
| Class attribute / module variable | not mixedCase (N815/N816); UPPER_SNAKE for constants | `max_retry`, `MAX_RETRY` |
| Constant | UPPER_SNAKE | `MAX_RETRY` |
| Method that is internal | leading underscore | `_parse_row` |
| Name clash with keyword | trailing underscore | `class_` |

Do not flag dunder names, or a leading underscore used as "unused".

## Comparisons and idioms that PEP 8 calls out

- `is` / `is not` for `None`, not `==` / `!=`.
- Do not compare booleans with `== True` or `== False`. Write `if flag:` / `if not flag:`.
- `is not` as two words, never `not ... is`.
- Never name a variable `l`, `O` or `I` (E741). Do not assign a lambda to a name; write a `def` (E731). One statement per line; no trailing semicolons (E702, E703).
- Exceptions: `except ValueError:` not bare `except:`.
- Context managers for resources.

## Docstrings (PEP 257, required by PEP 8 for public modules, functions, classes, and methods)

- Triple double quotes (D300). `r"""` when the text has backslashes.
- One-line docstring fits on one line: `"""Return the total."""` (D200)
- Multi-line: summary line, blank line (D205), details, closing quotes on their own line (D209).
- Summary line ends with a period (D400). Imperative mood: "Return the total.", not "Returns the total." (D401, functions and methods only; test functions and properties are exempt).
- Public means: not starting with `_`, or listed in `__all__` when the module defines one. `__init__` needs a docstring (D107); other dunder methods are a nit (D105). `@overload` stubs and `@x.setter` methods do not need one.
- Keep docstring and comment lines to 72 characters (W505) unless the project sets another limit.

## What not to flag

- Quote style (`'` vs `"`) when no tool pins it.
- Trailing commas in multiline collections (PEP 8 allows them; formatters require them).
- Hanging indent vs aligned indent when either is readable.
- Line length inside a project that sets 88 or 100.
