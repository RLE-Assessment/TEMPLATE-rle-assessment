"""Criteria roll-up for the summary table and Criterion B write-back.

Shared by content/3_ecosystem_description.qmd (summary table) and
build_criterion_b.py (writes the computed B1/B2 categories into each
ecosystem.yaml).
"""

import copy

from rle.core import criterion_b_status
from rle.core.rle import rle_categories

CRITERIA = ["A", "B", "C", "D", "E"]

# rle_categories is ordered from most to least threatened (CO ... NE).
_RANK = {c["abbreviation"]: i for i, c in enumerate(rle_categories)}


def most_threatened(values):
    """Return the most-threatened category code in ``values``.

    Values that are not category codes (e.g. sub-condition notes or "TODO") are
    ignored; returns None when no value is a category code.
    """
    categories = [v for v in values if v in _RANK]
    return min(categories, key=_RANK.get) if categories else None


def _is_set(value):
    return value not in (None, "", "TODO")


def criteria_summary(eco):
    """Per-criterion category (A-E) and overall category for one ecosystem.

    Each criterion is the most-threatened of its sub-criteria (NE when none is
    evaluated). ``overall`` is the authored ``assessment_outcome`` when set,
    otherwise the most-threatened of A-E.
    """
    status = eco.get("criteria_status") or {}
    summary = {
        c: most_threatened((status.get(c) or {}).values()) or "NE" for c in CRITERIA
    }
    outcome = eco.get("assessment_outcome")
    summary["overall"] = (
        outcome if _is_set(outcome)
        else most_threatened(summary[c] for c in CRITERIA)
    )
    return summary


def with_criterion_b(eco, eoo_km2, aoo_cells):
    """Return a copy of ``eco`` with B1/B2 set from the EOO/AOO spatial thresholds.

    A metric that is None leaves its sub-criterion as authored; B3 and the a-c
    sub-conditions are never touched (not derivable from the spatial metrics).
    """
    out = copy.deepcopy(eco)
    b = criterion_b_status(eoo_km2=eoo_km2, aoo_cells=aoo_cells)
    status = out.setdefault("criteria_status", {})
    b_row = status.setdefault("B", {})
    for sub in ("B1", "B2"):
        if b[sub] is not None:
            b_row[sub] = b[sub]
    return out
