"""Draw the architecture diagram: docs/images/architecture.svg and architecture.png.

    python scripts/make_diagram.py            # make diagram

Official AWS Architecture Icons are used (AWS lets customers use them to draw architecture diagrams).
The icon package is downloaded once into .cache/ (git-ignored: only the finished picture is committed,
not the icon files). The SVG is laid out here, and the PNG is a screenshot of it from headless Chrome or
Edge. Numbers on the picture (companies, documents, harness limits, model) are read from the repo, so
they cannot drift from what is deployed.
"""

import base64
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ICON_ZIP = ROOT / ".cache" / "aws-icons" / "icon-package.zip"
ICON_URL = (
    "https://d1.awsstatic.com/onedam/marketing-channels/website/public/shared/architecture-icon-release/"
    "Icon-package_07312026.5846e92413caa21490223536cc97f1269e44fa92.zip"
)
OUT_DIR = ROOT / "docs" / "images"

WIDTH, HEIGHT = 2340, 1520
INK, MUTED, GRAY = "#232F3E", "#4B5563", "#5A6C86"

_P = "Architecture-Service-Icons_07312026/Arch_"
_R = "Resource-Icons_07312026/Res_"
ICON_FILES = {
    "agentcore": _P + "Artificial-Intelligence/64/Arch_Amazon-Bedrock-AgentCore_64.svg",
    "bedrock": _P + "Artificial-Intelligence/64/Arch_Amazon-Bedrock_64.svg",
    "nova": _P + "Artificial-Intelligence/64/Arch_Amazon-Nova_64.svg",
    "lambda": _P + "Compute/64/Arch_AWS-Lambda_64.svg",
    "dynamodb": _P + "Databases/64/Arch_Amazon-DynamoDB_64.svg",
    "s3": _P + "Storage/64/Arch_Amazon-Simple-Storage-Service_64.svg",
    "s3vectors": _R + "Storage/Res_Amazon-Simple-Storage-Service_S3-Vectors_48.svg",
    "cloudwatch": _P + "Management-Tools/64/Arch_Amazon-CloudWatch_64.svg",
    "iam": _P + "Security-Identity/64/Arch_AWS-Identity-and-Access-Management_64.svg",
    "budgets": _P + "Cloud-Financial-Management/64/Arch_AWS-Budgets_64.svg",
    "client": _R + "General-Icons/Res_48_Light/Res_Client_48_Light.svg",
    "shield": _R + "General-Icons/Res_48_Light/Res_Shield_48_Light.svg",
    "alert": _R + "General-Icons/Res_48_Light/Res_Alert_48_Light.svg",
    "code": _R + "General-Icons/Res_48_Light/Res_Source-Code_48_Light.svg",
    "cloud": "Architecture-Group-Icons_07312026/AWS-Cloud_32.svg",
    "region": "Architecture-Group-Icons_07312026/Region_32.svg",
}


# --------------------------------------------------------------------------- facts from the repo


@dataclass(frozen=True)
class Facts:
    demo_companies: int
    red_team_records: int
    kb_documents: int
    max_iterations: int
    max_tokens: int
    timeout_seconds: int
    model_id: str


def _tf_default(text, name):
    block = re.search(rf'variable\s+"{name}"\s*\{{.*?default\s*=\s*([^\n]+)', text, re.S)
    if not block:
        raise ValueError(f"no default found for Terraform variable {name}")
    return int(block.group(1).strip())


def read_facts(root=ROOT):
    root = Path(root)

    def count(path):
        return len(json.loads((root / path).read_text(encoding="utf-8"))["accounts"])

    agent_vars = (root / "infra/modules/agent/variables.tf").read_text(encoding="utf-8")
    main_tf = (root / "infra/main/main.tf").read_text(encoding="utf-8")
    model = re.search(r'\bmodel_id\s*=\s*"([^"]+)"', main_tf)
    return Facts(
        demo_companies=count("data/accounts.json"),
        red_team_records=count("data/eval_accounts.json"),
        kb_documents=len(list((root / "data" / "kb_docs").glob("*.md"))),
        max_iterations=_tf_default(agent_vars, "max_iterations"),
        max_tokens=_tf_default(agent_vars, "max_tokens"),
        timeout_seconds=_tf_default(agent_vars, "timeout_seconds"),
        model_id=model.group(1) if model else "unknown",
    )


# --------------------------------------------------------------------------- the model of the picture


@dataclass(frozen=True)
class Group:
    key: str
    x: int
    y: int
    w: int
    h: int
    title: str
    style: str = "generic"  # cloud | region | generic
    icon: str | None = None


@dataclass(frozen=True)
class Card:
    key: str
    x: int
    y: int
    w: int
    h: int
    title: str
    lines: tuple = ()
    icon: str | None = None
    group: str | None = None  # the group box it must sit inside
    kind: str = "card"  # card | note | inset
    valign: str = "middle"
    icon_size: int = 48
    text_x: int = 72
    title_size: int = 15
    parent: str | None = None  # an inset sits inside another card


@dataclass(frozen=True)
class Arrow:
    points: tuple
    label: str | None = None
    label_at: tuple | None = None
    label_anchor: str = "middle"
    dashed: bool = False
    both: bool = False
    badge: int | None = None
    badge_at: tuple | None = None


@dataclass(frozen=True)
class Note:
    text: str
    x: int
    y: int
    size: int = 14
    bold: bool = False
    color: str = MUTED
    anchor: str = "start"


def text_width(text, size, bold=False):
    """A cautious estimate (Arial averages about 0.5em; this assumes a little more), for the fit check."""
    return len(text) * size * (0.6 if bold else 0.55)


STEPS = (
    "You sign an InvokeHarness call with your AWS identity (SigV4); there are no API keys.",
    "The harness runs the model in a loop. Every model call is screened by the guardrail.",
    "The model's tool calls go to the Gateway over MCP, authenticated with IAM.",
    "The Gateway invokes the Lambdas: the profile once, two or three searches, the ROI once.",
    "account_profile reads one row from DynamoDB (GetItem).",
    "kb_retrieve queries the knowledge base, which uses S3 Vectors and Titan embeddings.",
    "The brief streams back to you together with the tool results.",
    "The client checks links, AWS services and ROI figures against the tool results.",
)


def layout(facts):
    f = facts
    groups = [
        Group("cloud", 380, 100, 1940, 1100, "AWS Cloud", "cloud", "cloud"),
        Group("region", 400, 150, 1900, 810, "Region: us-east-1", "region", "region"),
        Group("agentcore", 430, 210, 320, 390, "Amazon Bedrock AgentCore"),
        Group("lambdas", 1210, 330, 330, 380, "Tool Lambdas, one IAM role each"),
    ]
    cards = [
        # --- you
        Card("you", 10, 240, 270, 170, "You", ("CLI: make brief", "Web page: make ui", "(localhost only)", "SigV4-signed requests"), "client"),
        Card("checks", 10, 450, 270, 100, "Client-side checks", ("links, ROI figures, services", "client/brief_checks.py"), "shield"),
        Card(
            "override", 10, 590, 270, 130, "Known weakness",
            ("Callers allowed to InvokeHarness", "can override the guardrail,", "model, prompt and tools", "in the same request."),
            "alert", kind="note", icon_size=28, text_x=46, title_size=13,
        ),
        Card("terraform", 10, 1010, 270, 110, "Terraform", ("bootstrap stack: the budget", "main stack: everything else"), "code"),
        # --- AgentCore
        Card(
            "harness", 445, 240, 290, 170, "AgentCore Harness",
            ("agent loop + system prompt", f"caps: {f.max_iterations} steps, {f.max_tokens:,} tokens,", f"{f.timeout_seconds} s, memory off, no shell"),
            "agentcore", "agentcore", valign="top",
        ),
        Card("model", 457, 348, 266, 52, "Amazon Nova 2 Lite", ("US inference profile, temp 0.2",), "nova", kind="inset", icon_size=32, text_x=50, title_size=13, parent="harness"),
        Card("gateway", 445, 474, 290, 100, "AgentCore Gateway", ("MCP tools, AWS_IAM auth", "3 Lambda targets"), "agentcore", "agentcore"),
        # --- guardrail and its caveat
        Card(
            "guardrail", 860, 240, 290, 130, "Bedrock Guardrails",
            ("18 PII types, 4 denied topics", "prompt-attack filter (input)", "grounding score: info only"), "bedrock",
        ),
        Card(
            "blind", 860, 395, 290, 110, "Known weakness",
            ("Not scanned by the guardrail:", "tool arguments and tool results.", "Planted instructions worked", "in 6 of 6 evaluation runs."),
            "alert", kind="note", icon_size=28, text_x=46, title_size=13,
        ),
        # --- the three tools
        Card("profile", 1225, 360, 300, 96, "account_profile", ("GetItem on one DynamoDB table",), "lambda", "lambdas"),
        Card("roi", 1225, 476, 300, 96, "roi_estimator", ("pure Python 3-year ROI model", "assumptions.json in the zip"), "lambda", "lambdas"),
        Card("kbfn", 1225, 592, 300, 96, "kb_retrieve", ("Retrieve on one knowledge base", "returns passages + links"), "lambda", "lambdas"),
        # --- data
        Card("ddb", 1620, 360, 280, 96, "Amazon DynamoDB", ("accounts table:", f"{f.demo_companies} demo companies", f"+ {f.red_team_records} red-team records"), "dynamodb"),
        Card("kb", 1620, 592, 280, 96, "Bedrock Knowledge Base", ("semantic search (Retrieve)", f"{f.kb_documents} sourced AWS-doc summaries"), "bedrock"),
        Card("docs", 1620, 770, 280, 96, "Amazon S3", ("document bucket:", f"{f.kb_documents} docs + metadata files", "(indexed by make ingest)"), "s3"),
        Card("titan", 1980, 470, 290, 96, "Titan Embeddings V2", ("Bedrock embedding model", "turns text into vectors"), "bedrock"),
        Card("vectors", 1980, 592, 290, 96, "Amazon S3 Vectors", ("vector index (1,024 dims)", "pay per use, $0 idle"), "s3vectors"),
        # --- operations, security, cost
        Card("cw", 860, 800, 300, 110, "Amazon CloudWatch", ("logs (14-day retention),", "6 metric filters, 4 alarms,", "1 dashboard"), "cloudwatch"),
        Card("iam", 430, 1010, 900, 110, "AWS IAM", ("one role per Lambda, plus gateway, harness and knowledge-base roles", "callers sign requests (SigV4); no API keys"), "iam"),
        Card("budgets", 1390, 1010, 900, 110, "AWS Budgets", ("$25 a month, alerts at 20, 50, 80 and 100%", "separate bootstrap stack, kept by make destroy"), "budgets"),
    ]
    arrows = [
        Arrow(((280, 285), (445, 285)), "InvokeHarness", (334, 265), badge=1, badge_at=(322, 285)),
        Arrow(((445, 365), (280, 365)), "brief + results", (330, 389), badge=7, badge_at=(405, 365)),
        Arrow(((145, 410), (145, 450)), badge=8, badge_at=(172, 430)),
        Arrow(((735, 305), (860, 305)), "each model call", (797, 288), both=True, badge=2, badge_at=(797, 326)),
        Arrow(((590, 410), (590, 474)), "tool calls (MCP)", (604, 446), "start", badge=3, badge_at=(570, 442)),
        # the Gateway fans out to the three Lambdas (the three lines share the first stretch)
        Arrow(((735, 524), (1225, 524)), "invoke", (1000, 548), badge=4, badge_at=(1000, 524)),
        Arrow(((735, 524), (1180, 524), (1180, 408), (1225, 408))),
        Arrow(((735, 524), (1180, 524), (1180, 640), (1225, 640))),
        Arrow(((1525, 408), (1620, 408)), "GetItem", (1572, 392), badge=5, badge_at=(1572, 428)),
        Arrow(((1525, 640), (1620, 640)), "Retrieve", (1572, 624), badge=6, badge_at=(1572, 660)),
        Arrow(((1900, 640), (1980, 640)), "vectors", (1940, 624)),
        Arrow(((1860, 592), (1860, 518), (1980, 518)), "embed", (1925, 502)),
        Arrow(((1760, 770), (1760, 688)), "ingest", (1772, 734), "start", dashed=True),
        Arrow(((590, 600), (590, 855), (860, 855)), "logs, metrics", (725, 845), dashed=True),
        Arrow(((1375, 710), (1375, 855), (1160, 855)), "logs, metrics", (1268, 845), dashed=True),
    ]
    notes = [
        Note("Presales Accelerator: Account Brief Generator", 30, 44, 30, True, INK),
        Note("Architecture: how one discovery brief is produced. Repository: discovery-brief-agent.", 30, 74, 16, False, MUTED),
        Note("Request flow", 30, 1250, 20, True, INK),
        Note(
            "Independent portfolio project, not an AWS product. AWS and the AWS icons are trademarks of Amazon Web Services, Inc. "
            "Icons: AWS Architecture Icons, July 2026 release.",
            30, 1500, 12, False, MUTED,
        ),
    ]
    return groups, cards, arrows, notes


# --------------------------------------------------------------------------- drawing


def zip_loader(path=ICON_ZIP):
    package = zipfile.ZipFile(path)

    def load(key):
        return package.read(ICON_FILES[key])

    return load


def _image(load_icon, key, x, y, size):
    data = base64.b64encode(load_icon(key)).decode("ascii")
    return f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="data:image/svg+xml;base64,{data}"/>'


def _text(x, y, text, size=12, bold=False, color=MUTED, anchor="start"):
    weight = ' font-weight="bold"' if bold else ""
    return f'<text x="{x}" y="{y}" font-size="{size}"{weight} fill="{color}" text-anchor="{anchor}">{escape(text)}</text>'


def _group_svg(g, load_icon):
    if g.style == "cloud":
        box = f'<rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="4" fill="#FFFFFF" stroke="{INK}" stroke-width="2"/>'
    elif g.style == "region":
        box = f'<rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="4" fill="#F7FCFC" stroke="#00A4A6" stroke-width="1.6" stroke-dasharray="9 5"/>'
    else:
        box = f'<rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="6" fill="#FBFBFD" stroke="{GRAY}" stroke-width="1.2" stroke-dasharray="6 4"/>'
    if g.icon:
        return box + _image(load_icon, g.icon, g.x + 8, g.y + 8, 32) + _text(g.x + 48, g.y + 30, g.title, 16, True, INK)
    return box + _text(g.x + 14, g.y + 24, g.title, 13, True, GRAY)


def _card_svg(c, load_icon):
    styles = {
        "card": ('#FFFFFF', '#B8C2CE'),
        "note": ('#FFF4E0', '#E8A33D'),
        "inset": ('#F2F5F8', '#D3DAE2'),
    }
    fill, stroke = styles[c.kind]
    out = [f'<rect x="{c.x}" y="{c.y}" width="{c.w}" height="{c.h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>']
    n = len(c.lines)
    if c.valign == "top":
        icon_y, top = c.y + 14, c.y + 16
    else:
        icon_y = c.y + (c.h - c.icon_size) / 2
        top = c.y + (c.h - (20 + 16 * n)) / 2
    if c.icon:
        out.append(_image(load_icon, c.icon, c.x + 12, icon_y, c.icon_size))
    colour = "#5B3A00" if c.kind == "note" else INK
    out.append(_text(c.x + c.text_x, top + 14, c.title, c.title_size, True, colour))
    for i, line in enumerate(c.lines):
        out.append(_text(c.x + c.text_x, top + 14 + 19 + 16 * i, line, 12, False, "#5B4A1F" if c.kind == "note" else MUTED))
    return "".join(out)


def _arrow_svg(a):
    colour = GRAY if a.dashed else INK
    dash = ' stroke-dasharray="7 5"' if a.dashed else ""
    start = ' marker-start="url(#head-dashed)"' if (a.both and a.dashed) else (' marker-start="url(#head)"' if a.both else "")
    end = "url(#head-dashed)" if a.dashed else "url(#head)"
    pts = " ".join(f"{x},{y}" for x, y in a.points)
    out = [f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2"{dash}{start} marker-end="{end}"/>']
    if a.label and a.label_at:
        x, y = a.label_at
        width = text_width(a.label, 11) + 8
        left = x - width / 2 if a.label_anchor == "middle" else x - 4
        out.append(f'<rect x="{left:.0f}" y="{y - 11}" width="{width:.0f}" height="15" rx="3" fill="#FFFFFF" fill-opacity="0.92"/>')
        out.append(_text(x, y, a.label, 11, False, INK, a.label_anchor).replace("<text ", '<text font-style="italic" ', 1))
    if a.badge is not None and a.badge_at:
        out.append(_badge(a.badge, *a.badge_at))
    return "".join(out)


def _badge(number, x, y, radius=11):
    return (
        f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{INK}"/>'
        f'<text x="{x}" y="{y + 4.5}" font-size="13" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{number}</text>'
    )


def _flow_svg():
    out = []
    for i, step in enumerate(STEPS):
        column, row = divmod(i, 4)
        x, y = 30 + column * 1130, 1290 + row * 38
        out.append(_badge(i + 1, x + 11, y - 4))
        out.append(_text(x + 32, y, step, 15, False, INK))
    return "".join(out)


def _legend_svg():
    x, y = 1640, 26
    return (
        f'<line x1="{x}" y1="{y + 8}" x2="{x + 44}" y2="{y + 8}" stroke="{INK}" stroke-width="2" marker-end="url(#head)"/>'
        + _text(x + 54, y + 12, "request / response", 12, False, INK)
        + f'<line x1="{x}" y1="{y + 34}" x2="{x + 44}" y2="{y + 34}" stroke="{GRAY}" stroke-width="2" stroke-dasharray="7 5" marker-end="url(#head-dashed)"/>'
        + _text(x + 54, y + 38, "logs, ingestion", 12, False, INK)
        + f'<rect x="{x + 230}" y="{y}" width="30" height="18" rx="4" fill="#FFF4E0" stroke="#E8A33D" stroke-width="1.3"/>'
        + _text(x + 270, y + 13, "weakness measured in the evaluation", 12, False, INK)
    )


def build_svg(facts, load_icon):
    groups, cards, arrows, notes = layout(facts)
    marker = (
        '<marker id="{id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Arial, Helvetica, sans-serif">',
        "<title>Presales Accelerator architecture</title>",
        "<desc>How one discovery brief is produced: client, AgentCore harness and gateway, guardrail, three Lambda tools, DynamoDB, knowledge base on S3 Vectors, CloudWatch, IAM, Budgets.</desc>",
        "<defs>" + marker.format(id="head", c=INK) + marker.format(id="head-dashed", c=GRAY) + "</defs>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#FFFFFF"/>',
    ]
    parts += [_group_svg(g, load_icon) for g in groups]
    parts += [_arrow_svg(a) for a in arrows]
    parts += [_card_svg(c, load_icon) for c in cards if c.kind != "inset"]
    parts += [_card_svg(c, load_icon) for c in cards if c.kind == "inset"]
    parts += [_text(n.x, n.y, n.text, n.size, n.bold, n.color, n.anchor) for n in notes]
    parts += [_flow_svg(), _legend_svg(), "</svg>"]
    return "\n".join(parts)


# --------------------------------------------------------------------------- files and rendering


def ensure_icon_package():
    if ICON_ZIP.exists() and ICON_ZIP.stat().st_size > 1_000_000:
        return
    ICON_ZIP.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading the AWS Architecture Icons (about 14 MB) to {ICON_ZIP} ...", file=sys.stderr)
    urllib.request.urlretrieve(ICON_URL, ICON_ZIP)
    if ICON_ZIP.stat().st_size < 1_000_000:
        ICON_ZIP.unlink()
        sys.exit("The icon download looks wrong (too small). Get the package from https://aws.amazon.com/architecture/icons/")


def find_browser():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    sys.exit("No Chrome or Edge found to turn the SVG into a PNG. Open docs/images/architecture.svg in a browser instead.")


def render_png(svg_path, png_path, scale=2):
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                f"--force-device-scale-factor={scale}", f"--window-size={WIDTH},{HEIGHT}",
                f"--screenshot={png_path}", Path(svg_path).resolve().as_uri(),
            ],
            check=True, capture_output=True, timeout=120,
        )


def main():
    ensure_icon_package()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path, png_path = OUT_DIR / "architecture.svg", OUT_DIR / "architecture.png"
    svg_path.write_text(build_svg(read_facts(), zip_loader()), encoding="utf-8", newline="\n")
    print(f"wrote {svg_path}")
    render_png(svg_path, png_path)
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
