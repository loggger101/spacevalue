//! PROTOTYPE: `spacevalue.cargo`'s payload knapsack in Rust.
//!
//! Three functions, ported operation for operation from `spacevalue/cargo.py`:
//! `optimal_payload_mix`, `_hold_refining` and `_capped_sale_value`.  The
//! contract is the one `tests/test_cargo_golden.py` holds the Python to: the
//! same bits.  Every float operation below is the Python's, in the Python's
//! order and association; read each against its line in cargo.py.
//!
//! What the Python does that Rust must copy, and where:
//!   * `sorted(phases, key=lambda p: -p[2])` is a STABLE sort on the negated
//!     price.  Any stable sort agrees with timsort under a strict weak order,
//!     which floats are once NaN is excluded (`has_nan_price` refuses it).
//!   * `min(a, b)` returns `a` unless `b < a`; `max(items, key=...)` keeps the
//!     first item unless a later key is strictly greater (`>`).
//!   * `mix` is a dict: a name keeps the position of its first insertion.
//!   * `caps` is consumed in place.  Here it is a local copy the caller writes
//!     back only on success, so a refused call leaves the caller's dict as it
//!     found it and the Python can run instead.
//!
//! Nothing here allocates per item beyond the walk's own lists, and nothing
//! depends on Python: es_core links this crate directly, and the PyO3 binding
//! in `rust/cargo_py` is a thin shell over it.

/// One row of `asteroid_phase_table`: `(name, mass_fraction, usd_per_kg)`.
#[derive(Clone, Copy, Debug)]
pub struct Phase<'a> {
    pub name: &'a str,
    pub frac: f64,
    pub price: f64,
}

/// `caps` together with `cap_keys`, as the walk reads and spends them, asked
/// by PHASE name: the map resolves the market key itself, exactly as the
/// Python's `cap_keys.get(name, name) if cap_keys else name` does per item.
/// `None` values are absent keys: `caps.get(key)` cannot tell them apart and
/// neither branch writes one.
pub trait Caps {
    fn get(&self, phase: &str) -> Option<f64>;
    fn set(&mut self, phase: &str, v: f64);
}

/// A small owned caps map (insertion-ordered; the walk only ever updates keys
/// that exist, so order is never changed by it).  `key_of` is `cap_keys`
/// (empty when `cap_keys` is None or empty, which the Python treats alike).
#[derive(Clone, Debug, Default)]
pub struct CapsVec {
    pub entries: Vec<(String, f64)>,
    pub touched: Vec<bool>,
    pub key_of: Vec<(String, String)>,
}

impl CapsVec {
    pub fn new(entries: Vec<(String, f64)>, key_of: Vec<(String, String)>) -> Self {
        let n = entries.len();
        CapsVec { entries, touched: vec![false; n], key_of }
    }
    fn index(&self, phase: &str) -> Option<usize> {
        let key = match self.key_of.iter().find(|(n, _)| n == phase) {
            Some((_, k)) => k.as_str(),
            None => phase,
        };
        self.entries.iter().position(|(k, _)| k == key)
    }
}

impl Caps for CapsVec {
    fn get(&self, phase: &str) -> Option<f64> {
        self.index(phase).map(|i| self.entries[i].1)
    }
    fn set(&mut self, phase: &str, v: f64) {
        if let Some(i) = self.index(phase) {
            self.entries[i].1 = v;
            self.touched[i] = true;
        }
    }
}

#[inline(always)]
fn py_min(a: f64, b: f64) -> f64 {
    if b < a { b } else { a }
}

#[inline(always)]
fn planted(take: f64) -> f64 {
    #[cfg(feature = "planted_knapsack_defect")]
    {
        if take > 0.0 {
            return f64::from_bits(take.to_bits() ^ 1);
        }
    }
    take
}

pub fn planted_defect() -> bool {
    cfg!(feature = "planted_knapsack_defect")
}

/// True if any price is NaN: the sort would not be a strict weak order, and
/// timsort's answer would then depend on its merge pattern.
pub fn has_nan_price(phases: &[Phase<'_>]) -> bool {
    phases.iter().any(|p| p.price.is_nan())
}

/// `sorted(phases, key=lambda p: -p[2])`.  Caller guarantees no NaN price.
pub fn by_price<'a>(phases: &[Phase<'a>]) -> Vec<Phase<'a>> {
    let mut v = phases.to_vec();
    v.sort_by(|a, b| (-a.price).partial_cmp(&(-b.price)).unwrap());
    v
}

/// The full result dict.  `None` is the empty dict (no `loaded_kg` key).
#[derive(Clone, Debug, PartialEq)]
pub struct Mix<'a> {
    pub value_usd: f64,
    pub usd_per_kg: f64,
    pub loaded_kg: f64,
    pub mix_kg: Vec<(&'a str, f64)>,
    pub surplus_kg: f64,
    pub dominant_phase: &'a str,
    pub dominant_frac: f64,
}

#[derive(Clone, Debug, PartialEq)]
pub enum MixOut<'a> {
    /// `want_phase` was given: the bare float.
    Want(f64),
    /// The dict; `None` is the empty-load dict.
    Full(Option<Mix<'a>>),
    /// The Python raises here (`max()` of an empty mix, reached when
    /// `loaded` is NaN, i.e. an infinite payload nothing was taken from):
    /// the caller must run the Python so the same exception surfaces.
    Raises,
}

/// `optimal_payload_mix`.  `ordered` is `by_price(phases)` (the Python's
/// `_PHASE_ORDER_CACHE`), computed once by the caller per phase table.
/// `phases_empty` stands for `not phases` on the ORIGINAL list.
#[allow(clippy::too_many_arguments)]
pub fn optimal_payload_mix<'a, C: Caps>(
    payload_kg: f64,
    feed_kg: f64,
    ordered: &[Phase<'a>],
    recovery: f64,
    want_phase: Option<&str>,
    mut caps: Option<&mut C>,
    surplus_price_frac: f64,
) -> MixOut<'a> {
    if payload_kg <= 0.0 || ordered.is_empty() {
        return if want_phase.is_some() { MixOut::Want(0.0) } else { MixOut::Full(None) };
    }

    // The tiered walk (v1.22.0): each phase twice, full price then discount.
    let tiered_mode = caps.is_some() && surplus_price_frac > 0.0 && want_phase.is_none();
    let tiered_list: Vec<Phase<'a>>;
    let walk: &[Phase<'a>] = if tiered_mode {
        let frac = if surplus_price_frac < 1.0 { surplus_price_frac } else { 1.0 };
        let mut t: Vec<Phase<'a>> = Vec::with_capacity(2 * ordered.len());
        for p in ordered {
            t.push(*p);
            t.push(Phase { name: p.name, frac: p.frac, price: p.price * frac });
        }
        t.sort_by(|a, b| (-a.price).partial_cmp(&(-b.price)).unwrap());
        tiered_list = t;
        &tiered_list
    } else {
        ordered
    };
    // `tier_taken`, a dict keyed by name; small, so a linear map.
    let mut tier_taken: Vec<(&'a str, f64)> = Vec::new();

    let mut remaining = payload_kg;
    let mut total = 0.0f64;
    let mut surplus_kg = 0.0f64;
    let mut mix: Vec<(&'a str, f64)> = Vec::new();
    for p in walk {
        if remaining <= 0.0 {
            break;
        }
        let (available, full_tier, had);
        if !tiered_mode {
            available = feed_kg * p.frac * recovery;
            full_tier = true;
            had = 0.0;
        } else {
            let h = tier_taken.iter().find(|(n, _)| *n == p.name).map(|(_, v)| *v).unwrap_or(-1.0);
            full_tier = h < 0.0;
            if full_tier {
                had = 0.0;
                available = feed_kg * p.frac * recovery;
            } else {
                had = h;
                available = feed_kg * p.frac * recovery - had;
            }
        }
        let mut take = py_min(available, remaining);
        if full_tier {
            if let Some(c) = caps.as_deref_mut() {
                if let Some(allowance) = c.get(p.name) {
                    if allowance < take {
                        take = allowance;
                    }
                    c.set(p.name, allowance - take);
                }
            }
        }
        if tiered_mode {
            let v = had + take;
            match tier_taken.iter_mut().find(|(n, _)| *n == p.name) {
                Some(e) => e.1 = v,
                None => tier_taken.push((p.name, v)),
            }
        }
        if take <= 0.0 {
            continue;
        }
        let take = planted(take);
        if let Some(w) = want_phase {
            if p.name == w {
                return MixOut::Want(take);
            }
            remaining -= take;
            continue;
        }
        if full_tier {
            match mix.iter_mut().find(|(n, _)| *n == p.name) {
                Some(e) => e.1 = take,
                None => mix.push((p.name, take)),
            }
        } else {
            match mix.iter_mut().find(|(n, _)| *n == p.name) {
                Some(e) => e.1 += take,
                None => mix.push((p.name, 0.0 + take)),
            }
            surplus_kg += take;
        }
        total += take * p.price;
        remaining -= take;
    }

    if want_phase.is_some() {
        return MixOut::Want(0.0);
    }
    let loaded = payload_kg - remaining;
    if loaded <= 0.0 {
        return MixOut::Full(None);
    }
    // max(mix.items(), key=kv[1]): first item unless a later one is strictly
    // greater.  `loaded` is NaN when the payload is infinite, and then the
    // mix can be empty and the Python's `max()` raises.
    if mix.is_empty() {
        return MixOut::Raises;
    }
    let mut dom = mix[0];
    for e in &mix[1..] {
        if e.1 > dom.1 {
            dom = *e;
        }
    }
    MixOut::Full(Some(Mix {
        value_usd: total,
        usd_per_kg: total / loaded,
        loaded_kg: loaded,
        mix_kg: mix,
        surplus_kg,
        dominant_phase: dom.0,
        dominant_frac: dom.1 / loaded,
    }))
}

/// `_hold_refining`: `(refining Wh, Some(water kg) or None)`.
/// `refinery` is `None` or `(per_phase lookup, raw Wh/kg)`; `per_phase(name)`
/// is `per_phase.get(name, 0.0)`.  `phases_empty` is `not phases`.
/// `None` where the Python raises (see `MixOut::Raises`).
pub fn hold_refining<'a>(
    refinery: Option<(&dyn Fn(&str) -> f64, f64)>,
    ordered: &[Phase<'a>],
    payload_kg: f64,
    feed_kg: f64,
    beneficiate: bool,
    recovery: f64,
) -> Option<(f64, Option<f64>)> {
    let Some((per_phase, raw_wh_per_kg)) = refinery else { return Some((0.0, None)) };
    if payload_kg <= 0.0 {
        return Some((0.0, None));
    }
    if !beneficiate || ordered.is_empty() {
        return Some((payload_kg * raw_wh_per_kg, None));
    }
    let out = optimal_payload_mix::<CapsVec>(payload_kg, feed_kg, ordered, recovery, None, None, 0.0);
    let mix: Vec<(&str, f64)> = match out {
        MixOut::Full(Some(m)) => m.mix_kg,
        MixOut::Raises => return None,
        _ => Vec::new(),
    };
    let mut wh = 0.0f64;
    for (name, kg) in &mix {
        wh += kg * per_phase(name);
    }
    let water = mix.iter().find(|(n, _)| *n == "water").map(|(_, v)| *v).unwrap_or(0.0);
    Some((wh, Some(water)))
}

/// One `sale_terms` entry: `(kg, price, annual market kg, market key)`.
#[derive(Clone, Copy, Debug)]
pub struct SaleTerm<'a> {
    pub kg: f64,
    pub price: f64,
    pub mkt: f64,
    pub key: &'a str,
}

/// `_capped_sale_value`: `(value_usd, unsold_kg, surplus_kg)`.  Caller
/// guarantees no NaN price (the grant order is a sort on it).
pub fn capped_sale_value(terms: &[SaleTerm<'_>], window_yr: f64, surplus_price_frac: f64) -> (f64, f64, f64) {
    let sells = surplus_price_frac > 0.0;
    let mut order: Vec<usize> = (0..terms.len()).collect();
    order.sort_by(|&a, &b| (-terms[a].price).partial_cmp(&(-terms[b].price)).unwrap());
    let mut remaining: Vec<(&str, f64)> = Vec::new();
    let mut grants = vec![0.0f64; terms.len()];
    for &i in &order {
        let t = terms[i];
        let allowance = match remaining.iter().find(|(k, _)| *k == t.key) {
            Some((_, v)) => *v,
            None => t.mkt * window_yr,
        };
        grants[i] = if t.kg > allowance { allowance } else { t.kg };
        let left = if t.kg > allowance { 0.0 } else { allowance - t.kg };
        match remaining.iter_mut().find(|(k, _)| *k == t.key) {
            Some(e) => e.1 = left,
            None => remaining.push((t.key, left)),
        }
    }
    let (mut value, mut unsold, mut surplus) = (0.0f64, 0.0f64, 0.0f64);
    for (i, t) in terms.iter().enumerate() {
        let granted = grants[i];
        if t.kg > granted {
            let over = t.kg - granted;
            value += granted * t.price;
            if sells {
                value += over * t.price * surplus_price_frac;
                surplus += over;
            } else {
                unsold += over;
            }
        } else {
            value += t.kg * t.price;
        }
    }
    #[cfg(feature = "planted_knapsack_defect")]
    {
        if value != 0.0 {
            value = f64::from_bits(value.to_bits() ^ 1);
        }
    }
    (value, unsold, surplus)
}
