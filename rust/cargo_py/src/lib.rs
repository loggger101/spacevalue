//! PROTOTYPE: the optional Python binding of `spacevalue_cargo_core`.
//!
//! Same names, same signatures and same results as `spacevalue.cargo`'s
//! `optimal_payload_mix`, `_hold_refining` and `_capped_sale_value`.  Any
//! input the Rust path cannot be sure of (a non-exact float, a NaN price, an
//! int past 2**53, a caps value that is neither float nor None) is handed to
//! the Python function itself, untouched, and counted; so is any answer with
//! a NaN in it.  `caps` is written back only after the Rust walk succeeded.

use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
use spacevalue_cargo_core as core;
use std::sync::atomic::{AtomicU64, Ordering::Relaxed};

static FAST: AtomicU64 = AtomicU64::new(0);
static SLOW: AtomicU64 = AtomicU64::new(0);

fn exact_f(v: &Bound<'_, PyAny>) -> Option<f64> {
    v.downcast_exact::<PyFloat>().ok().map(|f| f.value())
}

/// A float, or an int that converts exactly (what `float(x)` gives).
fn float_or_int(v: &Bound<'_, PyAny>) -> Option<f64> {
    if let Some(f) = exact_f(v) {
        return Some(f);
    }
    let n: i64 = v.downcast_exact::<PyInt>().ok()?.extract().ok()?;
    if n.abs() <= (1i64 << 53) { Some(n as f64) } else { None }
}

/// The phase list: exact `(str, float, float)` tuples in a list.  `None` for
/// anything else.  Names are copied out (the walk outlives the borrow).
fn read_phases(v: &Bound<'_, PyAny>) -> Option<Vec<(String, f64, f64)>> {
    let l = v.downcast_exact::<PyList>().ok()?;
    let mut out = Vec::with_capacity(l.len());
    for item in l.iter() {
        let t = item.downcast_exact::<PyTuple>().ok()?;
        if t.len() != 3 {
            return None;
        }
        let name = t.get_item(0).ok()?.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned();
        let frac = exact_f(&t.get_item(1).ok()?)?;
        let price = exact_f(&t.get_item(2).ok()?)?;
        out.push((name, frac, price));
    }
    Some(out)
}

fn as_phases(owned: &[(String, f64, f64)]) -> Vec<core::Phase<'_>> {
    owned.iter().map(|(n, f, p)| core::Phase { name: n.as_str(), frac: *f, price: *p }).collect()
}

fn py_cargo<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyModule>> {
    py.import("spacevalue.cargo")
}

fn slow<'py>(py: Python<'py>, name: &str, args: Bound<'py, PyTuple>, kwargs: Option<&Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyAny>> {
    SLOW.fetch_add(1, Relaxed);
    py_cargo(py)?.getattr(name)?.call(args, kwargs)
}

fn mix_nan(m: &core::Mix<'_>) -> bool {
    m.value_usd.is_nan() || m.usd_per_kg.is_nan() || m.loaded_kg.is_nan() || m.surplus_kg.is_nan()
        || m.dominant_frac.is_nan() || m.mix_kg.iter().any(|(_, v)| v.is_nan())
}

fn mix_dict<'py>(py: Python<'py>, out: Option<&core::Mix<'_>>) -> PyResult<Bound<'py, PyDict>> {
    let d = PyDict::new(py);
    match out {
        None => {
            d.set_item("value_usd", 0.0)?;
            d.set_item("usd_per_kg", 0.0)?;
            d.set_item("mix_kg", PyDict::new(py))?;
            d.set_item("dominant_phase", py.None())?;
            d.set_item("dominant_frac", 0.0)?;
            d.set_item("surplus_kg", 0.0)?;
        }
        Some(m) => {
            let mk = PyDict::new(py);
            for (n, v) in &m.mix_kg {
                mk.set_item(*n, *v)?;
            }
            d.set_item("value_usd", m.value_usd)?;
            d.set_item("usd_per_kg", m.usd_per_kg)?;
            d.set_item("loaded_kg", m.loaded_kg)?;
            d.set_item("mix_kg", mk)?;
            d.set_item("surplus_kg", m.surplus_kg)?;
            d.set_item("dominant_phase", m.dominant_phase)?;
            d.set_item("dominant_frac", m.dominant_frac)?;
        }
    }
    Ok(d)
}

/// Inputs of one `optimal_payload_mix` call, read exactly, or None.
struct MixIn {
    payload: f64,
    feed: f64,
    phases: Vec<(String, f64, f64)>,
    recovery: f64,
    want: Option<String>,
    caps: Option<core::CapsVec>,
    surplus: f64,
}

fn read_mix_in(
    payload: &Bound<'_, PyAny>, feed: &Bound<'_, PyAny>, phases: &Bound<'_, PyAny>,
    recovery: &Bound<'_, PyAny>, want: &Bound<'_, PyAny>, caps: &Bound<'_, PyAny>,
    cap_keys: &Bound<'_, PyAny>, surplus: &Bound<'_, PyAny>,
) -> Option<MixIn> {
    let payload = float_or_int(payload)?;
    let feed = float_or_int(feed)?;
    let phases = read_phases(phases)?;
    let recovery = float_or_int(recovery)?;
    let want = if want.is_none() { None } else { Some(want.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned()) };
    // `cap_keys.get(name, name) if cap_keys else name`: an empty dict is
    // falsy, so None and {} are one case.
    let mut key_of = Vec::new();
    if !cap_keys.is_none() {
        let d = cap_keys.downcast_exact::<PyDict>().ok()?;
        for (k, v) in d.iter() {
            let k = k.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned();
            let v = v.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned();
            key_of.push((k, v));
        }
    }
    let caps = if caps.is_none() {
        None
    } else {
        let d = caps.downcast_exact::<PyDict>().ok()?;
        let mut entries = Vec::with_capacity(d.len());
        for (k, v) in d.iter() {
            let k = k.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned();
            if v.is_none() {
                continue; // `caps.get(key)` is None: never read, never written
            }
            entries.push((k, exact_f(&v)?));
        }
        Some(core::CapsVec::new(entries, key_of))
    };
    let surplus = exact_f(surplus)?;
    if phases.iter().any(|p| p.2.is_nan()) {
        return None;
    }
    Some(MixIn { payload, feed, phases, recovery, want, caps, surplus })
}

#[pyfunction]
#[pyo3(signature = (payload_kg, feed_kg, phases, recovery, want_phase=None, caps=None, cap_keys=None, surplus_price_frac=None))]
#[allow(clippy::too_many_arguments)]
fn optimal_payload_mix<'py>(
    py: Python<'py>,
    payload_kg: Bound<'py, PyAny>,
    feed_kg: Bound<'py, PyAny>,
    phases: Bound<'py, PyAny>,
    recovery: Bound<'py, PyAny>,
    want_phase: Option<Bound<'py, PyAny>>,
    caps: Option<Bound<'py, PyAny>>,
    cap_keys: Option<Bound<'py, PyAny>>,
    surplus_price_frac: Option<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    let none = py.None().into_bound(py);
    let want_b = want_phase.clone().unwrap_or_else(|| none.clone());
    let caps_b = caps.clone().unwrap_or_else(|| none.clone());
    let keys_b = cap_keys.clone().unwrap_or_else(|| none.clone());
    let zero = PyFloat::new(py, 0.0).into_any();
    let surplus_b = surplus_price_frac.clone().unwrap_or(zero);
    let fallback = |py: Python<'py>| -> PyResult<Bound<'py, PyAny>> {
        let args = PyTuple::new(py, [payload_kg.clone(), feed_kg.clone(), phases.clone(), recovery.clone()])?;
        let kw = PyDict::new(py);
        if let Some(v) = &want_phase { kw.set_item("want_phase", v)?; }
        if let Some(v) = &caps { kw.set_item("caps", v)?; }
        if let Some(v) = &cap_keys { kw.set_item("cap_keys", v)?; }
        if let Some(v) = &surplus_price_frac { kw.set_item("surplus_price_frac", v)?; }
        slow(py, "optimal_payload_mix", args, Some(&kw))
    };
    let Some(mut inp) = read_mix_in(&payload_kg, &feed_kg, &phases, &recovery, &want_b, &caps_b, &keys_b, &surplus_b) else {
        return fallback(py);
    };
    let ph = as_phases(&inp.phases);
    let ordered = core::by_price(&ph);
    let mut caps_local = inp.caps.take();
    let out = core::optimal_payload_mix(inp.payload, inp.feed, &ordered, inp.recovery,
                                        inp.want.as_deref(), caps_local.as_mut(), inp.surplus);
    match out {
        core::MixOut::Want(v) => {
            if v.is_nan() {
                return fallback(py);
            }
            if let (Some(c), Some(d)) = (&caps_local, &caps) { write_back(c, d)?; }
            FAST.fetch_add(1, Relaxed);
            Ok(PyFloat::new(py, v).into_any())
        }
        core::MixOut::Raises => fallback(py),
        core::MixOut::Full(m) => {
            if let Some(m) = &m {
                if mix_nan(m) {
                    return fallback(py);
                }
            }
            if let (Some(c), Some(d)) = (&caps_local, &caps) { write_back(c, d)?; }
            FAST.fetch_add(1, Relaxed);
            Ok(mix_dict(py, m.as_ref())?.into_any())
        }
    }
}

/// `caps[key] = allowance - take` for every key the walk spent.  Each key
/// already existed, so the dict's order is unchanged, as in the Python.
fn write_back(c: &core::CapsVec, d: &Bound<'_, PyAny>) -> PyResult<()> {
    let d = d.downcast_exact::<PyDict>()?;
    for (i, (k, v)) in c.entries.iter().enumerate() {
        if c.touched[i] {
            d.set_item(k, *v)?;
        }
    }
    Ok(())
}

#[pyfunction]
#[pyo3(name = "_hold_refining")]
fn hold_refining<'py>(
    py: Python<'py>,
    refinery: Bound<'py, PyAny>,
    phases: Bound<'py, PyAny>,
    payload_kg: Bound<'py, PyAny>,
    feed_kg: Bound<'py, PyAny>,
    beneficiate: Bound<'py, PyAny>,
    recovery: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyAny>> {
    let fallback = |py: Python<'py>| {
        let args = PyTuple::new(py, [refinery.clone(), phases.clone(), payload_kg.clone(),
                                     feed_kg.clone(), beneficiate.clone(), recovery.clone()])?;
        slow(py, "_hold_refining", args, None)
    };
    // (per_phase dict as pairs, raw Wh/kg), or None.
    let reff: Option<(Vec<(String, f64)>, f64)> = if refinery.is_none() {
        None
    } else {
        let parsed = (|| -> Option<(Vec<(String, f64)>, f64)> {
            let t = refinery.downcast_exact::<PyTuple>().ok()?;
            if t.len() != 2 { return None; }
            let d = t.get_item(0).ok()?;
            let d = d.downcast_exact::<PyDict>().ok()?;
            let mut m = Vec::with_capacity(d.len());
            for (k, v) in d.iter() {
                m.push((k.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned(), exact_f(&v)?));
            }
            Some((m, exact_f(&t.get_item(1).ok()?)?))
        })();
        match parsed { Some(p) => Some(p), None => return fallback(py) }
    };
    let (Some(payload), Some(feed), Some(rec)) = (float_or_int(&payload_kg), float_or_int(&feed_kg), float_or_int(&recovery)) else {
        return fallback(py);
    };
    let Ok(ben) = beneficiate.downcast_exact::<PyBool>().map(|b| b.is_true()) else { return fallback(py) };
    let owned: Vec<(String, f64, f64)> = if phases.is_none() {
        Vec::new()
    } else {
        match read_phases(&phases) { Some(p) => p, None => return fallback(py) }
    };
    if owned.iter().any(|p| p.2.is_nan()) {
        return fallback(py);
    }
    let ph = as_phases(&owned);
    let ordered = core::by_price(&ph);
    let r = match &reff {
        None => core::hold_refining(None, &ordered, payload, feed, ben, rec),
        Some((m, raw)) => {
            let f = |name: &str| -> f64 { m.iter().find(|(k, _)| k == name).map(|(_, v)| *v).unwrap_or(0.0) };
            core::hold_refining(Some((&f, *raw)), &ordered, payload, feed, ben, rec)
        }
    };
    let Some(r) = r else { return fallback(py) };
    if r.0.is_nan() || r.1.is_some_and(|w| w.is_nan()) {
        return fallback(py);
    }
    FAST.fetch_add(1, Relaxed);
    let water: Bound<'py, PyAny> = match r.1 {
        None => py.None().into_bound(py),
        Some(w) => PyFloat::new(py, w).into_any(),
    };
    Ok(PyTuple::new(py, [PyFloat::new(py, r.0).into_any(), water])?.into_any())
}

#[pyfunction]
#[pyo3(name = "_capped_sale_value", signature = (sale_terms, window_yr, surplus_price_frac=None))]
fn capped_sale_value<'py>(
    py: Python<'py>,
    sale_terms: Bound<'py, PyAny>,
    window_yr: Bound<'py, PyAny>,
    surplus_price_frac: Option<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    let fallback = |py: Python<'py>| {
        let args = PyTuple::new(py, [sale_terms.clone(), window_yr.clone()])?;
        let kw = PyDict::new(py);
        if let Some(v) = &surplus_price_frac { kw.set_item("surplus_price_frac", v)?; }
        slow(py, "_capped_sale_value", args, Some(&kw))
    };
    let parsed = (|| -> Option<(Vec<(f64, f64, f64, String)>, f64, f64)> {
        let l = sale_terms.downcast_exact::<PyList>().ok()?;
        let mut v = Vec::with_capacity(l.len());
        for it in l.iter() {
            let t = it.downcast_exact::<PyTuple>().ok()?;
            if t.len() != 4 { return None; }
            v.push((exact_f(&t.get_item(0).ok()?)?, exact_f(&t.get_item(1).ok()?)?,
                    exact_f(&t.get_item(2).ok()?)?,
                    t.get_item(3).ok()?.downcast_exact::<PyString>().ok()?.to_str().ok()?.to_owned()));
        }
        let w = exact_f(&window_yr)?;
        let s = match &surplus_price_frac { None => 0.0, Some(b) => exact_f(b)? };
        if v.iter().any(|t| t.1.is_nan()) { return None; }
        Some((v, w, s))
    })();
    let Some((owned, w, s)) = parsed else { return fallback(py) };
    let terms: Vec<core::SaleTerm<'_>> = owned.iter().map(|(kg, p, m, k)| core::SaleTerm { kg: *kg, price: *p, mkt: *m, key: k.as_str() }).collect();
    let (a, b, c) = core::capped_sale_value(&terms, w, s);
    if a.is_nan() || b.is_nan() || c.is_nan() {
        return fallback(py);
    }
    FAST.fetch_add(1, Relaxed);
    Ok(PyTuple::new(py, [a, b, c])?.into_any())
}

/// (calls answered in Rust, calls handed to the Python).
#[pyfunction]
fn counts() -> (u64, u64) {
    (FAST.load(Relaxed), SLOW.load(Relaxed))
}

#[pyfunction]
fn planted_defect() -> bool {
    core::planted_defect()
}

#[pymodule]
fn spacevalue_cargo_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(optimal_payload_mix, m)?)?;
    m.add_function(wrap_pyfunction!(hold_refining, m)?)?;
    m.add_function(wrap_pyfunction!(capped_sale_value, m)?)?;
    m.add_function(wrap_pyfunction!(counts, m)?)?;
    m.add_function(wrap_pyfunction!(planted_defect, m)?)?;
    Ok(())
}
