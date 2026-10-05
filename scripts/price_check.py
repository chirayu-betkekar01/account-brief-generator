"""Print the unit prices this project depends on, straight from the AWS Price List API.

Run it before every `terraform apply` (cost rule #1: don't trust a README, trust the
price list). Standard library only, no AWS credentials needed: the bulk price files
are public.

    python scripts/price_check.py            # print the table
    python scripts/price_check.py --json     # machine-readable

Source: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/<offer>/current/us-east-1/index.json
"""

import argparse
import json
import urllib.request

BASE = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{offer}/current/us-east-1/index.json"

# (label, offer, usagetype without the "USE1-" prefix, target unit, multiplier from the file's
#  unit[, service-name prefix]). Token prices are normalised to USD per 1M tokens, guardrail
# prices to USD per 1K text units. A check must resolve to exactly ONE price or it is reported
# as AMBIGUOUS / NOT FOUND: a wrong number here would silently corrupt the cost estimate.
CHECKS = [
    ("Nova Micro input", "AmazonBedrock", "NovaMicro-input-tokens", "$/1M tokens", 1000),
    ("Nova Micro output", "AmazonBedrock", "NovaMicro-output-tokens", "$/1M tokens", 1000),
    ("Nova Lite input", "AmazonBedrock", "NovaLite-input-tokens", "$/1M tokens", 1000),
    ("Nova Lite output", "AmazonBedrock", "NovaLite-output-tokens", "$/1M tokens", 1000),
    ("Nova 2 Lite input (US geo profile)", "AmazonBedrock", "Nova2.0Lite-input-tokens", "$/1M tokens", 1000),
    ("Nova 2 Lite output (US geo profile)", "AmazonBedrock", "Nova2.0Lite-output-tokens", "$/1M tokens", 1000),
    ("Nova 2 Lite input (global profile)", "AmazonBedrock", "Nova2.0Lite-input-tokens-cross-region-global", "$/1M tokens", 1000),
    ("Nova 2 Lite output (global profile)", "AmazonBedrock", "Nova2.0Lite-output-tokens-cross-region-global", "$/1M tokens", 1000),
    # Marketplace-billed models share usagetype strings across models, so they need the
    # sixth field (service-name prefix) to select one model.
    ("Claude Haiku 4.5 input (geo/regional)", "AmazonBedrockFoundationModels", "MP:USE1_InputTokenCount-Units", "$/1M tokens", 1, "Claude Haiku 4.5"),
    ("Claude Haiku 4.5 output (geo/regional)", "AmazonBedrockFoundationModels", "MP:USE1_OutputTokenCount-Units", "$/1M tokens", 1, "Claude Haiku 4.5"),
    ("Claude Haiku 4.5 input (global)", "AmazonBedrockFoundationModels", "MP:USE1_InputTokenCount_Global-Units", "$/1M tokens", 1, "Claude Haiku 4.5"),
    ("Claude Haiku 4.5 output (global)", "AmazonBedrockFoundationModels", "MP:USE1_OutputTokenCount_Global-Units", "$/1M tokens", 1, "Claude Haiku 4.5"),
    ("Titan Text Embeddings V2", "AmazonBedrock", "TitanEmbeddingV2-Text-input-tokens", "$/1M tokens", 1000),
    ("Guardrails denied topics", "AmazonBedrock", "Guardrail-TopicPolicyUnitsConsumed", "$/1K text units", 1000),
    ("Guardrails content filters", "AmazonBedrock", "Guardrail-ContentPolicyUnitsConsumed", "$/1K text units", 1000),
    ("Guardrails PII filters", "AmazonBedrock", "Guardrail-SensitiveInformationPolicyPaidUnitsConsumed", "$/1K text units", 1000),
    ("Guardrails contextual grounding", "AmazonBedrock", "Guardrail-ContextualGroundingPolicyUnitsConsumed", "$/1K text units", 1000),
    ("S3 Vectors storage", "AmazonS3", "Vectors-TimedStorage-ByteHrs", "$/GB-month", 1),
    ("S3 Vectors PUT", "AmazonS3", "Vectors-Put-Bytes", "$/GB", 1),
    ("S3 Vectors query request", "AmazonS3", "Vectors-Request-Tier3", "$/1M queries", 1_000_000),
    ("AgentCore Runtime vCPU (v2)", "AmazonBedrockAgentCore", "Runtime:Consumption-based:vCPU-v2", "$/vCPU-hour", 1),
    ("AgentCore Runtime memory (v2)", "AmazonBedrockAgentCore", "Runtime:Consumption-based:Memory-v2", "$/GB-hour", 1),
    ("AgentCore Gateway invocation", "AmazonBedrockAgentCore", "Gateway:Consumption-based:API-Invocations", "$/1K invocations", 1000),
    ("DynamoDB on-demand write", "AmazonDynamoDB", "WriteRequestUnits", "$/1M write units", 1_000_000),
    ("DynamoDB on-demand read", "AmazonDynamoDB", "ReadRequestUnits", "$/1M read units", 1_000_000),
]


def fetch(offer: str) -> dict:
    with urllib.request.urlopen(BASE.format(offer=offer), timeout=120) as resp:
        return json.load(resp)


def lookup(doc: dict, usagetype: str, service: str | None = None) -> list[float]:
    """Return the distinct non-zero on-demand USD prices for a usagetype (and service)."""
    terms = doc["terms"].get("OnDemand", {})
    prices = set()
    for sku, product in doc["products"].items():
        attrs = product["attributes"]
        if attrs.get("usagetype", "").removeprefix("USE1-") != usagetype:
            continue
        if service and not attrs.get("servicename", "").startswith(service):
            continue
        for term in terms.get(sku, {}).values():
            for dim in term["priceDimensions"].values():
                usd = float(dim["pricePerUnit"].get("USD", 0))
                if usd > 0:
                    prices.add(usd)
    return sorted(prices)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    docs: dict[str, dict] = {}
    rows = []
    for label, offer, usagetype, unit, mult, *rest in CHECKS:
        if offer not in docs:
            docs[offer] = fetch(offer)
        found = [round(p * mult, 6) for p in lookup(docs[offer], usagetype, rest[0] if rest else None)]
        rows.append({"item": label, "unit": unit, "price": found[0] if len(found) == 1 else None, "all_tiers": found})

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    published = {o: d.get("publicationDate", "?") for o, d in docs.items()}
    print("| Item | Price | Unit |\n|---|---|---|")
    for r in rows:
        if r["price"] is not None:
            price = f"{r['price']:g}"
        elif r["all_tiers"]:
            price = f"AMBIGUOUS {r['all_tiers']}"
        else:
            price = "NOT FOUND"
        print(f"| {r['item']} | {price} | {r['unit']} |")
    print("\nPrice files published:", ", ".join(f"{o}={d}" for o, d in published.items()))


if __name__ == "__main__":
    main()
