"""Deterministic checks on a finished brief.

The fixtures in tests/fixtures/briefs are REAL answers and tool results from the live agent
(2026-10-07, system prompt revision 2). They were chosen because the model broke its rules in
different ways: northwind is clean; summit names five AWS services that no retrieved passage
mentions; harborview names one and leaves most architecture bullets without a link.

These checks exist because the contextual grounding filter could not tell these apart (a clean
section scored 0.17, the one with five invented services 0.05).
"""

import json
from pathlib import Path

import pytest

from brief_checks import run_checks

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "briefs"
GOOD_CALLS = ["profile___get_account_profile", "kb___search_knowledge_base", "kb___search_knowledge_base", "roi___estimate_roi"]


def load(slug):
    answer = (FIXTURES / f"{slug}.answer.md").read_text(encoding="utf-8")
    tools = list(json.loads((FIXTURES / f"{slug}.tools.json").read_text(encoding="utf-8")).values())
    return answer, tools


def result(checks, name):
    matches = [c for c in checks if c.name == name]
    assert len(matches) == 1, f"expected exactly one check named {name}, got {[c.name for c in checks]}"
    return matches[0]


def test_a_clean_brief_passes_every_check():
    answer, tools = load("northwind")
    failed = [c for c in run_checks(answer, tools, GOOD_CALLS) if not c.passed]
    assert failed == []


def test_invented_services_are_named_in_the_failure():
    answer, tools = load("summit")
    check = result(run_checks(answer, tools, GOOD_CALLS), "services_supported")
    assert not check.passed
    for invented in ("AWS Lambda", "Amazon CloudWatch", "Amazon EventBridge", "Amazon RDS"):
        assert invented in check.detail


def test_one_invented_service_is_enough_to_fail():
    answer, tools = load("harborview")
    check = result(run_checks(answer, tools, GOOD_CALLS), "services_supported")
    assert not check.passed
    assert "AWS Backup" in check.detail


def test_services_the_passages_do_name_are_not_flagged():
    answer, tools = load("northwind")
    # Northwind recommends Migration Evaluator, Transform MGN, EC2 and S3, all in retrieved passages.
    assert result(run_checks(answer, tools, GOOD_CALLS), "services_supported").passed


def test_architecture_bullets_without_a_link_fail():
    answer, tools = load("harborview")
    check = result(run_checks(answer, tools, GOOD_CALLS), "architecture_bullets_cited")
    assert not check.passed
    assert "3 of 4" in check.detail


def test_all_architecture_bullets_linked_passes():
    answer, tools = load("northwind")
    assert result(run_checks(answer, tools, GOOD_CALLS), "architecture_bullets_cited").passed


def test_footnote_markers_fail():
    answer, tools = load("northwind")
    answer = answer.replace("](https", "][^1](https", 1) + "\n[^1]: note"
    assert not result(run_checks(answer, tools, GOOD_CALLS), "no_footnote_markers").passed


def test_a_link_that_no_retrieved_passage_supplied_fails():
    answer, tools = load("northwind")
    answer += "\nSee [made up](https://example.com/not-retrieved)."
    check = result(run_checks(answer, tools, GOOD_CALLS), "links_from_passages")
    assert not check.passed
    assert "https://example.com/not-retrieved" in check.detail


def test_a_link_to_a_low_scoring_passage_fails():
    answer, tools = load("northwind")
    low = json.dumps(
        {"found": True, "results": [{"text": "Pizza.", "score": 0.534, "title": "Pizza", "topic": "x",
                                      "source_url": "https://example.com/pizza", "checked_on": "2026-10-07"}]}
    )
    answer += "\nSee [Pizza](https://example.com/pizza)."
    check = result(run_checks(answer, tools + [low], GOOD_CALLS), "links_from_passages")
    assert not check.passed  # retrieved, but below the 0.60 relevance threshold the prompt sets


def test_missing_section_fails_structure():
    answer, tools = load("northwind")
    answer = answer.split("## 6.")[0]
    assert not result(run_checks(answer, tools, GOOD_CALLS), "six_sections_in_order").passed


def test_sections_out_of_order_fail_structure():
    answer, tools = load("northwind")
    answer = answer.replace("## 2.", "## TMP").replace("## 3.", "## 2.").replace("## TMP", "## 3.")
    assert not result(run_checks(answer, tools, GOOD_CALLS), "six_sections_in_order").passed


@pytest.mark.parametrize("count,expected", [(7, False), (8, True), (9, True), (10, True), (14, False)])
def test_question_count_must_be_between_eight_and_ten(count, expected):
    answer, tools = load("northwind")
    head, rest = answer.split("## 3. Discovery questions")
    _, tail = rest.split("## 4.")
    questions = "\n".join(f"{i}. Question number {i}?" for i in range(1, count + 1))
    answer = f"{head}## 3. Discovery questions\n{questions}\n\n## 4.{tail}"
    assert result(run_checks(answer, tools, GOOD_CALLS), "question_count_8_to_10").passed is expected


def test_a_changed_roi_number_fails():
    answer, tools = load("northwind")
    assert "5,391,484" in answer
    tampered = answer.replace("5,391,484", "5,391,485")
    check = result(run_checks(tampered, tools, GOOD_CALLS), "roi_numbers_match_tool")
    assert not check.passed
    assert "5391485" in check.detail.replace(",", "")


def test_untouched_roi_numbers_pass():
    answer, tools = load("northwind")
    assert result(run_checks(answer, tools, GOOD_CALLS), "roi_numbers_match_tool").passed


def test_roi_must_be_labelled_preliminary():
    answer, tools = load("northwind")
    stripped = answer.replace("Preliminary", "Final").replace("preliminary", "final")
    assert not result(run_checks(stripped, tools, GOOD_CALLS), "roi_labelled_preliminary").passed


def test_headquarters_must_not_appear():
    answer, tools = load("northwind")
    check = result(run_checks(answer + "\nBased in Columbus.", tools, GOOD_CALLS), "no_headquarters")
    assert not check.passed
    assert "Columbus" in check.detail


def test_tool_call_pattern_one_profile_one_roi_two_or_three_searches():
    answer, tools = load("northwind")
    assert result(run_checks(answer, tools, GOOD_CALLS), "tool_calls_as_instructed").passed
    no_roi = [c for c in GOOD_CALLS if not c.startswith("roi")]
    assert not result(run_checks(answer, tools, no_roi), "tool_calls_as_instructed").passed
    too_many = GOOD_CALLS + ["kb___search_knowledge_base"] * 2
    assert not result(run_checks(answer, tools, too_many), "tool_calls_as_instructed").passed


def test_tool_call_check_is_skipped_when_calls_are_not_supplied():
    answer, tools = load("northwind")
    names = [c.name for c in run_checks(answer, tools)]
    assert "tool_calls_as_instructed" not in names
