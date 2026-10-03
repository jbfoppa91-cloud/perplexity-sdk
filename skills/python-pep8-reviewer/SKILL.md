---
name: python-pep8-reviewer
description: "Review Python code against PEP 8 and report concrete fixes. Use when asked to review, lint, or check Python style, formatting, naming, imports, whitespace, docstrings, or PEP 8 compliance."
type: workflow
lifecycle: active
---

# Python PEP 8 Reviewer

Review Python against PEP 8 (style guide for code, not correctness). Prefer a project's configured formatter and line length over the PEP 8 defaults when those files exist.

## Workflow

1. **Scope.** Review the files or diff the user named. If none are named, review changed `.py` files, else the package under the working directory. Skip `venv/`, `.venv/`, `site-packages/`, and generated files.
2. **Overrides.** Read `pyproject.toml`, `setup.cfg`, `tox.ini`, `.flake8`, and `ruff.toml` before flagging length or quote style. Record the effective line length. Default is 79 for code and 72 for comments and docstrings.
3. **Mechanical pass.** Run `python3 scripts/pep8_review.py <paths>` from this skill directory. Pass `--line-length N` when the project sets one and `--doc-length N` if it sets a comment/docstring limit (default 72). Exit code 0 means no findings, 1 means findings, 2 means no Python files were found. Codes follow pycodestyle (E/W), pyflakes (`F403`), pep8-naming (`N8xx`) and pydocstyle's pep257 convention (`D1xx`-`D4xx`); `I001` is the script's own import-group check. Treat script output as the finding list, not as a final verdict. The script does not score quote style, hanging-indent style, continuation-line indents (E12x), operator spacing (E22x), import aliases (N811-N814) or docstring sections; cover those in the judgment pass. `D401` (imperative mood) is a word-list heuristic: confirm before reporting it.
4. **Judgment pass.** Read the same files for issues the script does not score. Use `references/pep8-checklist.md`. Do not restyle code that already matches Black, Ruff format, or an explicit project formatter unless the user asked for strict PEP 8.
5. **Report.** Group findings by file. Lead with must-fix PEP 8 breaks, then nits. Every finding needs a location, the rule, and a corrected snippet.

## Severity

| Level | Use for |
|---|---|
| Must-fix | Tabs, mixed indent (E101/W191), broken import grouping, wildcard imports (F403), multiple imports on one line (E401), `== None` / `== True` (E711/E712), bare `except:` (E722), naming that violates PEP 8 (N801-N806, N815, N816, N818), missing two blank lines between top-level defs (E302) |
| Should-fix | Line length over the effective limit (E501), trailing whitespace, inline-comment spacing, imports below code (E402), missing docstring on a public module, class, function or method (D100-D104, D107), docstring form: quotes, summary line, period (D200-D400) |
| Nit | Extra blank lines, trailing commas already valid, quote style when the project does not pin one, missing docstring on a magic method (D105), imperative mood (D401), doc lines over 72 (W505) |

## Report format

```markdown
# PEP 8 review — <scope>

Config: line length <N> (source: pyproject.toml | PEP 8 default). Formatter: <black|ruff|none>.

## path/to/file.py
- L12 [must-fix] E711: comparison to None should be `is` / `is not`.
  ```python
  if value is None:
  ```
- L40 [should-fix] E501: line is 96 chars; limit is 79.

## Summary
- N must-fix, N should-fix, N nits
- Not reviewed: tests of runtime behavior, type errors, security
```

If the tree is clean, say so and name the config you applied. Do not invent findings.

## Rules that override PEP 8 defaults

- A configured `line-length` or `max-line-length` wins over 79.
- If Black or Ruff format is the project formatter, do not flag hanging-indent style, quote style, or trailing commas that the formatter owns. Still flag naming, import cycles of concern, `== None`, and wildcard imports.
- PEP 8 allows aligning with the opening delimiter or a hanging indent. Accept either.
- Do not demand a module docstring on a script whose only job is `if __name__ == "__main__"` (the script already skips D100 there).
- Single-letter names are acceptable in comprehensions and math, not in public functions.

## Out of scope

Do not review type-checker errors, algorithmic bugs, or test coverage unless the user also asked for a general code review. Say that those were skipped.

## Resources

- Checklist and examples: `references/pep8-checklist.md`
- Mechanical scan: `scripts/pep8_review.py`
- Tests: `python3 -m pytest tests` from this directory. Fixture files under `tests/fixtures/` are cross-checked against flake8 with pep8-naming and flake8-docstrings when those are installed.
