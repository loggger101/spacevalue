# -*- coding: utf-8 -*-
"""House rules: a quiet import, ASCII output, one version written once.

Each of these has failed once somewhere in this family of repositories, which
is why they are tests and not advice. The generic rules are samebytes'
(`samebytes.source` and `samebytes.docs`), the one copy the family shares;
the ones only this package needs are written out here.
"""

import dataclasses
import os
import subprocess
import sys

from samebytes import docs, source

import spacevalue

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "spacevalue")
SOURCES = sorted(os.path.join(PKG, f) for f in os.listdir(PKG) if f.endswith(".py"))


def test_import_is_silent():
    """A library that prints when imported for one constant is a nuisance.

    Every module, because `import spacevalue` alone no longer imports any of
    them (the names resolve lazily). Run in a fresh interpreter in an empty
    directory, which must stay empty: importing creates nothing.
    """
    probe = ("import spacevalue, spacevalue.cargo, spacevalue.catalog, "
             "spacevalue.release; spacevalue.DATA_VERSION")
    assert source.quiet_import(ROOT, probe) == ([], 1)


def test_cargo_imports_neither_the_catalog_nor_spacecost():
    """A Stage 4 worker imports `spacevalue.cargo` at spawn, many times a run.

    The package's names resolve lazily for exactly this, so a lost laziness
    (one eager `from .catalog import ...` in `__init__`) shows up here and not
    as slower workers nobody times.
    """
    probe = ("import sys; sys.path.insert(0, %r); import spacevalue.cargo; "
             "print(sorted(m for m in sys.modules if m == 'spacecost' "
             "or m.startswith(('spacecost.', 'spacevalue.'))))" % ROOT)
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True,
                         text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "['spacevalue.cargo']"


def test_lazy_names_are_the_public_names():
    """`__all__` and the lazy table name the same things, so neither rots."""
    lazy = set(spacevalue._LAZY) | {"DATA_VERSION", "__version__"}
    assert sorted(lazy ^ set(spacevalue.__all__)) == []


def test_printed_strings_are_ascii():
    """Windows gives a redirected stdout cp1252: one non-ASCII byte kills it.

    Checked on every string literal passed to `say` or `print`.  Comments,
    docstrings and the `notes` data keep their characters; they are not
    printed by the progress output.
    """
    bad, n = source.printed_non_ascii(ROOT, SOURCES, callers=("say", "print"))
    assert bad == [] and n > 0


def test_no_print_outside_the_cli():
    """Library output goes through `say`; only the command line prints."""
    lib = [p for p in SOURCES if os.path.basename(p) != "cli.py"]
    assert source.calls(ROOT, lib, ["print"])[0] == []


def test_the_package_version_is_written_once():
    assert source.version_written_once(ROOT, "spacevalue") == ([], 1)


def test_the_changelog_has_this_release():
    log = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    assert ("### %s " % spacevalue.__version__) in log
    assert spacevalue.DATA_VERSION in log


def test_the_readme_names_the_current_contract():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert spacevalue.DATA_VERSION in readme


def test_internal_anchors_resolve():
    """Every `](#anchor)` and relative link in the README names something that exists."""
    bad, n = docs.links(ROOT, ["README.md"])
    assert bad == [] and n > 0


def test_git_pins_agree():
    """Every `github.com/loggger101/<repo>@<ref>` names one ref per repository.

    samebytes is pinned in pyproject's test extra and in CI's hooks job, and
    this package's own tag in two README install lines.  Both pairs had
    drifted when this test was written (the hooks job on v0.2.0 against
    v0.3.0; the live extra's install line on v0.1.0 against v0.2.0).
    CHANGELOG is left out: an old pin there is history.
    """
    files = ["pyproject.toml", ".github/workflows/tests.yml", "README.md", "CLAUDE.md",
             "CITATIONS.md"]
    bad, n = docs.pins(ROOT, files, "loggger101")
    assert bad == [] and n >= 5, "; ".join(bad)


def test_every_config_field_has_help():
    """Every `MineralValueConfig` field carries a help comment.

    Read by samebytes' `source.field_docs`, the rule economicspace's dashboard
    shows a config's comments by: the block directly above a field, to the
    first blank line, banner or bare rule, plus a trailing comment.
    """
    from spacevalue.catalog import MineralValueConfig
    fields = [f.name for f in dataclasses.fields(MineralValueConfig)]
    bad, n = source.missing_help(ROOT, "spacevalue/catalog.py", "MineralValueConfig",
                                 fields=fields)
    assert bad == [] and n == len(fields), "; ".join(bad)
