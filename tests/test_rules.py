# -*- coding: utf-8 -*-
"""House rules: a quiet import, ASCII output, one version written once.

Each of these has failed once somewhere in this family of repositories, which
is why they are tests and not advice.
"""

import ast
import os
import re
import subprocess
import sys

import spacevalue

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "spacevalue")
SOURCES = sorted(os.path.join(PKG, f) for f in os.listdir(PKG) if f.endswith(".py"))


def test_import_is_silent():
    """A library that prints when imported for one constant is a nuisance."""
    out = subprocess.run([sys.executable, "-c", "import spacevalue"],
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    assert out.stdout == "" and out.stderr == ""


def test_import_creates_nothing(tmp_path):
    subprocess.run([sys.executable, "-c",
                    "import sys; sys.path.insert(0, %r); import spacevalue" % ROOT],
                   cwd=str(tmp_path), check=True)
    assert os.listdir(str(tmp_path)) == []


def test_printed_strings_are_ascii():
    """Windows gives a redirected stdout cp1252: one non-ASCII byte kills it.

    Checked on every string literal passed to `say` or `print`.  Comments,
    docstrings and the `notes` data keep their characters; they are not
    printed by the progress output.
    """
    bad = []
    for path in SOURCES:
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("say", "print")):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        if any(ord(c) > 127 for c in sub.value):
                            bad.append((os.path.basename(path), sub.lineno))
    assert not bad


def test_no_print_outside_the_cli():
    for path in SOURCES:
        if os.path.basename(path) == "cli.py":
            continue
        tree = ast.parse(open(path, encoding="utf-8").read())
        calls = [n.lineno for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "print"]
        assert not calls, (os.path.basename(path), calls)


def test_the_package_version_is_written_once():
    text = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    assert 'dynamic = ["version"]' in text
    assert 'version = { attr = "spacevalue.__version__" }' in text
    assert re.search(r'^version\s*=\s*"', text, re.M) is None


def test_the_changelog_has_this_release():
    log = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    assert ("### %s " % spacevalue.__version__) in log
    assert spacevalue.DATA_VERSION in log


def test_the_readme_names_the_current_contract():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert spacevalue.DATA_VERSION in readme


def test_internal_anchors_resolve():
    """Every `](#anchor)` in the README names a heading that exists."""
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    heads = {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
             for h in re.findall(r"^#+ (.+)$", text, re.M)}
    links = set(re.findall(r"\]\(#([^)]+)\)", text))
    assert sorted(links - heads) == []
