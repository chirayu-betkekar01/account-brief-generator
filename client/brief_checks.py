"""Deterministic checks on a finished brief, using only the tool results the agent was given.

Why these exist: the guardrail's contextual grounding check could not tell a faithful brief from one
with invented AWS services (scores 0.17 against 0.05, both far below any usable threshold), and the
model followed "name only services you were given" in some briefs and not in others. A plain string
comparison against the retrieved passages caught every case in the sample. These checks run in the
client and in the evaluation script; they report, they do not rewrite the answer.
"""

import json
import re
from dataclasses import dataclass

# Must match the rule in agent/system_prompt.md: a passage is only usable at or above this score.
MIN_PASSAGE_SCORE = 0.60
EXPECTED_SECTIONS = [1, 2, 3, 4, 5, 6]
MIN_QUESTIONS, MAX_QUESTIONS = 8, 10

_HEADING = re.compile(r"^## (\d)\. ", re.M)
# "AWS Foo", "Amazon Foo Bar", and names with a lowercase joiner such as "AWS Identity and Access Management".
_SERVICE_NAME = re.compile(r"\b(?:AWS|Amazon) [A-Z][A-Za-z0-9]+(?: (?:and |for |of )?[A-Z][A-Za-z0-9]+){0,3}")
_LINK_URL = re.compile(r"\]\((https?://[^)\s]+)\)")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def split_sections(answer):
    """Map section number to its text (heading included), for the sections that are present."""
    marks = [(int(m.group(1)), m.start()) for m in _HEADING.finditer(answer)]
    sections = {}
    for position, (number, start) in enumerate(marks):
        end = marks[position + 1][1] if position + 1 < len(marks) else len(answer)
        sections.setdefault(number, answer[start:end])
    return sections


def _parse_results(tool_results):
    for text in tool_results:
        try:
            parsed = json.loads(text)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            yield parsed


def _usable_passages(parsed):
    return [
        r
        for d in parsed
        for r in d.get("results", [])
        if isinstance(r, dict) and r.get("score", 0) >= MIN_PASSAGE_SCORE
    ]


def _numbers_in(value):
    """Every number anywhere in a parsed JSON structure."""
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield float(value)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _numbers_in(v)
    elif isinstance(value, list):
        for v in value:
            yield from _numbers_in(v)


def _roi_numbers(roi):
    numbers = set(_numbers_in({k: v for k, v in roi.items() if k != "assumptions"}))
    for assumption in roi.get("assumptions", {}).values():
        value = assumption.get("value")
        if isinstance(value, (int, float)):
            numbers.add(float(value))
            numbers.add(float(value) * 100)  # a fraction written as a percentage
    return numbers


def _significant_numbers(text):
    """Numbers worth checking: four or more digits, or with a decimal point (not 1, 2, 3 or years)."""
    for raw in _NUMBER.findall(text):
        cleaned = raw.replace(",", "").rstrip(".")
        if "." in cleaned or len(cleaned) >= 4:
            yield raw, float(cleaned)


def _matches_any(value, candidates):
    tolerance = 0.051 if value != int(value) else 0.5
    return any(abs(value - c) <= tolerance for c in candidates)


def run_checks(answer, tool_results, tool_calls=None):
    """Run every check. tool_calls (a list of tool names) is optional; its check is skipped without it."""
    parsed = list(_parse_results(tool_results))
    passages = _usable_passages(parsed)
    allowed_urls = {p.get("source_url") for p in passages}
    passage_text = " ".join(f"{p.get('title', '')} {p.get('text', '')}" for p in passages)
    profile = next((d["profile"] for d in parsed if "profile" in d), None)
    roi = next((d for d in parsed if "totals" in d), None)
    sections = split_sections(answer)
    checks = []

    order = [int(n) for n in _HEADING.findall(answer)]
    checks.append(
        Check("six_sections_in_order", order == EXPECTED_SECTIONS, f"headings found: {order}")
    )

    questions = re.findall(r"^\s*\d+\.\s+.*\?\s*$", sections.get(3, ""), flags=re.M)
    checks.append(
        Check(
            "question_count_8_to_10",
            MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS,
            f"{len(questions)} questions",
        )
    )

    footnotes = re.findall(r"\[\^\d+\]", answer)
    checks.append(Check("no_footnote_markers", not footnotes, f"{len(footnotes)} footnote markers"))

    bad_links = sorted({url for url in _LINK_URL.findall(answer) if url not in allowed_urls})
    checks.append(
        Check(
            "links_from_passages",
            not bad_links,
            "every link is a retrieved passage with score >= 0.60"
            if not bad_links
            else "not from a usable passage: " + ", ".join(bad_links),
        )
    )

    architecture = sections.get(4, "")
    invented = sorted({n for n in _SERVICE_NAME.findall(architecture) if n not in passage_text})
    checks.append(
        Check(
            "services_supported",
            not invented,
            "every AWS service named appears in a retrieved passage"
            if not invented
            # Conservative on purpose: a spelled-out name (AWS Identity and Access Management) for an
            # abbreviation the passage uses (IAM) is flagged too. A false alarm beats a missed invention.
            else "not found word for word in any retrieved passage: " + ", ".join(invented),
        )
    )

    bullets = [line for line in architecture.splitlines() if re.match(r"\s*(?:[-*]|\d+\.)\s+", line)]
    unlinked = [line for line in bullets if "](http" not in line]
    checks.append(
        Check(
            "architecture_bullets_cited",
            bool(bullets) and not unlinked,
            f"{len(unlinked)} of {len(bullets)} architecture bullets have no link",
        )
    )

    roi_section = sections.get(5, "")
    if roi is None:
        checks.append(Check("roi_numbers_match_tool", False, "no ROI tool result to compare against"))
    else:
        known = _roi_numbers(roi)
        stray = [raw for raw, value in _significant_numbers(roi_section) if not _matches_any(value, known)]
        checks.append(
            Check(
                "roi_numbers_match_tool",
                not stray,
                "every figure in the ROI section is in the tool result"
                if not stray
                else "not in the ROI tool result: " + ", ".join(stray),
            )
        )

    checks.append(
        Check(
            "roi_labelled_preliminary",
            "preliminary" in roi_section.lower(),
            "the ROI section says it is preliminary",
        )
    )

    if profile is not None and profile.get("headquarters"):
        place = profile["headquarters"]
        city = place.split(",")[0].strip()
        found = [p for p in {place, city} if p and p.lower() in answer.lower()]
        checks.append(
            Check(
                "no_headquarters",
                not found,
                "headquarters not mentioned" if not found else "mentions the headquarters: " + ", ".join(sorted(found)),
            )
        )

    if tool_calls is not None:
        profile_calls = sum(1 for n in tool_calls if n.startswith("profile___"))
        roi_calls = sum(1 for n in tool_calls if n.startswith("roi___"))
        kb_calls = sum(1 for n in tool_calls if n.startswith("kb___"))
        ok = profile_calls == 1 and roi_calls == 1 and 2 <= kb_calls <= 3
        checks.append(
            Check(
                "tool_calls_as_instructed",
                ok,
                f"profile x{profile_calls}, knowledge base x{kb_calls}, roi x{roi_calls} (want 1, 2 to 3, 1)",
            )
        )

    return checks
