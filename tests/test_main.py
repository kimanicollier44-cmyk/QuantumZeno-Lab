"""Tests for QuantumZeno-Lab: watched qubit, regimes, anti-Zeno, subspace."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as lab


# ---------------- watched two-level system ----------------

def test_free_survival_full_flip():
    assert lab.free_survival(math.pi) < 1e-15


def test_free_survival_half_flip():
    assert abs(lab.free_survival(math.pi / 2) - 0.5) < 1e-12


def test_one_measurement_equals_free():
    for t in (0.3, 1.1, 2.2):
        assert abs(lab.watched_survival(t, 1) - lab.free_survival(t)) < 1e-12


def test_watched_two_measurements_quarter():
    assert abs(lab.watched_survival(math.pi, 2) - 0.25) < 1e-12


def test_watched_matches_step_simulation():
    for n in (2, 5, 10, 50):
        assert abs(lab.watched_survival(math.pi, n)
                   - lab.watched_survival_sim(math.pi, n)) < 1e-12


def test_watched_table_monotone():
    survivals = [r["survival"] for r in lab.watched_table()["rows"]]
    assert all(a < b for a, b in zip(survivals, survivals[1:]))
    assert abs(survivals[-1] - 0.997536) < 1e-5


def test_deficit_asymptotic_converges():
    rows = {r["n"]: r for r in lab.watched_table()["rows"]}

    def rel(n):
        return abs(rows[n]["deficit"] - rows[n]["deficit_asymptotic"]) \
            / rows[n]["deficit_asymptotic"]

    assert rel(1000) < 0.005
    assert rel(1000) < rel(100) < rel(10)


# ---------------- quadratic vs exponential regimes ----------------

def test_delta_h_from_matrix():
    assert abs(lab.delta_h() - lab.MODEL_OMEGA / 2.0) < 1e-12


def test_zeno_time():
    assert abs(lab.zeno_time() - 2.0) < 1e-12


def test_exact_survival_matches_rk4():
    assert abs(lab.exact_survival(1.0) - lab.exact_survival_rk4(1.0)) < 1e-7


def test_quadratic_law_short_time():
    assert abs(lab.exact_survival(0.2) - lab.quadratic_survival(0.2)) < 1e-4


def test_quadratic_law_fails_at_tau_z():
    gap = abs(lab.exact_survival(lab.zeno_time())
              - lab.quadratic_survival(lab.zeno_time()))
    assert gap > 0.05


def test_crossover_time():
    cross = lab.crossover_time()
    assert 0.5 < cross < 1.0
    assert abs(lab.quadratic_survival(cross)
               - lab.exponential_survival(cross)) < 1e-8


def test_quadratic_breakdown_bracket():
    assert 0.5 < lab.quadratic_breakdown_time() < 1.0


# ---------------- anti-Zeno reservoir ----------------

def test_free_rate_golden_rule():
    expected = lab.GAMMA0 * lab.LAMBDA ** 2 / (
        (lab.OMEGA_A - lab.OMEGA0) ** 2 + lab.LAMBDA ** 2)
    assert abs(lab.free_decay_rate() - expected) < 1e-12


def test_transition_on_slope():
    assert lab.spectral_density(lab.OMEGA0) > lab.spectral_density(lab.OMEGA_A)


def test_zeno_suppression_small_tau():
    assert lab.gamma_ratio(0.05) < 0.2
    assert 0.0 < lab.gamma_ratio(0.05) < lab.gamma_ratio(0.1) \
        < lab.gamma_ratio(0.2)


def test_antizeno_peak():
    peak = lab.antizeno_peak()
    assert peak["ratio"] > 1.15
    assert 1.0 <= peak["tau"] <= 3.0


def test_antizeno_crossing():
    tau_star = lab.antizeno_crossing()
    assert 0.5 < tau_star < 1.5
    assert abs(lab.gamma_ratio(tau_star) - 1.0) < 1e-6


def test_rate_relaxes_to_free():
    assert abs(lab.gamma_ratio(20.0) - 1.0) < 0.03
    assert lab.gamma_ratio(2.0) > lab.gamma_ratio(5.0) > 1.0


# ---------------- Zeno subspace ----------------

def test_free_leak_exact_and_rk4():
    assert abs(lab.unmeasured_leak()
               - math.sin(lab.G_LEAK * math.pi) ** 2) < 1e-15
    assert abs(lab.unmeasured_leak() - lab.unmeasured_leak_rk4()) < 1e-6


def test_guarded_stay_matches_simulation():
    assert abs(lab.guarded_stay(math.pi / 20)
               - lab.guarded_stay_sim(math.pi / 20)) < 1e-5


def test_guarded_leak_monotone_and_suppression():
    rows = lab.subspace_table()["rows"]
    leaks = [r["leaked"] for r in rows]
    assert all(a > b for a, b in zip(leaks, leaks[1:]))
    assert rows[-1]["suppression_vs_free"] > 50.0


def test_per_interval_leak_quadratic():
    row = lab.subspace_table()["rows"][-1]
    ratio = row["leak_per_interval"] / row["quadratic_estimate"]
    assert abs(ratio - 1.0) < 0.01


# ---------------- classifier + gates + seats ----------------

def test_classifier_scenarios():
    rep = lab.classifier_report()
    assert rep["frozen_pi_flip_N1000"] == "zeno-frozen"
    assert rep["antizeno_peak_tau2"] == "anti-zeno-accelerated"
    assert rep["moderate_watching_N10"] == "free-evolution"
    assert rep["unmeasured_unstable_state"] == "exponential-decay"


def test_classifier_matches_policy_on_grid():
    assert all(lab.classify_regime(*f) == label
               for f, label in lab.TRAINING_GRID)


def test_hold_gates():
    assert len(lab.HOLD_GATES) == 14
    assert lab.gate("qubit_protection_claim") == "HOLD"
    assert lab.gate("real_error_correction_deployment") == "HOLD"
    assert lab.gate("run_simulation") == "PROCEED"


def test_seats_cannot_override():
    brains = lab.brains_report()
    assert brains["decider"]["can_override_hold"] is False
    assert brains["decider"]["model_id"] == "gemini-argon-4"
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0
