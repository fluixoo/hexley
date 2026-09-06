import numpy as np
import pytest

from chaindesk.agents.profiler import Profiler
from chaindesk.agents.referee import Referee, Rule


def path(*pts):
    return np.array(pts, dtype=float)


@pytest.fixture
def paths():
    return [
        path(1, 1.2, 1.6, 2.1, 3.0, 4.2, 3.0, 2.0, 1.0),  # runs to x4 then fades
        path(1, 0.9, 0.7, 0.5, 0.4, 0.4, 0.4, 0.4, 0.4),  # dies
        path(1, 1.5, 2.2, 1.8, 1.4, 1.1, 1.0, 0.9, 0.8),  # x2 then back
        path(1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),  # flat
    ]


def test_first_hit_times(paths):
    ref = Referee(paths, horizon_min=8)
    assert list(ref.first_hit_up(ref.P, 2.0)) == [3, 9, 2, 9]
    assert list(ref.first_hit_down(ref.P, 0.6)) == [9, 3, 9, 9]
    assert list(ref.first_trail_hit(ref.P, 0.4)) == [7, 3, 5, 9]


def test_full_tp_rule_pays_on_runner(paths):
    ref = Referee(paths, horizon_min=8)
    r = ref.evaluate(Rule(tp=4.0, tp_frac=1.0, stop=None, time_stop_min=8, trail=None))
    # runner: +300%, dead: -60%, x2: -20% (closes at 0.8), flat: 0
    assert r.ev_pct == pytest.approx((3.0 - 0.6 - 0.2 + 0.0) / 4 * 100, abs=0.01)
    assert r.win_rate == 0.25


def test_stop_caps_the_loser(paths):
    ref = Referee(paths, horizon_min=8)
    no_stop = ref.evaluate(Rule(4.0, 1.0, None, 8, None))
    with_stop = ref.evaluate(Rule(4.0, 1.0, 0.6, 8, None))
    assert with_stop.ev_pct > no_stop.ev_pct  # dead path exits at 0.5 instead of 0.4


def test_time_stop_closes_early(paths):
    ref = Referee(paths, horizon_min=8)
    r = ref.evaluate(Rule(10.0, 1.0, None, 2, None))
    # exit at minute 2 for all: 1.6, 0.7, 2.2, 1.0
    assert r.ev_pct == pytest.approx((0.6 - 0.3 + 1.2 + 0.0) / 4 * 100, abs=0.01)


def test_delay_shifts_entry(paths):
    ref = Referee(paths, horizon_min=8)
    zero = ref.evaluate(Rule(2.0, 1.0, None, 8, None), delay_min=0)
    late = ref.evaluate(Rule(2.0, 1.0, None, 8, None), delay_min=2)
    assert late.ev_pct < zero.ev_pct


def test_grid_returns_sorted_top(paths):
    ref = Referee(paths, horizon_min=8)
    top = ref.grid(tps=(2, 4), fracs=(1.0,), stops=(None, 0.6), time_stops=(8,), trails=(None,), top=3)
    assert len(top) == 3
    assert top[0].ev_pct >= top[1].ev_pct >= top[2].ev_pct


def test_profiler_scorecard(paths):
    card = Profiler().score(paths, premiums=[1.05, 1.1, 1.08, 1.0], holds_min=[3, 2, 5, 4])
    assert card.entries == 4
    assert card.p_x2 == 0.5
    assert card.p_x3 == 0.25
    assert card.median_max_x == pytest.approx(1.6, abs=0.01)  # median of (4.2, 1.0, 2.2, 1.0)
    assert card.copier_premium == pytest.approx(1.065, abs=0.001)


def test_bootstrap_ci_brackets_point_estimate():
    rng = np.random.default_rng(1)
    vals = rng.normal(0.2, 1.0, size=200)
    lo, hi = Profiler.bootstrap(vals, n=500)
    assert lo < vals.mean() < hi
