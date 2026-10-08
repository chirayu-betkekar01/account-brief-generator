"""Post-answer contextual grounding check, via ApplyGuardrail. INFORMATIONAL ONLY.

The guardrail's grounding filter needs a tagged source, query and answer, which the harness cannot
supply, so the client makes the call itself after the brief is written. Measured on 2026-10-07 it
does not separate faithful sections from ungrounded ones (a clean architecture section scored 0.17,
one with five ungrounded services 0.05), so the result is shown for information and never used to
pass or fail a brief. The deterministic checks in brief_checks.py do that.
"""

import json

from brief_checks import MIN_PASSAGE_SCORE

# Documented limits of the contextual grounding check, in characters.
MAX_SOURCE, MAX_QUERY, MAX_RESPONSE = 100_000, 1_000, 5_000


def build_source(tool_results):
    """The text the answer is supposed to rest on: the profile, usable passages and the ROI result."""
    parts = []
    for text in tool_results:
        try:
            parsed = json.loads(text)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        if "profile" in parsed:
            parts += [f"{key}: {value}" for key, value in parsed["profile"].items()]
        for passage in parsed.get("results", []):
            if passage.get("score", 0) >= MIN_PASSAGE_SCORE:
                parts.append(f"{passage.get('title', '')}. {passage.get('text', '')}")
        if "totals" in parsed:
            parts.append("ROI result: " + json.dumps(parsed))
    return "\n\n".join(parts)


def build_content(source, query, section_text):
    """The three content blocks ApplyGuardrail needs, each trimmed to the documented limit."""
    return [
        {"text": {"text": source[:MAX_SOURCE], "qualifiers": ["grounding_source"]}},
        {"text": {"text": query[:MAX_QUERY], "qualifiers": ["query"]}},
        {"text": {"text": section_text[:MAX_RESPONSE], "qualifiers": ["guard_content"]}},
    ]


def extract_scores(response):
    """{'GROUNDING': 0.17, 'RELEVANCE': 0.45} from an ApplyGuardrail response (empty if none)."""
    scores = {}
    for assessment in response.get("assessments", []):
        for item in assessment.get("contextualGroundingPolicy", {}).get("filters", []):
            scores[item["type"]] = round(float(item["score"]), 2)
    return scores


def ground_section(client, guardrail_id, guardrail_version, source, query, section_text):
    response = client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=guardrail_version,
        source="OUTPUT",
        content=build_content(source, query, section_text),
        outputScope="FULL",
    )
    return extract_scores(response)
