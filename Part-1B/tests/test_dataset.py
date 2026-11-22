"""Dataset shape and ID traceability (FR-025, FR-026, constitution III and XII)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import check_dataset
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATASET = json.loads((ROOT / "evals" / "dataset.json").read_text())


@pytest.mark.covers("FR-025", "FR-026")
def test_repository_dataset_has_no_violations():
    assert check_dataset.find_violations(ROOT) == []


@pytest.mark.covers("FR-025")
def test_dataset_counts():
    cases = DATASET["cases"]
    assert DATASET["synthetic"] is True
    assert len(cases) >= 20
    for category in check_dataset.CATEGORIES:
        assert sum(1 for c in cases if c["category"] == category) >= 3, category


def _violations_for(mutate):
    dataset = copy.deepcopy(DATASET)
    mutate(dataset)
    return check_dataset.dataset_violations(dataset, check_dataset.spec_ids(ROOT))


@pytest.mark.covers("FR-025")
@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda d: d.update(synthetic=False), "synthetic"),
        (lambda d: d["cases"][1].update(id=d["cases"][0]["id"]), "duplicate"),
        (lambda d: d["cases"][0].update(covers=[]), "covers"),
        (lambda d: d["cases"][0].update(covers=["FR-999"]), "FR-999"),
        (
            lambda d: d["cases"][0]["request"].update(text="mail ana@example.org"),
            "e-mail",
        ),
        (
            lambda d: d["cases"][0]["request"].update(text="call +44 20 7946 0000"),
            "phone",
        ),
        (lambda d: d["cases"][0]["request"].update(text="see https://x.test"), "URL"),
        (lambda d: d["cases"][0]["expected"].update(extra=1), "schema"),
        (
            lambda d: d["cases"][0]["expected"].update(due="2026-03-05T09:00:00+00:00"),
            "offset",
        ),
        (lambda d: d["cases"][22].update(guardrail=False), "guardrail"),
        (lambda d: d.update(cases=d["cases"][:19]), "at least 20"),
    ],
)
def test_checker_rejects_broken_datasets(mutate, fragment):
    found = _violations_for(mutate)
    assert any(fragment in item for item in found), found


@pytest.mark.covers("FR-026")
def test_uncited_id_is_reported(tmp_path):
    ids = {"FR-001", "FR-002"}
    cited = {"FR-001"}
    assert check_dataset.uncited(ids, cited) == ["FR-002"]
