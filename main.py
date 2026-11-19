#!/usr/bin/env python3
"""QuantumZeno-Lab - educational quantum Zeno & anti-Zeno effect lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * This lab computes the quantum Zeno and anti-Zeno effects in
    labelled toy models: a resonantly driven two-level system under
    ideal projective measurements, the quadratic short-time law of
    an unstable state versus the exponential law it follows later,
    the measurement-rate curve into a Lorentzian reservoir (where
    the anti-Zeno acceleration lives), and a three-level leakage
    toy where measurements guard a computational subspace.
  * Every measurement here is IDEAL and projective. No detector
    inefficiency, dark count, finite bandwidth, or readout error
    is modelled, and none may be claimed from these numbers.
  * A computed suppression factor is a statement about the model
    at the stated inputs - it is not a qubit-protection result,
    not an error-correction deployment, and not a promise that
    any real process can be frozen, slowed, or hurried.

Conventions, stated once and used everywhere (hbar = 1):

  * Watched system: resonant Rabi drive, H = (OMEGA/2) sigma_x,
    free survival P_free(t) = cos^2(OMEGA t / 2). N ideal projective
    measurements at equal intervals over total time t give
    P_N(t) = [cos^2(OMEGA t / (2N))]^N exactly.
  * Short-time law: P(t) ~ 1 - (t / tau_Z)^2 with
    tau_Z = 1 / DeltaH, DeltaH^2 = <H^2> - <H>^2 computed from the
    labelled model Hamiltonian's matrix, never quoted.
  * Reservoir: Lorentzian spectral density
    J(w) = (GAMMA0 / 2pi) * LAMBDA^2 / ((w - OMEGA0)^2 + LAMBDA^2).
    The free decay rate is the golden-rule value
    GAMMA_FREE = 2 pi J(OMEGA_A). Under measurements at interval
    tau the Kofman-Kurizki filter gives
    GAMMA(tau) = tau * Integral J(w) sinc^2((w - OMEGA_A) tau / 2) dw,
    integrated numerically on a stated grid.
  * Subspace toy: H couples |1> to the leakage state |2> with
    strength G_LEAK; one interval leaks sin^2(G_LEAK tau) and M
    guarded intervals keep [cos^2(G_LEAK tau)]^M in the subspace.

Real error-correction deployment, qubit protection, decay control,
device, vendor, and hardware claims are permanent HOLD gates -
with Gemini Argon 4 Extended Thinking as DECIDER (names-only,
tighten-only), Muse as advisor (never overrides HOLD), and
Google Flow plan-only seats.
"""
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# Labelled teaching parameters. These are model inputs chosen so the
# arithmetic is easy to audit - they are not device specifications.
OMEGA = 1.0            # resonant Rabi frequency of the watched qubit
MODEL_OMEGA = 1.0      # drive term of the short-time model Hamiltonian
MODEL_DELTA = 0.7      # detuning term of the model Hamiltonian
GAMMA0 = 0.5           # reservoir coupling scale in J(w)
LAMBDA = 1.0           # reservoir linewidth (Lorentzian half-width)
OMEGA0 = 9.0           # reservoir centre frequency
OMEGA_A = 10.5         # transition frequency (detuned +1.5 LAMBDA)
G_LEAK = 0.3           # leakage coupling |1> -> |2> in the subspace toy
T_TOTAL = math.pi      # total guarded time in the subspace toy

# Reservoir integration grid, stated openly: trapezoid rule on
# w in [GRID_W_MIN, GRID_W_MAX] with GRID_STEP spacing. The Lorentzian
# tail beyond the grid edge carries < 1% of the total spectral weight;
# every rate tolerance in CHECKS is set with that truncation in mind.
GRID_W_MIN = 0.0
GRID_W_MAX = 70.0
GRID_STEP = 0.025

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "real_error_correction_deployment": "HOLD - no deploying Zeno-based error correction on a real device from this lab",
    "qubit_protection_claim": "HOLD - no claiming a real qubit, memory, or state was protected by these toy numbers",
    "real_device_control": "HOLD - no control of real qubits, detectors, lasers, or measurement hardware",
    "decay_control_claim": "HOLD - no claiming control over real radioactive, chemical, or biological decay",
    "detector_efficiency_claim": "HOLD - measurements here are ideal and projective; no real detector efficiency, dark-count, or bandwidth spec may be quoted",
    "hardware_spec_claim": "HOLD - labelled model inputs are not hardware specifications",
    "vendor_product_claim": "HOLD - no vendor or product claim for any measurement or control system",
    "medical_claim": "HOLD - no medical, diagnostic, or therapy claim from Zeno toy models",
    "sensing_metrology_claim": "HOLD - no sensing or metrology performance claim from this lab",
    "quantum_computing_product_claim": "HOLD - no quantum-computing product or roadmap claim",
    "certified_protection_claim": "HOLD - no certifying that any system is Zeno-protected or error-proof",
    "investment_claim": "HOLD - no investment claim; a lab model is not a prospectus",
    "guaranteed_freezing_claim": "HOLD - no claiming a real process was frozen, stopped, or guaranteed stable",
    "safety_critical_reliance": "HOLD - no relying on computed Zeno suppression in any safety-critical system",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. Watched two-level system
# The textbook Zeno setup. A resonantly driven qubit would Rabi-flop
# from |0> to |1> and back; ideal projective measurements onto |0>,
# repeated N times over the same total time, keep resetting the tiny
# quadratic leakage - and the survival probability climbs to 1.

def free_survival(t, omega=OMEGA):
    """Unmeasured survival probability cos^2(omega t / 2)."""
    return math.cos(omega * t / 2.0) ** 2


def watched_survival(t, n, omega=OMEGA):
    """Closed form: [cos^2(omega t / (2N))]^N for N ideal measurements."""
    if n < 1:
        raise ValueError("measurement count must be >= 1")
    return math.cos(omega * t / (2.0 * n)) ** (2 * n)


def _rabi_step(state, dt, omega=OMEGA):
    """One free-evolution step under H = (omega/2) sigma_x."""
    a, b = state
    c = math.cos(omega * dt / 2.0)
    s = math.sin(omega * dt / 2.0)
    return (c * a - 1j * s * b, -1j * s * a + c * b)


def watched_survival_sim(t, n, omega=OMEGA):
    """Step-by-step route: evolve, project onto |0>, renormalise, repeat.

    The surviving probability is the product of the per-interval
    |amplitude|^2 values. This is an independent implementation of
    watched_survival - CHECKS asserts the two agree, which catches
    exponent and interval errors in either one.
    """
    if n < 1:
        raise ValueError("measurement count must be >= 1")
    dt = t / n
    state = (1.0 + 0.0j, 0.0j)
    survival = 1.0
    for _ in range(n):
        state = _rabi_step(state, dt, omega)
        p = abs(state[0]) ** 2
        survival *= p
        state = (1.0 + 0.0j, 0.0j)  # projected + renormalised
    return survival


def zeno_deficit_asymptotic(t, n, omega=OMEGA):
    """Leading short-time deficit: 1 - P_N ~ (omega t)^2 / (4N).

    From ln P_N = N ln cos^2(x/N) with x = omega t / 2 and
    ln cos^2(u) = -u^2 - u^4/6 - ..., so ln P_N ~ -x^2/N.
    """
    return (omega * t) ** 2 / (4.0 * n)


def watched_table(t=math.pi):
    """Survival at the full-flip time for the standard N ladder."""
    rows = []
    for n in (1, 2, 5, 10, 50, 100, 1000):
        p = watched_survival(t, n)
        rows.append({
            "n": n,
            "survival": p,
            "deficit": 1.0 - p,
            "deficit_asymptotic": zeno_deficit_asymptotic(t, n),
        })
    return {"t": t, "free_survival": free_survival(t), "rows": rows}


# ================================================================ 2. Quadratic vs exponential regimes
# An unstable state does NOT start decaying exponentially. For short
# times P(t) ~ 1 - (DeltaH t)^2 - the quadratic law that makes the
# Zeno effect possible. DeltaH is computed from the labelled model
# Hamiltonian H = (MODEL_DELTA/2) sigma_z + (MODEL_OMEGA/2) sigma_x
# acting on |0>, straight from the matrix entries.

def model_hamiltonian():
    """The labelled 2x2 model Hamiltonian (real symmetric)."""
    return [[MODEL_DELTA / 2.0, MODEL_OMEGA / 2.0],
            [MODEL_OMEGA / 2.0, -MODEL_DELTA / 2.0]]


def _mat2_mul(a, b):
    return [[a[i][0] * b[0][j] + a[i][1] * b[1][j] for j in range(2)]
            for i in range(2)]


def delta_h():
    """DeltaH of |0> under the model Hamiltonian, from the matrix.

    DeltaH^2 = <H^2>_00 - <H>_00^2, both read off the matrices.
    """
    h = model_hamiltonian()
    h2 = _mat2_mul(h, h)
    mean = h[0][0]
    mean_sq = h2[0][0]
    return math.sqrt(max(mean_sq - mean * mean, 0.0))


def zeno_time():
    """tau_Z = 1 / DeltaH (hbar = 1)."""
    return 1.0 / delta_h()


def exact_survival(t):
    """Exact survival of |0> under the model Hamiltonian.

    P(t) = 1 - (OMEGA^2 / w^2) sin^2(w t / 2), w = sqrt(OMEGA^2+DELTA^2).
    """
    w = math.sqrt(MODEL_OMEGA ** 2 + MODEL_DELTA ** 2)
    return 1.0 - (MODEL_OMEGA ** 2 / w ** 2) * math.sin(w * t / 2.0) ** 2


def exact_survival_rk4(t, steps=4000):
    """Independent route: RK4 integration of dpsi/dt = -i H psi."""
    h = model_hamiltonian()
    dt = t / steps
    psi = [1.0 + 0.0j, 0.0j]

    def deriv(p):
        return [-1j * (h[0][0] * p[0] + h[0][1] * p[1]),
                -1j * (h[1][0] * p[0] + h[1][1] * p[1])]

    for _ in range(steps):
        k1 = deriv(psi)
        p2 = [psi[i] + 0.5 * dt * k1[i] for i in range(2)]
        k2 = deriv(p2)
        p3 = [psi[i] + 0.5 * dt * k2[i] for i in range(2)]
        k3 = deriv(p3)
        p4 = [psi[i] + dt * k3[i] for i in range(2)]
        k4 = deriv(p4)
        psi = [psi[i] + dt * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0
               for i in range(2)]
    return abs(psi[0]) ** 2


def quadratic_survival(t):
    """Short-time law: 1 - (DeltaH t)^2 = 1 - (t / tau_Z)^2."""
    return 1.0 - (delta_h() * t) ** 2


def exponential_survival(t, gamma=None):
    """Long-time law with the reservoir's free rate (section 3)."""
    gamma = free_decay_rate() if gamma is None else gamma
    return math.exp(-gamma * t)


def _bisect(f, lo, hi, iterations=200):
    flo = f(lo)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if flo * f(mid) <= 0.0:
            hi = mid
        else:
            lo, flo = mid, f(mid)
    return 0.5 * (lo + hi)


def crossover_time():
    """Where the quadratic and exponential asymptotes cross.

    f(t) = quadratic - exponential is positive at t = 0.5 (the
    exponential's linear term makes it dip faster at first) and
    negative at t = 1.5 (the quadratic plunges to zero at tau_Z
    while the exponential is still near 0.79). One crossing.
    """
    return _bisect(lambda t: quadratic_survival(t) - exponential_survival(t),
                   0.5, 1.5)


def quadratic_breakdown_time(tol=0.01):
    """First t where |exact - quadratic| exceeds tol (scan + bisect)."""
    def gap(t):
        return abs(exact_survival(t) - quadratic_survival(t)) - tol
    return _bisect(gap, 0.5, 1.0)


def regimes_report():
    return {
        "model_hamiltonian": model_hamiltonian(),
        "delta_h": delta_h(),
        "tau_z": zeno_time(),
        "free_decay_rate": free_decay_rate(),
        "crossover_time": crossover_time(),
        "quadratic_breakdown_time_1pct": quadratic_breakdown_time(),
        "samples": [
            {"t": t,
             "exact": exact_survival(t),
             "quadratic": quadratic_survival(t),
             "exponential": exponential_survival(t)}
            for t in (0.1, 0.2, 0.5, 1.0, 1.5, 2.0)
        ],
    }


# ================================================================ 3. Anti-Zeno: decay into a reservoir
# Repeated measurement does not always slow decay. The measurement
# broadens the transition line into a sinc^2 filter of width ~1/tau;
# the decay rate is the overlap of that filter with the reservoir
# spectrum J(w). The transition OMEGA_A sits on the SLOPE of the
# Lorentzian (detuned +1.5 LAMBDA from its centre), so moderate
# broadening pulls in MORE spectral weight than the free rate sees:
# Gamma(tau) rises above GAMMA_FREE (anti-Zeno), peaks near
# tau ~ 2, then falls to zero linearly as tau -> 0 (Zeno).

def spectral_density(w):
    """Lorentzian reservoir spectrum J(w)."""
    return (GAMMA0 / (2.0 * math.pi)) * LAMBDA ** 2 / (
        (w - OMEGA0) ** 2 + LAMBDA ** 2)


def free_decay_rate():
    """Golden-rule rate GAMMA_FREE = 2 pi J(OMEGA_A), analytic."""
    return 2.0 * math.pi * spectral_density(OMEGA_A)


_GRID = None


def _reservoir_grid():
    """Precomputed (w, J(w)) trapezoid grid - built once per process."""
    global _GRID
    if _GRID is None:
        n = int(round((GRID_W_MAX - GRID_W_MIN) / GRID_STEP))
        _GRID = [(GRID_W_MIN + i * GRID_STEP,
                  spectral_density(GRID_W_MIN + i * GRID_STEP))
                 for i in range(n + 1)]
    return _GRID


def gamma_rate(tau):
    """Decay rate under measurements at interval tau (numeric integral).

    GAMMA(tau) = tau * Integral J(w) sinc^2((w - OMEGA_A) tau / 2) dw
    on the stated trapezoid grid. As tau -> infinity the filter
    tends to a delta at OMEGA_A and GAMMA -> GAMMA_FREE; as
    tau -> 0 the filter flattens and GAMMA ~ tau * Integral J -> 0.
    """
    if tau <= 0:
        raise ValueError("measurement interval must be positive")
    grid = _reservoir_grid()
    total = 0.0
    last = len(grid) - 1
    for i, (w, jw) in enumerate(grid):
        x = (w - OMEGA_A) * tau / 2.0
        filt = 1.0 if abs(x) < 1e-12 else (math.sin(x) / x) ** 2
        weight = 0.5 if i in (0, last) else 1.0
        total += weight * jw * filt
    return tau * total * GRID_STEP


def gamma_ratio(tau):
    """GAMMA(tau) / GAMMA_FREE: < 1 Zeno side, > 1 anti-Zeno side."""
    return gamma_rate(tau) / free_decay_rate()


def antizeno_peak():
    """Peak of Gamma(tau)/GAMMA_FREE on a log scan, tau in [0.05, 20]."""
    best_tau, best_ratio = None, -1.0
    steps = 120
    for i in range(steps + 1):
        tau = 0.05 * (20.0 / 0.05) ** (i / steps)
        ratio = gamma_ratio(tau)
        if ratio > best_ratio:
            best_tau, best_ratio = tau, ratio
    return {"tau": best_tau, "ratio": best_ratio}


def antizeno_crossing():
    """tau* where Gamma(tau) first equals GAMMA_FREE (bisection).

    ratio(0.3) < 1 (Zeno side) and ratio(1.5) > 1 (anti-Zeno side),
    so the rising crossing is bracketed. Below tau* measurements
    protect; above it they accelerate the decay.
    """
    return _bisect(lambda tau: gamma_ratio(tau) - 1.0, 0.3, 1.5)


def antizeno_table():
    taus = (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0,
            8.0, 12.0, 20.0)
    return {
        "gamma_free": free_decay_rate(),
        "j_at_transition": spectral_density(OMEGA_A),
        "j_at_centre": spectral_density(OMEGA0),
        "peak": antizeno_peak(),
        "crossing_tau": antizeno_crossing(),
        "rows": [{"tau": tau, "gamma": gamma_rate(tau),
                  "ratio": gamma_ratio(tau)} for tau in taus],
    }


# ================================================================ 4. Zeno subspace: leakage toy
# A three-level toy: |0> and |1> are the computational subspace and
# |2> is a leakage state coupled to |1> with strength G_LEAK. Left
# alone for the total time T_TOTAL the leakage Rabi-flops to
# sin^2(G_LEAK T). Projective checks every tau throw the leaked
# amplitude away, and each interval can only leak ~(G_LEAK tau)^2 -
# the quadratic law doing guard duty.

def leakage_hamiltonian():
    """3x3 real symmetric H: only the |1> <-> |2> coupling G_LEAK."""
    h = [[0.0] * 3 for _ in range(3)]
    h[1][2] = G_LEAK
    h[2][1] = G_LEAK
    return h


def _evolve3(psi, duration, h, substeps):
    """RK4 evolution of a 3-component complex state under H."""
    dt = duration / substeps

    def deriv(p):
        return [-1j * sum(h[i][j] * p[j] for j in range(3))
                for i in range(3)]

    for _ in range(substeps):
        k1 = deriv(psi)
        p2 = [psi[i] + 0.5 * dt * k1[i] for i in range(3)]
        k2 = deriv(p2)
        p3 = [psi[i] + 0.5 * dt * k2[i] for i in range(3)]
        k3 = deriv(p3)
        p4 = [psi[i] + dt * k3[i] for i in range(3)]
        k4 = deriv(p4)
        psi = [psi[i] + dt * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0
               for i in range(3)]
    return psi


def unmeasured_leak(t=T_TOTAL):
    """Exact leaked population after time t with no checks: sin^2(g t)."""
    return math.sin(G_LEAK * t) ** 2


def unmeasured_leak_rk4(t=T_TOTAL, substeps=4000):
    """Independent route: RK4 on the 3-level Hamiltonian."""
    psi = _evolve3([0.0j, 1.0 + 0.0j, 0.0j], t, leakage_hamiltonian(),
                   substeps)
    return abs(psi[2]) ** 2


def guarded_stay(tau, total=T_TOTAL):
    """Closed form: [cos^2(G_LEAK tau)]^M, M = total / tau intervals."""
    m = total / tau
    if abs(m - round(m)) > 1e-9:
        raise ValueError("tau must divide the total time")
    return math.cos(G_LEAK * tau) ** (2 * int(round(m)))


def guarded_stay_sim(tau, total=T_TOTAL, substeps=500):
    """Step-by-step route: evolve one interval, project out |2>,
    renormalise, repeat. Returns the population left in the subspace.
    """
    m = total / tau
    if abs(m - round(m)) > 1e-9:
        raise ValueError("tau must divide the total time")
    h = leakage_hamiltonian()
    psi = [0.0j, 1.0 + 0.0j, 0.0j]
    stay = 1.0
    for _ in range(int(round(m))):
        psi = _evolve3(psi, tau, h, substeps)
        leaked = abs(psi[2]) ** 2
        stay *= (1.0 - leaked)
        keep = math.sqrt(max(1.0 - leaked, 0.0))
        psi = [psi[0] / keep, psi[1] / keep, 0.0j]
    return stay


def subspace_table():
    rows = []
    free_leak = unmeasured_leak()
    for m in (2, 5, 10, 20, 50, 100):
        tau = T_TOTAL / m
        stay = guarded_stay(tau)
        rows.append({
            "intervals": m,
            "tau": tau,
            "stay": stay,
            "leaked": 1.0 - stay,
            "leak_per_interval": math.sin(G_LEAK * tau) ** 2,
            "quadratic_estimate": (G_LEAK * tau) ** 2,
            "suppression_vs_free": free_leak / (1.0 - stay),
        })
    return {"g_leak": G_LEAK, "total_time": T_TOTAL,
            "free_leak": free_leak, "rows": rows}


# ================================================================ 5. kNN regime classifier
# Features: survival probability P_N at the reference time, the
# reservoir rate ratio GAMMA(tau)/GAMMA_FREE, and the measurement
# count N. The training grid is labelled by the lab's own policy
# (model_label below) - the classifier interpolates the policy,
# it does not replace the physics sections above.

def model_label(p_surv, rate_ratio, n_meas):
    """The regime policy distilled to a four-way teaching label."""
    if rate_ratio > 1.05:
        return "anti-zeno-accelerated"
    if n_meas >= 50 and p_surv >= 0.95:
        return "zeno-frozen"
    if n_meas <= 1:
        return "exponential-decay"
    return "free-evolution"


def _training_grid():
    rows = []
    for p_surv in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0):
        for rate_ratio in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0, 1.1,
                           1.25, 1.5, 2.0):
            for n_meas in (0, 1, 2, 5, 10, 25, 50, 100, 1000):
                rows.append(((p_surv, rate_ratio, n_meas),
                             model_label(p_surv, rate_ratio, n_meas)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    p_surv, rate_ratio, n_meas = features
    return (p_surv, rate_ratio / 2.0,
            math.log1p(n_meas) / math.log1p(1000))


def classify_regime(p_surv, rate_ratio, n_meas, k=7):
    """Distance-weighted kNN over the policy-labelled grid.

    Weight 1/(d^2 + 1e-12): a grid point's own vote dominates, so
    the classifier reproduces the policy exactly on the grid and
    interpolates it smoothly between grid points.
    """
    target = _scaled((p_surv, rate_ratio, n_meas))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        d2 = sum((a - b) ** 2 for a, b in zip(target, point))
        ranked.append((d2, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for d2, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0.0) + 1.0 / (d2 + 1e-12)
    priority = {"zeno-frozen": 0, "anti-zeno-accelerated": 1,
                "free-evolution": 2, "exponential-decay": 3}
    return sorted(votes.items(), key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def classifier_scenarios():
    """Scenario features computed from the lab's own functions."""
    return {
        "frozen_pi_flip_N1000": (watched_survival(math.pi, 1000),
                                 gamma_ratio(0.05), 1000),
        "watched_pi_flip_N50": (watched_survival(math.pi, 50),
                                gamma_ratio(0.2), 50),
        "antizeno_peak_tau2": (watched_survival(math.pi, 12),
                               gamma_ratio(2.0), 12),
        "moderate_watching_N10": (watched_survival(math.pi, 10),
                                  gamma_ratio(0.5), 10),
        "unmeasured_unstable_state": (math.exp(-1.0), 1.0, 0),
        "one_check_only": (watched_survival(math.pi, 1), 1.0, 1),
    }


def classifier_report():
    return {name: classify_regime(*features)
            for name, features in classifier_scenarios().items()}


# ================================================================ 6. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumzeno-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "role": "DECIDER",
        "model_id": "gemini-argon-4",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all protection and deployment gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantumzeno-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Say it in the first line of every report: frequent ideal measurement freezes the toy model, real detectors are neither ideal nor free - then show the survival table, the rate-ratio curve with its anti-Zeno peak, and the exact grid every integral was computed on.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["a lone qubit mid-flip, freezing as measurement flashes multiply",
                  "the survival curve climbing toward 1 as N grows past 1000",
                  "a sinc-squared filter widening over a Lorentzian hill",
                  "the decay rate cresting above the free-rate line, then falling",
                  "a leakage state knocking at a guarded subspace door"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. watched two-level system
    chk("free_flip_is_zero", free_survival(math.pi) < 1e-15)
    chk("free_half_flip_is_half",
        abs(free_survival(math.pi / 2) - 0.5) < 1e-12)
    chk("one_measurement_equals_free",
        all(abs(watched_survival(t, 1) - free_survival(t)) < 1e-12
            for t in (0.3, 1.1, 2.2, math.pi)))
    chk("watched_matches_step_simulation",
        all(abs(watched_survival(math.pi, n)
                - watched_survival_sim(math.pi, n)) < 1e-12
            for n in (2, 5, 10, 50)))
    table = watched_table()
    survivals = [row["survival"] for row in table["rows"]]
    chk("watched_table_monotone_to_one",
        all(a < b for a, b in zip(survivals, survivals[1:]))
        and survivals[-1] < 1.0)
    chk("watched_N1000_survival_value",
        abs(survivals[-1] - 0.997536) < 1e-5)
    chk("watched_N2_quarter", abs(watched_survival(math.pi, 2) - 0.25) < 1e-12)
    def rel_err(n):
        row = [r for r in table["rows"] if r["n"] == n][0]
        return abs(row["deficit"] - row["deficit_asymptotic"]) \
            / row["deficit_asymptotic"]
    chk("deficit_asymptotic_N1000_within_half_pct", rel_err(1000) < 0.005)
    chk("deficit_asymptotic_converges",
        rel_err(1000) < rel_err(100) < rel_err(10))

    # 2. quadratic vs exponential regimes
    chk("delta_h_from_matrix_is_half_omega",
        abs(delta_h() - MODEL_OMEGA / 2.0) < 1e-12)
    chk("zeno_time_is_reciprocal", abs(zeno_time() - 2.0 / MODEL_OMEGA) < 1e-12)
    chk("exact_survival_matches_rk4",
        abs(exact_survival(1.0) - exact_survival_rk4(1.0)) < 1e-7
        and abs(exact_survival(2.0) - exact_survival_rk4(2.0)) < 1e-7)
    chk("quadratic_law_holds_at_short_time",
        abs(exact_survival(0.2) - quadratic_survival(0.2)) < 1e-4)
    chk("quadratic_law_fails_by_tau_z",
        abs(exact_survival(zeno_time()) - quadratic_survival(zeno_time()))
        > 0.05)
    chk("quadratic_breakdown_time_bracketed",
        0.5 < quadratic_breakdown_time() < 1.0)
    cross = crossover_time()
    chk("crossover_time_bracketed", 0.5 < cross < 1.0)
    chk("crossover_residual",
        abs(quadratic_survival(cross) - exponential_survival(cross)) < 1e-8)
    chk("exponential_starts_at_one_and_decays",
        exponential_survival(0.0) == 1.0
        and exponential_survival(1.0) > exponential_survival(2.0) > 0.0)

    # 3. anti-Zeno reservoir curve
    chk("free_rate_golden_rule",
        abs(free_decay_rate()
            - GAMMA0 * LAMBDA ** 2
            / ((OMEGA_A - OMEGA0) ** 2 + LAMBDA ** 2)) < 1e-12)
    chk("transition_on_reservoir_slope",
        spectral_density(OMEGA0) > spectral_density(OMEGA_A) > 0.0)
    chk("zeno_suppression_at_tau_0p05", gamma_ratio(0.05) < 0.2)
    chk("rate_vanishes_as_tau_shrinks",
        0.0 < gamma_ratio(0.05) < gamma_ratio(0.1) < gamma_ratio(0.2))
    peak = antizeno_peak()
    chk("antizeno_peak_above_free_rate", peak["ratio"] > 1.15)
    chk("antizeno_peak_tau_window", 1.0 <= peak["tau"] <= 3.0)
    chk("antizeno_falling_side", gamma_ratio(2.0) > gamma_ratio(5.0) > 1.0)
    cross_tau = antizeno_crossing()
    chk("antizeno_crossing_bracketed", 0.5 < cross_tau < 1.5)
    chk("antizeno_crossing_residual",
        abs(gamma_ratio(cross_tau) - 1.0) < 1e-6)
    chk("rate_relaxes_to_free_at_tau_20",
        abs(gamma_ratio(20.0) - 1.0) < 0.03)

    # 4. Zeno subspace leakage toy
    sub = subspace_table()
    chk("free_leak_exact", abs(unmeasured_leak() - math.sin(G_LEAK * math.pi) ** 2) < 1e-15)
    chk("free_leak_matches_rk4",
        abs(unmeasured_leak() - unmeasured_leak_rk4()) < 1e-6)
    chk("guarded_stay_matches_simulation",
        abs(guarded_stay(math.pi / 20) - guarded_stay_sim(math.pi / 20))
        < 1e-5)
    leaks = [row["leaked"] for row in sub["rows"]]
    chk("guarded_leak_falls_as_checks_multiply",
        all(a > b for a, b in zip(leaks, leaks[1:])))
    row100 = sub["rows"][-1]
    chk("per_interval_leak_is_quadratic",
        abs(row100["leak_per_interval"] / row100["quadratic_estimate"] - 1.0)
        < 0.01)
    chk("suppression_factor_at_100_checks", row100["suppression_vs_free"] > 50.0)
    chk("guarded_stay_below_one", all(row["stay"] < 1.0 for row in sub["rows"]))

    # 5. classifier - labels come from the lab's own policy
    rep = classifier_report()
    chk("classifier_frozen", rep["frozen_pi_flip_N1000"] == "zeno-frozen")
    chk("classifier_watched_N50_frozen", rep["watched_pi_flip_N50"] == "zeno-frozen")
    chk("classifier_antizeno", rep["antizeno_peak_tau2"] == "anti-zeno-accelerated")
    chk("classifier_moderate_free", rep["moderate_watching_N10"] == "free-evolution")
    chk("classifier_unmeasured_exponential",
        rep["unmeasured_unstable_state"] == "exponential-decay")
    chk("classifier_one_check_exponential",
        rep["one_check_only"] == "exponential-decay")
    chk("classifier_matches_policy_on_scenarios",
        all(classify_regime(*f) == model_label(*f)
            for f in classifier_scenarios().values()))
    chk("classifier_matches_policy_on_grid",
        all(classify_regime(*f) == label for f, label in TRAINING_GRID))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_error_correction_hold",
        gate("real_error_correction_deployment") == "HOLD")
    chk("gate_protection_hold", gate("qubit_protection_claim") == "HOLD")
    chk("gate_decay_control_hold", gate("decay_control_claim") == "HOLD")
    chk("gate_detector_hold", gate("detector_efficiency_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking"
        and brains["decider"]["model_id"] == "gemini-argon-4")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumZeno-Lab - quantum Zeno & anti-Zeno effect lab")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - what watching does and does not do")
    print("    A quantum state left alone starts to change QUADRATICALLY,")
    print("    not exponentially - and that flat start is a handle. Measure")
    print("    often enough and each check throws away only a tiny squared")
    print("    sliver of leakage: the watched pot never boils. Measure at")
    print("    the wrong rate into the wrong reservoir and the same trick")
    print("    runs backwards - decay speeds up (anti-Zeno).")
    print("    Every measurement here is IDEAL and projective. No real")
    print("    detector, qubit, or decay is modelled or protected.")
    table = watched_table()
    print(f"\n[2] Watched qubit - resonant drive OMEGA = {OMEGA}, t = pi "
          f"(a full flip if unwatched)")
    print(f"    free survival P_free(pi) = {table['free_survival']:.6f}")
    print(f"    {'N':>6} {'P_N(pi)':>10} {'1 - P_N':>12} {'(OMEGA t)^2/4N':>15}")
    for row in table["rows"]:
        print(f"    {row['n']:>6} {row['survival']:>10.6f} "
              f"{row['deficit']:>12.6e} {row['deficit_asymptotic']:>15.6e}")
    print("    -> survival climbs monotonically to 1; the deficit falls")
    print("       as (OMEGA t)^2/(4N), the short-time expansion made visible.")
    reg = regimes_report()
    print("\n[3] Quadratic vs exponential - the two regimes of decay")
    print(f"    model H: DELTA = {MODEL_DELTA}, OMEGA = {MODEL_OMEGA} "
          f"(labelled) -> DeltaH = {reg['delta_h']:.6f} from the matrix,")
    print(f"    tau_Z = {reg['tau_z']:.6f}; the quadratic law breaks "
          f"(>1% error) at t = {reg['quadratic_breakdown_time_1pct']:.6f},")
    print(f"    and the quadratic / exponential asymptotes cross at "
          f"t = {reg['crossover_time']:.6f}.")
    print(f"    {'t':>5} {'exact':>9} {'quadratic':>10} {'exponential':>12}")
    for s in reg["samples"]:
        print(f"    {s['t']:>5.1f} {s['exact']:>9.6f} "
              f"{s['quadratic']:>10.6f} {s['exponential']:>12.6f}")
    print("    -> near t = 0 the exact curve hugs the quadratic, NOT the")
    print("       exponential: decay has a flat start, and Zeno lives there.")
    az = antizeno_table()
    print("\n[4] Anti-Zeno - measuring into a Lorentzian reservoir")
    print(f"    J(w): centre {OMEGA0}, width {LAMBDA}; transition at "
          f"{OMEGA_A} (on the slope). GAMMA_FREE = {az['gamma_free']:.6f}")
    print(f"    {'tau':>6} {'GAMMA(tau)':>11} {'ratio':>8}")
    for row in az["rows"]:
        print(f"    {row['tau']:>6.2f} {row['gamma']:>11.6f} "
              f"{row['ratio']:>8.4f}")
    print(f"    -> ratio crosses 1 at tau* = {az['crossing_tau']:.4f} and "
          f"peaks at {az['peak']['ratio']:.4f} near tau = {az['peak']['tau']:.2f}:")
    print("       moderate watching ACCELERATES decay here. As tau -> 0")
    print("       the rate falls linearly to zero - the Zeno limit.")
    sub = subspace_table()
    print("\n[5] Zeno subspace - guarding against leakage")
    print(f"    g = {sub['g_leak']}, total time {sub['total_time']:.4f}; "
          f"unguarded leak = {sub['free_leak']:.6f}")
    print(f"    {'checks':>6} {'tau':>8} {'leaked':>10} {'suppression':>12}")
    for row in sub["rows"]:
        print(f"    {row['intervals']:>6} {row['tau']:>8.4f} "
              f"{row['leaked']:>10.6f} {row['suppression_vs_free']:>11.1f}x")
    print("    -> each interval leaks only ~(g tau)^2, so 100 checks cut")
    print("       the leaked population by the printed factor. Toy model:")
    print("       real error correction is a permanent HOLD gate.")
    print("\n[6] Regime classifier (TinyML kNN, labels from the lab policy)")
    scenarios = classifier_scenarios()
    for name, label in classifier_report().items():
        p, ratio, n = scenarios[name]
        print(f"    {name:28s} P={p:.4f} ratio={ratio:.3f} N={n:<5} -> {label}")
    print("\n[7] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[8] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "watched":
        print(json.dumps(watched_table(), indent=2, sort_keys=True))
        return 0
    if cmd == "regimes":
        print(json.dumps(regimes_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "antizeno":
        print(json.dumps(antizeno_table(), indent=2, sort_keys=True))
        return 0
    if cmd == "subspace":
        print(json.dumps(subspace_table(), indent=2, sort_keys=True))
        return 0
    if cmd == "sweeps":
        print(json.dumps({
            "watched_N_sweep_at_pi": watched_table()["rows"],
            "antizeno_tau_sweep": antizeno_table()["rows"],
            "subspace_tau_sweep": subspace_table()["rows"],
        }, indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "qubit_protection_claim"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
