# Changelog
## 2026-10-02
- Initial skill creation: PEP 8 review workflow, checklist, and mechanical scanner.
- Scanner fixes after testing against flake8:
  - E712 no longer flags `== 0`, `== 1` or `== 1.0` (identity check for True/False).
  - E261 uses real comment tokens, so `#` inside strings is ignored.
  - E111 only checks the first line of each logical line; aligned continuations and string contents are accepted.
  - N801 accepts private classes such as `_Private`; N802 accepts unittest names such as `setUp`.
  - E711/E712 check both sides of the comparison.
  - New checks: E101 mixed indent, E401 multiple imports, E402 late import, E701 compound statement on one line, E722 bare except.
  - E302 counts from the first decorator, ignores comment lines in the gap, and applies after imports and other statements.
  - Wildcard imports reported as F403 (was E401). Missing paths reported as E902.
  - Long lone URLs (including in comments) are exempt from E501, matching pycodestyle.
  - Exit codes: 0 no findings, 1 findings, 2 no Python files.
  - Script itself passes flake8 and its own scan.
- Files arranged in the layout SKILL.md expects: scripts/ and references/.

## 2026-10-03
- Docstring checks added (pydocstyle pep257 semantics): D100-D107 missing docstrings with `__all__`, overload, setter, nested-scope and private-package handling; D200, D205, D209, D300, D400, D419 docstring form; D401 imperative mood from pydocstyle's verb and blacklist word lists.
- Naming checks added (pep8-naming semantics): N803 argument names, N804/N805 `cls`/`self` including metaclasses, implicit classmethods and `name = staticmethod(name)`; N806 locals; N815/N816 mixedCase class and module variables; N818 `Error` suffix.
- W505 doc line length for comment-only lines and docstrings, with `--doc-length` (default 72).
- E501 now matches pycodestyle: lone long chunks are exempt only inside multi-line strings; `# <url>` comments stay exempt.
- One-line `def` bodies are no longer E701 (pycodestyle reports E704 and ignores it by default).
- Definitions inside `try`/`except`/`if` at module or class level are found for docstring and naming checks.
- Test suite: `tests/test_pep8_review.py` (43 tests) with fixtures cross-checked against flake8 + pep8-naming + flake8-docstrings.
- Verified on real projects: `perplexity-sdk` (11 files) and `psf/requests` (34 files, 1,308 shared findings) with zero disagreements against flake8 on every implemented code.
- Runs on Python 3.8+: `ast.Match` guarded, stdlib fallback list for Python < 3.10 (which lacks `sys.stdlib_module_names`). Test suite verified on 3.8, 3.10, 3.12 and 3.14.
