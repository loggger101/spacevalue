# rust/: the cargo knapsack in Rust (prototype)

**Status:** a prototype on branch `rust-cargo-prototype`. Not merged, not
released, and nothing in `spacevalue` imports it. The Python in
`spacevalue/cargo.py` stays the reference and the default.

## What it is

Two crates:

| crate | is | used by |
|---|---|---|
| `cargo_core` | `optimal_payload_mix`, `_hold_refining` and `_capped_sale_value`, ported operation for operation from `cargo.py`; plain Rust, no Python | `cargo_py` here, and economicspace's `es_core`, which links it directly |
| `cargo_py` | an optional PyO3 module, `spacevalue_cargo_rs`, with the same three names and signatures | `tests/test_cargo_rust.py` |

The point of keeping the port here rather than in economicspace: the copy
lives next to the code it copies and is tested against it by the same suite,
so a change to the knapsack that is not made in both places fails here,
before a release, not later in economicspace.

## The contract

The golden test's: the same result bit for bit, and the same arguments
afterwards (`caps` is consumed in place). What a port gets wrong, and how
this one copies the Python:

- `sorted(..., key=lambda p: -p[2])` is a stable sort on the negated price.
  Any stable sort agrees with timsort when no price is NaN, so a NaN price is
  handed back to the Python.
- Python's `min(a, b)` keeps `a` unless `b < a`; `max(items, key=...)` keeps
  the first item unless a later key is strictly greater.
- `mix_kg` is a dict: a name keeps the position of its first insertion.
- `caps` is spent on a local copy and written back only on success, so a call
  handed to the Python finds the caller's dict untouched.
- Where the Python raises (an infinite payload from which nothing was taken
  ends in `max()` of an empty mix), the Python runs, so the same exception
  surfaces.

The binding hands a call to the Python, untouched, whenever it cannot read
the inputs exactly: a non-float where a float goes, an int past 2**53, a caps
value that is neither float nor None, a NaN in the answer. `counts()` says how
many calls each side answered.

## Measured (2026-11-15, Windows, CPython 3.14)

| check | result |
|---|---|
| golden replay, `optimal_payload_mix` / `_hold_refining` / `_capped_sale_value` | 256 / 416 / 67 recorded calls, 0 differ |
| fuzz against the Python | 60,000 + 30,000 + 30,000 calls, 0 differ (exceptions compared too) |
| plant (`planted_knapsack_defect`: one ulp in every take and in the capped sale's value) | all six tests fail |
| the whole suite with the binding installed | 189 passed |
| per call, through the Python boundary | 1.9x / 1.3x / 3.7x faster: about 1 to 3.5 us saved per call |

Called from Python, the binding is worth little: the boundary costs about as
much as the walk. The gain is in `es_core`, where the sizing loop calls
`cargo_core` with no boundary at all (economicspace's
`rust/es_core/README.md` has those numbers).

## Build and test

Build outside OneDrive (inside it, build scripts fail with "output path is
not a writable directory"):

    export CARGO_TARGET_DIR="$HOME/.cargo-target/spacevalue_cargo"
    cd rust/cargo_py
    python -m maturin build --release -o dist
    python -m pip install --force-reinstall --no-deps dist/spacevalue_cargo_rs-*.whl
    cd ../..
    SPACEVALUE_REQUIRE_RUST=1 python -m pytest tests/test_cargo_rust.py

Without the module, `test_cargo_rust.py` skips; `SPACEVALUE_REQUIRE_RUST=1`
turns that skip into a failure, and the gate always sets it, so the check
cannot pass by not running. The planted build, which must fail all six:

    python -m maturin build --release --features planted_knapsack_defect -o dist-plant

## Before this could merge (not done)

- CI: build the binding on the three hosts in `tests.yml` and run
  `test_cargo_rust.py` with `SPACEVALUE_REQUIRE_RUST=1`; build and run the
  planted copy, expecting failure. Without that, a knapsack change that skips
  the Rust copy only fails on a machine that happens to have it built.
- Decide how economicspace's `es_core` pins `cargo_core`: a git dependency at
  the same tag as the spacevalue pin, held together by a check, as check 7
  holds the Python pins.
- Decide whether `spacevalue.cargo` should ever dispatch to the binding
  itself. The per-call numbers above say probably not.
- A change to the knapsack is then a change to both copies, and the golden
  fixture re-recorded only with the calc release that moves it, as now.
