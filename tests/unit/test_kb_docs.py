"""Guards on data/kb_docs: every knowledge document must be well-formed, sourced and free of personal data."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "kb_docs"
DOCS = sorted(DOCS_DIR.glob("*.md"))
ALLOWED_HOSTS = {"docs.aws.amazon.com", "aws.amazon.com"}
S3_VECTORS_METADATA_LIMIT_BYTES = 1024  # custom metadata per vector when used with Bedrock Knowledge Bases
S3_VECTORS_METADATA_KEY_LIMIT = 35


def metadata_of(doc):
    path = doc.with_name(doc.name + ".metadata.json")
    return json.loads(path.read_text(encoding="utf-8"))["metadataAttributes"]


def test_there_are_documents():
    assert len(DOCS) >= 12


def test_no_stray_files_in_the_corpus_folder():
    allowed = {p.name for p in DOCS} | {p.name + ".metadata.json" for p in DOCS}
    assert {p.name for p in DOCS_DIR.iterdir()} == allowed


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_document_has_metadata_with_the_expected_keys(doc):
    meta = metadata_of(doc)
    assert set(meta) == {"title", "topic", "source_url", "checked_on"}
    assert all(isinstance(v, str) and v.strip() for v in meta.values())


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_metadata_fits_the_s3_vectors_limits(doc):
    meta = metadata_of(doc)
    assert len(json.dumps(meta).encode()) < S3_VECTORS_METADATA_LIMIT_BYTES
    assert len(meta) <= S3_VECTORS_METADATA_KEY_LIMIT


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_source_is_an_official_aws_https_link_repeated_in_the_text(doc):
    meta = metadata_of(doc)
    url = urlparse(meta["source_url"])
    assert url.scheme == "https" and url.netloc in ALLOWED_HOSTS
    text = doc.read_text(encoding="utf-8")
    assert meta["source_url"] in text, "the citation must also travel inside the text itself"
    assert meta["checked_on"] in text


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_document_is_short_and_says_it_is_a_paraphrase(doc):
    text = doc.read_text(encoding="utf-8")
    words = len(text.split())
    assert 80 <= words <= 400, f"{words} words"
    assert "paraphrased, not a quotation" in text


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_document_has_a_title_that_matches_its_metadata(doc):
    first_line = doc.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == f"# {metadata_of(doc)['title']}"


@pytest.mark.parametrize(
    "label, pattern",
    [
        ("email address", r"[\w.+-]+@[\w-]+\.[\w.]+"),
        ("phone number", r"\b\d{3}[-.\s]\d{3,4}[-.\s]\d{4}\b"),
        ("US social security number", r"\b\d{3}-\d{2}-\d{4}\b"),
    ],
)
def test_corpus_contains_no_pii_like_strings(label, pattern):
    for doc in DOCS:
        assert not re.search(pattern, doc.read_text(encoding="utf-8")), f"{label} in {doc.name}"
