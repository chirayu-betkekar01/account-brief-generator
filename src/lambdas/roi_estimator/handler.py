"""roi_estimator Lambda: run the 3-year ROI model for one set of inputs.

Called by the AgentCore Gateway; the event IS the tool's arguments, e.g.
{"on_prem_annual_cost_usd": 3900000, "servers": 340, "storage_tb": 180, "annual_growth_pct": 12}.

The assumptions live in assumptions.json next to this file and are returned
with every answer (value, unit, rationale, source), so the brief can show a
reader exactly what the numbers rest on. This function makes no AWS calls, so
its IAM role needs nothing but permission to write its own logs.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

try:  # imported as a package (unit tests)
    from .roi import compute_roi
except ImportError:  # deployed as a flat zip: handler.py and roi.py sit side by side
    from roi import compute_roi

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ASSUMPTIONS_FILE = Path(__file__).with_name("assumptions.json")
INPUT_FIELDS = ("on_prem_annual_cost_usd", "servers", "storage_tb", "annual_growth_pct")
MAX_ERROR_LENGTH = 200


@lru_cache(maxsize=2)
def _load_assumptions(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["assumptions"]


def lambda_handler(event, context):
    event = event if isinstance(event, dict) else {}
    inputs = {name: event.get(name) for name in INPUT_FIELDS}
    assumptions = _load_assumptions(ASSUMPTIONS_FILE)
    values = {name: entry["value"] for name, entry in assumptions.items()}

    try:
        result = compute_roi(**inputs, assumptions=values)
    except ValueError as error:
        # Bad input is an answer the agent can act on, not a crash.
        logger.warning("roi request rejected: %s", str(error)[:MAX_ERROR_LENGTH])
        return {"ok": False, "error": str(error)[:MAX_ERROR_LENGTH]}

    logger.info(
        "roi computed roi_pct=%s breakeven_year=%s", result["totals"]["roi_pct"], result["breakeven_year"]
    )
    return {"ok": True, "inputs": inputs, "assumptions": assumptions, **result}
