"""Gate G8: dataset shape, ID traceability (III) and synthetic inputs (XII)."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
MIN_CASES = 20
MIN_PER_CATEGORY = 3
CATEGORIES = (
    "normal",
    "boundary",
    "ambiguous",
    "missing_information",
    "malformed",
    "adversarial",
)
CASE_KEYS = {
    "id",
    "category",
    "guardrail",
    "embedded_instruction",
    "request",
    "expected",
    "accepted_tasks",
    "covers",
}
ID_DEFINITION = re.compile(r"\*\*((?:FR|INV|PROP)-\d{3})\*\*:")
ID_REFERENCE = re.compile(r"\b(?:FR|INV|PROP)-\d{3}\b")
CASE_ID = re.compile(r"^EVAL-\d{3}$")
COVERS_MARKER = re.compile(r"mark\.covers\(([^)]*)\)")
PATTERNS = {
    "e-mail": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"\+?\d[\d ().-]{7,}\d"),
    "URL": re.compile(
        r"https?://|www\.|\b[\w-]+\.(?:com|org|net|io|test)\b", re.IGNORECASE
    ),
}


def spec_ids(root: Path) -> set[str]:
    """Return the FR/INV/PROP ids defined in the spec named by the dataset."""
    dataset = json.loads((root / "evals" / "dataset.json").read_text(encoding="utf-8"))
    text = (root / dataset["spec"]).read_text(encoding="utf-8")
    return set(ID_DEFINITION.findall(text))


def duplicate_spec_ids(root: Path) -> list[str]:
    """Return ids defined more than once in the spec."""
    dataset = json.loads((root / "evals" / "dataset.json").read_text(encoding="utf-8"))
    text = (root / dataset["spec"]).read_text(encoding="utf-8")
    counts = Counter(ID_DEFINITION.findall(text))
    return sorted(name for name, count in counts.items() if count > 1)


def ids_cited_by_tests(root: Path) -> set[str]:
    """Return ids named in ``@pytest.mark.covers(...)`` markers under tests/."""
    cited: set[str] = set()
    for path in sorted((root / "tests").glob("*.py")):
        for args in COVERS_MARKER.findall(path.read_text(encoding="utf-8")):
            cited.update(ID_REFERENCE.findall(args))
    return cited


def uncited(ids: set[str], cited: set[str]) -> list[str]:
    """Return defined ids that nothing cites, sorted."""
    return sorted(ids - cited)


def _expected_due_problems(case: dict) -> list[str]:
    due = case["expected"].get("due")
    if due is None:
        return []
    request = case["request"]
    try:
        instant = datetime.fromisoformat(due)
        now = datetime.fromisoformat(request["now"])
        zone = ZoneInfo(request["timezone"])
    except (ValueError, ZoneInfoNotFoundError):
        return [f"{case['id']}: unparseable expected due, now or timezone"]
    problems = []
    if instant.astimezone(zone).utcoffset() != instant.utcoffset():
        problems.append(f"{case['id']}: expected due has the wrong offset")
    if instant < now:
        problems.append(f"{case['id']}: expected due is before now")
    return problems


def _case_problems(
    case: dict, ids: set[str], validator: jsonschema.Validator
) -> list[str]:
    cid = case.get("id", "?")
    if set(case) != CASE_KEYS:
        return [f"{cid}: keys must be exactly {sorted(CASE_KEYS)}"]
    problems = []
    if not CASE_ID.match(cid):
        problems.append(f"{cid}: id must look like EVAL-nnn")
    if case["category"] not in CATEGORIES:
        problems.append(f"{cid}: unknown category {case['category']}")
    if not case["covers"]:
        problems.append(f"{cid}: empty covers")
    problems += [
        f"{cid}: covers unknown id {i}" for i in case["covers"] if i not in ids
    ]
    if not validator.is_valid(case["expected"]):
        problems.append(f"{cid}: expected output fails the output schema")
    must_guard = (
        case["expected"]["decision"] == "refuse" or case["embedded_instruction"]
    )
    if must_guard and case["guardrail"] is not True:
        problems.append(
            f"{cid}: refuse/embedded-instruction case must be a guardrail case"
        )
    if case["expected"]["task"] is not None and not case["accepted_tasks"]:
        problems.append(f"{cid}: accepted_tasks empty although a task is expected")
    text = case["request"].get("text", "")
    problems += [
        f"{cid}: input contains {kind}"
        for kind, p in PATTERNS.items()
        if p.search(text)
    ]
    return problems + _expected_due_problems(case)


def dataset_violations(dataset: dict, ids: set[str]) -> list[str]:
    """Return every rule the dataset breaks (empty list when it is valid)."""
    schema = json.loads(
        (ROOT / ".harness" / "output.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)
    cases = dataset.get("cases", [])
    problems = []
    if dataset.get("synthetic") is not True:
        problems.append('dataset must declare "synthetic": true')
    if len(cases) < MIN_CASES:
        problems.append(
            f"dataset must hold at least {MIN_CASES} cases, has {len(cases)}"
        )
    counts = Counter(case.get("category") for case in cases)
    problems += [
        f"category {name} has {counts[name]} cases, needs {MIN_PER_CATEGORY}"
        for name in CATEGORIES
        if counts[name] < MIN_PER_CATEGORY
    ]
    id_counts = Counter(case.get("id") for case in cases)
    problems += [f"duplicate case id {cid}" for cid, n in id_counts.items() if n > 1]
    for case in cases:
        problems += _case_problems(case, ids, validator)
    return problems


def find_violations(root: Path) -> list[str]:
    """Run every G8 check against the repository at ``root``."""
    dataset = json.loads((root / "evals" / "dataset.json").read_text(encoding="utf-8"))
    ids = spec_ids(root)
    problems = [
        f"id defined more than once in spec: {i}" for i in duplicate_spec_ids(root)
    ]
    problems += dataset_violations(dataset, ids)
    cited_by_tests = ids_cited_by_tests(root)
    unknown = sorted(cited_by_tests - ids)
    problems += [f"test marker cites unknown id {i}" for i in unknown]
    cited_by_cases = {
        i for case in dataset.get("cases", []) for i in case.get("covers", [])
    }
    problems += [
        f"id cited by no case or test: {i}"
        for i in uncited(ids, cited_by_cases | cited_by_tests)
    ]
    return problems


def main() -> int:
    """Print every violation; exit 0 only when there are none."""
    problems = find_violations(ROOT)
    for problem in problems:
        sys.stdout.write(f"G8: {problem}\n")
    if not problems:
        sys.stdout.write("G8: dataset and traceability clean\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
