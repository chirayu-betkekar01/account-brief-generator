"""Building and reading the (informational) grounding check request. No AWS calls."""

import json

from brief_ground import MAX_QUERY, MAX_RESPONSE, MAX_SOURCE, build_content, build_source, extract_scores


def passage(text, score, title="T"):
    return {"text": text, "score": score, "title": title, "source_url": "https://example.com", "topic": "x", "checked_on": "d"}


def test_source_includes_profile_usable_passages_and_roi_but_not_weak_passages():
    results = [
        json.dumps({"found": True, "profile": {"industry": "Logistics", "workloads": ["Batch"]}}),
        json.dumps({"found": True, "results": [passage("Strong passage.", 0.72), passage("Pizza passage.", 0.534)]}),
        json.dumps({"ok": True, "totals": {"roi_pct": 69.4}, "years": []}),
    ]
    source = build_source(results)
    assert "industry: Logistics" in source
    assert "Strong passage." in source
    assert "Pizza passage." not in source  # below the 0.60 relevance threshold
    assert "69.4" in source


def test_source_skips_results_that_are_not_json():
    assert build_source(["not json", "[1, 2]"]) == ""


def test_content_blocks_carry_the_right_qualifiers_in_the_right_order():
    blocks = build_content("source", "query", "answer")
    assert [b["text"]["qualifiers"] for b in blocks] == [["grounding_source"], ["query"], ["guard_content"]]
    assert [b["text"]["text"] for b in blocks] == ["source", "query", "answer"]


def test_content_is_trimmed_to_the_documented_limits():
    blocks = build_content("s" * (MAX_SOURCE + 50), "q" * (MAX_QUERY + 50), "a" * (MAX_RESPONSE + 50))
    assert [len(b["text"]["text"]) for b in blocks] == [MAX_SOURCE, MAX_QUERY, MAX_RESPONSE]


def test_scores_are_read_from_the_response():
    response = {
        "action": "GUARDRAIL_INTERVENED",
        "assessments": [
            {"contextualGroundingPolicy": {"filters": [
                {"type": "GROUNDING", "score": 0.1712, "threshold": 0.75, "action": "BLOCKED", "detected": True},
                {"type": "RELEVANCE", "score": 0.45, "threshold": 0.5, "action": "BLOCKED", "detected": True},
            ]}},
            {"topicPolicy": {"topics": []}},
        ],
    }
    assert extract_scores(response) == {"GROUNDING": 0.17, "RELEVANCE": 0.45}


def test_no_grounding_assessment_gives_no_scores():
    assert extract_scores({"action": "NONE", "assessments": [{"topicPolicy": {}}]}) == {}
    assert extract_scores({}) == {}
