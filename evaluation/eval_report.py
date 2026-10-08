"""Aggregate many run results into numbers, and render them as a markdown report."""

from collections import defaultdict
from dataclasses import dataclass, field

REFUSAL_CATEGORIES = ("pii", "off_topic", "injection_direct")


@dataclass
class RunResult:
    case_id: str
    category: str
    model: str
    repeat: int
    passed: bool
    rules: list  # [(rule name, passed, detail)]
    checks: dict = field(default_factory=dict)  # brief check name -> passed (brief runs only)
    check_details: dict = field(default_factory=dict)  # brief check name -> its detail text (brief runs only)
    tool_results: list = field(default_factory=list)  # what the tools returned, so a run can be re-checked later
    guardrail_blocked: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reasons: list = field(default_factory=list)
    tools: list = field(default_factory=list)
    answer: str = ""


def aggregate(results):
    """{category: {model: (passed, total)}}."""
    counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in results:
        cell = counts[r.category][r.model]
        cell[0] += 1 if r.passed else 0
        cell[1] += 1
    return {cat: {model: tuple(cell) for model, cell in models.items()} for cat, models in counts.items()}


def model_cost(result, prices):
    """Model-token cost of one run in dollars. prices: {model: (input $/M tokens, output $/M tokens)}."""
    price_in, price_out = prices[result.model]
    return round(result.input_tokens / 1e6 * price_in + result.output_tokens / 1e6 * price_out, 6)


def per_check_rates(results):
    """{model: {check name: (passed, total)}} over brief runs."""
    counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in results:
        if r.category != "brief":
            continue
        for name, ok in r.checks.items():
            cell = counts[r.model][name]
            cell[0] += 1 if ok else 0
            cell[1] += 1
    return {m: {n: tuple(c) for n, c in checks.items()} for m, checks in counts.items()}


def flagged_services(results):
    """{model: {service name: times flagged}} from the services_supported check of brief runs."""
    prefix = "not found word for word in any retrieved passage: "
    counts = defaultdict(lambda: defaultdict(int))
    for r in results:
        detail = r.check_details.get("services_supported", "")
        if r.category == "brief" and detail.startswith(prefix):
            for name in detail[len(prefix):].split(", "):
                counts[r.model][name] += 1
    return {m: dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))) for m, c in counts.items()}


def layer_breakdown(results):
    """For the refusal categories: how many were stopped by the guardrail, by the model or tools, or got through."""
    layers = defaultdict(lambda: {"guardrail": 0, "model_or_tools": 0, "failed": 0})
    for r in results:
        if r.category not in REFUSAL_CATEGORIES:
            continue
        if not r.passed:
            layers[r.model]["failed"] += 1
        elif r.guardrail_blocked:
            layers[r.model]["guardrail"] += 1
        else:
            layers[r.model]["model_or_tools"] += 1
    return dict(layers)


def _fmt(cell):
    passed, total = cell
    return f"{passed}/{total} ({round(100 * passed / total)}%)"


def render_markdown(results, prices, title, generated):
    models = sorted({r.model for r in results})
    table = aggregate(results)
    total_cost = sum(model_cost(r, prices) for r in results)
    lines = [f"# {title}", "", f"Generated {generated}. {len(results)} runs across {len(models)} model(s): {', '.join(models)}.", ""]

    lines += ["## Pass rate by category", "", "| category | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    for category in sorted(table):
        cells = [_fmt(table[category][m]) if m in table[category] else "-" for m in models]
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    lines.append("")

    layers = layer_breakdown(results)
    if layers:
        lines += ["## Which layer stopped the refusal cases (pii, off_topic, injection_direct)", "",
                  "| model | guardrail | model or tools | got through |", "|---|---|---|---|"]
        for model in models:
            if model in layers:
                v = layers[model]
                lines.append(f"| {model} | {v['guardrail']} | {v['model_or_tools']} | {v['failed']} |")
        lines.append("")

    rates = per_check_rates(results)
    if rates:
        names = sorted({n for checks in rates.values() for n in checks})
        lines += ["## Brief quality: pass rate of each deterministic check", "",
                  "| check | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
        for name in names:
            cells = [_fmt(rates[m][name]) if m in rates and name in rates[m] else "-" for m in models]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.append("")

    flagged = flagged_services(results)
    if flagged:
        lines += ["## AWS service names flagged as not in any retrieved passage", "",
                  "Genuinely ungrounded names and spelled-out names for abbreviations look the same to the check; read the list.", ""]
        for model in models:
            if model in flagged:
                lines.append(f"- **{model}**: " + ", ".join(f"{n} x{c}" for n, c in flagged[model].items()))
        lines.append("")

    failures = [r for r in results if not r.passed]
    lines += ["## Failures", ""]
    if not failures:
        lines.append("None.")
    for r in sorted(failures, key=lambda x: (x.case_id, x.model, x.repeat)):
        reasons = "; ".join(f"{name}: {detail}" for name, ok, detail in r.rules if not ok)
        lines.append(f"- **{r.case_id}** ({r.model}, run {r.repeat}): {reasons}")
    lines.append("")

    lines += ["## Cost (model tokens only; excludes guardrail and runtime charges)", "",
              "| model | runs | input tokens | output tokens | model cost | per brief run |", "|---|---|---|---|---|---|"]
    for model in models:
        mine = [r for r in results if r.model == model]
        briefs = [r for r in mine if r.category == "brief"]
        cost = sum(model_cost(r, prices) for r in mine)
        per_brief = sum(model_cost(r, prices) for r in briefs) / len(briefs) if briefs else 0
        lines.append(
            f"| {model} | {len(mine)} | {sum(r.input_tokens for r in mine)} | {sum(r.output_tokens for r in mine)} "
            f"| ${cost:.3f} | ${per_brief:.3f} |"
        )
    lines.append(f"\nTotal model cost of this evaluation: ${total_cost:.3f}.")
    return "\n".join(lines) + "\n"
