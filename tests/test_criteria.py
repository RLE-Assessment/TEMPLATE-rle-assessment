"""Tests for the criteria roll-up (summary table) and Criterion B write-back."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from _criteria import criteria_summary, most_threatened, with_criterion_b  # noqa: E402


def _eco(**criteria):
    """An ecosystem config with every sub-criterion NE, overridden by ``criteria``."""
    status = {
        "A": {"A1": "NE", "A2a": "NE", "A2b": "NE", "A3": "NE"},
        "B": {"B1": "NE", "B2": "NE", "subcriteria": "NE", "B3": "NE"},
        "C": {"C1": "NE", "C2a": "NE", "C2b": "NE", "C3": "NE"},
        "D": {"D1": "NE", "D2a": "NE", "D2b": "NE", "D3": "NE"},
        "E": {"E": "NE"},
    }
    for criterion, subs in criteria.items():
        status[criterion].update(subs)
    return {"global_classification": "T1.1.1", "criteria_status": status,
            "assessment_outcome": "TODO"}


# --- most_threatened ---------------------------------------------------------

def test_most_threatened_picks_highest_risk():
    assert most_threatened(["LC", "EN", "VU", "NE"]) == "EN"


def test_most_threatened_all_not_evaluated():
    assert most_threatened(["NE", "NE"]) == "NE"


def test_most_threatened_ignores_non_category_values():
    assert most_threatened(["a(i)", None, "VU", "TODO"]) == "VU"


def test_most_threatened_no_categories_is_none():
    assert most_threatened(["TODO", None]) is None


# --- criteria_summary --------------------------------------------------------

def test_summary_rolls_up_each_criterion():
    eco = _eco(A={"A1": "VU", "A3": "EN"}, C={"C2b": "LC"})
    s = criteria_summary(eco)
    assert (s["A"], s["B"], s["C"], s["D"], s["E"]) == ("EN", "NE", "LC", "NE", "NE")


def test_summary_overall_computed_when_outcome_unset():
    eco = _eco(A={"A1": "VU"}, B={"B2": "CR"})
    assert criteria_summary(eco)["overall"] == "CR"


def test_summary_overall_uses_assessment_outcome_when_set():
    eco = _eco(B={"B2": "CR"})
    eco["assessment_outcome"] = "EN"
    assert criteria_summary(eco)["overall"] == "EN"


def test_summary_missing_criteria_status_is_ne():
    s = criteria_summary({"global_classification": "X"})
    assert s == {"A": "NE", "B": "NE", "C": "NE", "D": "NE", "E": "NE", "overall": "NE"}


# --- with_criterion_b --------------------------------------------------------

def test_criterion_b_sets_b1_b2_from_metrics():
    eco = _eco(B={"subcriteria": "a(i)", "B3": "VU"})
    out = with_criterion_b(eco, eoo_km2=1_500, aoo_cells=30)
    assert out["criteria_status"]["B"] == {
        "B1": "CR", "B2": "VU", "subcriteria": "a(i)", "B3": "VU"}


def test_criterion_b_leaves_other_criteria_and_input_untouched():
    eco = _eco(A={"A1": "EN"})
    out = with_criterion_b(eco, eoo_km2=1_500, aoo_cells=30)
    assert out["criteria_status"]["A"]["A1"] == "EN"
    assert eco["criteria_status"]["B"]["B1"] == "NE"  # input not mutated


def test_criterion_b_skips_missing_metric():
    eco = _eco(B={"B2": "EN"})
    out = with_criterion_b(eco, eoo_km2=1_500, aoo_cells=None)
    assert out["criteria_status"]["B"]["B1"] == "CR"
    assert out["criteria_status"]["B"]["B2"] == "EN"


def test_criterion_b_is_idempotent():
    once = with_criterion_b(_eco(), eoo_km2=60_000, aoo_cells=10)
    assert with_criterion_b(once, eoo_km2=60_000, aoo_cells=10) == once
