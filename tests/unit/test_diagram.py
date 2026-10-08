"""The architecture diagram generator (scripts/make_diagram.py): facts, completeness and layout.

These tests run offline with a stub icon, so they need neither the AWS icon package nor Chrome. They
cannot judge how the picture looks (open docs/images/architecture.png for that); they catch the
mistakes that are easy to make by hand: a number that drifted from the repo, a missing component, two
boxes on top of each other, text wider than its box, an arrow that stops in mid-air.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import make_diagram as md

ROOT = Path(__file__).resolve().parents[2]
STUB_ICON = b"<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48'><rect width='48' height='48'/></svg>"


def stub_loader(key):
    return STUB_ICON


@pytest.fixture(scope="module")
def facts():
    return md.read_facts(ROOT)


@pytest.fixture(scope="module")
def svg(facts):
    return md.build_svg(facts, stub_loader)


@pytest.fixture(scope="module")
def parts(facts):
    return md.layout(facts)


def visible_text(svg_text):
    root = ET.fromstring(svg_text)
    return " ".join("".join(el.itertext()) for el in root.iter() if el.tag.endswith("text"))


# --- facts come from the repo, not from memory ---------------------------------------------------


def test_company_and_document_counts_come_from_the_data_files(facts):
    accounts = json.loads((ROOT / "data" / "accounts.json").read_text(encoding="utf-8"))["accounts"]
    red_team = json.loads((ROOT / "data" / "eval_accounts.json").read_text(encoding="utf-8"))["accounts"]
    docs = [p for p in (ROOT / "data" / "kb_docs").glob("*.md")]
    assert (facts.demo_companies, facts.red_team_records, facts.kb_documents) == (len(accounts), len(red_team), len(docs))


def test_harness_limits_and_model_come_from_terraform(facts):
    assert (facts.max_iterations, facts.max_tokens, facts.timeout_seconds) == (12, 6000, 180)
    assert facts.model_id == "us.amazon.nova-2-lite-v1:0"


def test_the_numbers_on_the_picture_are_the_facts(facts, svg):
    text = visible_text(svg)
    assert f"{facts.demo_companies} demo companies" in text
    assert f"{facts.kb_documents} " in text
    assert f"{facts.max_iterations} steps" in text
    assert f"{facts.timeout_seconds} s" in text


# --- the picture is well formed and complete -----------------------------------------------------


def test_the_svg_is_well_formed_xml(svg):
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


REQUIRED = [
    "AgentCore Harness", "AgentCore Gateway", "Bedrock Guardrails", "account_profile", "roi_estimator",
    "kb_retrieve", "Amazon DynamoDB", "Bedrock Knowledge Base", "Amazon S3 Vectors", "Titan Embeddings",
    "Amazon CloudWatch", "AWS IAM", "AWS Budgets", "Terraform", "Nova 2 Lite", "us-east-1", "Client-side checks",
]


@pytest.mark.parametrize("name", REQUIRED)
def test_every_component_is_on_the_picture(svg, name):
    assert name in visible_text(svg)


def test_the_two_measured_weaknesses_are_shown(svg):
    text = visible_text(svg)
    assert "tool results" in text  # the guardrail does not scan them
    assert "override" in text  # callers can override the guardrail per request


def test_all_eight_request_steps_are_numbered_and_explained(svg):
    text = visible_text(svg)
    for step in range(1, 9):
        assert re.search(rf"(^|\s){step}(\s|$)", text), f"step {step} missing"
    assert "Request flow" in text


def test_nothing_sensitive_is_on_the_picture(svg):
    assert not re.search(r"\b\d{12}\b", svg), "a 12-digit number (account id?)"
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", svg), "an e-mail address"
    assert "gmail" not in svg.lower()


def test_every_icon_the_layout_uses_has_a_file_in_the_package_map(parts):
    groups, cards, arrows, notes = parts
    used = {c.icon for c in cards if c.icon} | {g.icon for g in groups if g.icon}
    assert used <= set(md.ICON_FILES), used - set(md.ICON_FILES)


@pytest.mark.skipif(not md.ICON_ZIP.exists(), reason="AWS icon package not downloaded (make diagram downloads it)")
def test_every_mapped_icon_exists_in_the_downloaded_package():
    import zipfile

    names = set(zipfile.ZipFile(md.ICON_ZIP).namelist())
    missing = [path for path in md.ICON_FILES.values() if path not in names]
    assert not missing, missing


# --- layout lint ---------------------------------------------------------------------------------


def overlap(a, b):
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def related(a, b):
    return a.parent == b.key or b.parent == a.key  # an inset sits on purpose inside the card it belongs to


def test_no_two_boxes_overlap(parts):
    _, cards, _, _ = parts
    clashes = [(a.key, b.key) for i, a in enumerate(cards) for b in cards[i + 1 :] if overlap(a, b) and not related(a, b)]
    assert not clashes, clashes


def test_an_inset_sits_fully_inside_its_parent_card(parts):
    _, cards, _, _ = parts
    by_key = {c.key: c for c in cards}
    for card in cards:
        if card.parent:
            p = by_key[card.parent]
            assert p.x <= card.x and card.x + card.w <= p.x + p.w and p.y <= card.y and card.y + card.h <= p.y + p.h, card.key


def test_everything_is_inside_the_canvas(parts):
    groups, cards, arrows, _ = parts
    for box in [*groups, *cards]:
        assert box.x >= 0 and box.y >= 0 and box.x + box.w <= md.WIDTH and box.y + box.h <= md.HEIGHT, box.key
    for arrow in arrows:
        for px, py in arrow.points:
            assert 0 <= px <= md.WIDTH and 0 <= py <= md.HEIGHT, arrow.points


def test_every_card_sits_inside_its_group_when_it_has_one(parts):
    groups, cards, _, _ = parts
    by_key = {g.key: g for g in groups}
    for card in cards:
        if card.group:
            g = by_key[card.group]
            assert g.x <= card.x and card.x + card.w <= g.x + g.w and g.y <= card.y and card.y + card.h <= g.y + g.h, card.key


def test_text_fits_inside_its_card(parts):
    _, cards, _, _ = parts
    too_wide = []
    for card in cards:
        room = card.w - card.text_x - 10
        if md.text_width(card.title, 15, bold=True) > room:
            too_wide.append((card.key, card.title))
        for line in card.lines:
            if md.text_width(line, 12) > room:
                too_wide.append((card.key, line))
    assert not too_wide, too_wide


def on_edge(point, box, tolerance=1.0):
    px, py = point
    on_vertical = (abs(px - box.x) <= tolerance or abs(px - (box.x + box.w)) <= tolerance) and box.y - tolerance <= py <= box.y + box.h + tolerance
    on_horizontal = (abs(py - box.y) <= tolerance or abs(py - (box.y + box.h)) <= tolerance) and box.x - tolerance <= px <= box.x + box.w + tolerance
    return on_vertical or on_horizontal


def test_every_arrow_starts_and_ends_on_a_box_edge(parts):
    groups, cards, arrows, _ = parts
    boxes = [*groups, *cards]
    floating = []
    for arrow in arrows:
        for end in (arrow.points[0], arrow.points[-1]):
            if not any(on_edge(end, box) for box in boxes):
                floating.append((arrow.label, end))
    assert not floating, floating


def test_every_arrow_segment_is_horizontal_or_vertical(parts):
    _, _, arrows, _ = parts
    for arrow in arrows:
        for (x1, y1), (x2, y2) in zip(arrow.points, arrow.points[1:]):
            assert x1 == x2 or y1 == y2, (arrow.label, (x1, y1), (x2, y2))


def test_arrows_do_not_cut_through_cards(parts):
    _, cards, arrows, _ = parts
    crossings = []
    for arrow in arrows:
        for (x1, y1), (x2, y2) in zip(arrow.points, arrow.points[1:]):
            lo_x, hi_x, lo_y, hi_y = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
            for card in cards:
                # strictly inside the card (touching the edge at an end point is how an arrow arrives)
                if lo_x < card.x + card.w - 1 and hi_x > card.x + 1 and lo_y < card.y + card.h - 1 and hi_y > card.y + 1:
                    crossings.append((arrow.label, card.key))
    assert not crossings, crossings
