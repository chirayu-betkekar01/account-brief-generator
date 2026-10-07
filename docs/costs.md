# Cost model and guard-rails

**Ceiling for the whole build: US$25.** Prices below were verified on **2026-10-05** against
AWS's official Price List API (`pricing.us-east-1.amazonaws.com`, region `us-east-1`) and,
for CloudWatch, the CloudWatch pricing page. Re-verify any time with:

```
python scripts/price_check.py
```

The script resolves each line to exactly one price or reports `AMBIGUOUS` / `NOT FOUND`
instead of guessing.

## 1. How the ceiling is enforced

| Layer | What it does | Strength |
|---|---|---|
| Serverless-only design | Every resource is pay-per-use; **idle cost is $0/hour** (table in section 3) | Structural |
| Harness execution limits | `max_iterations`, `max_tokens`, `timeout_seconds`, short `idle_runtime_session_timeout` cap one run | **Hard**, per request |
| Tiny unit prices | A full brief costs about 3-9 cents (section 4) | Structural |
| AWS Budget + e-mail alerts | Alerts at 20/50/80/100 % of $25 actual spend, plus a forecast alert | **Soft**: see below |
| `make destroy` | Removes everything except the free budget | Manual, you run it |

**The budget is a warning, not a brake.** AWS documents that Budgets data is "updated up to
three times a day", typically 8-12 hours apart, and that you "might incur additional costs
... that exceed your budget notification threshold before AWS Budgets can notify you". That is
why the hard limits live in the harness, not in the alarm. The budget tracks *gross* usage
(`include_credit = false`) so promotional credits cannot hide a runaway bill.

## 2. Verified unit prices (US East, N. Virginia)

| Item | Price | Source offer |
|---|---|---|
| Nova Micro | $0.035 in / $0.14 out per 1M tokens | AmazonBedrock |
| Nova Lite | $0.06 in / $0.24 out per 1M tokens | AmazonBedrock |
| **Nova 2 Lite**, US geo profile (`us.`) | **$0.33 in / $2.75 out** per 1M tokens | AmazonBedrock |
| Nova 2 Lite, global profile (`global.`) | $0.30 in / $2.50 out per 1M tokens | AmazonBedrock |
| Claude Haiku 4.5, US geo profile | $1.10 in / $5.50 out per 1M tokens | AmazonBedrockFoundationModels |
| Claude Haiku 4.5, global profile | $1.00 in / $5.00 out per 1M tokens | AmazonBedrockFoundationModels |
| Titan Text Embeddings V2 | $0.02 per 1M tokens | AmazonBedrock |
| Guardrails: denied topics | $0.15 per 1K text units | AmazonBedrock |
| Guardrails: PII (sensitive information) | $0.10 per 1K text units | AmazonBedrock |
| Guardrails: contextual grounding | $0.10 per 1K text units | AmazonBedrock |
| Guardrails: content filters (not planned) | $0.15 per 1K text units | AmazonBedrock |
| S3 Vectors storage | $0.06 per GB-month | AmazonS3 |
| S3 Vectors ingest (PUT) | $0.20 per GB | AmazonS3 |
| S3 Vectors query | $2.50 per 1M requests (plus negligible per-GB processing) | AmazonS3 |
| AgentCore Runtime (v2 microVM) | $0.1276 per vCPU-hour, $0.0169 per GB-hour | AmazonBedrockAgentCore |
| AgentCore Gateway | $0.005 per 1K invocations | AmazonBedrockAgentCore |
| DynamoDB on-demand | $0.625 per 1M writes, $0.125 per 1M reads; first 25 GB storage free | AmazonDynamoDB |
| AWS Budgets | $0.00 per budget-day (first two *action-enabled* budgets free; we use none) | AWSBudgets |
| Lambda | 1,000,000 requests/month free tier; $0.0000166667 per GB-second beyond free compute | AWSLambda |
| CloudWatch (page) | Free: 5 GB logs, 3 dashboards, 10 custom metrics, 10 alarms. Beyond: $0.50/GB ingest, $3/dashboard-month, $0.30/metric-month, $0.10/alarm-month | CloudWatch pricing page |

Notes on things that are easy to get wrong:

* The `us.` geo inference profile carries a **~10 % premium** over `global.` for the same
  model. We use `us.` anyway: it keeps inference inside three US regions and lets the IAM
  policy name exact destination regions (least privilege). The cost difference is under a
  tenth of a cent per brief.
* AgentCore lists two microVM generations (v1 $0.0895/$0.00945, v2 $0.1276/$0.0169). It is not
  documented which one the harness uses, so every estimate uses the **higher v2 rates**.
* The price list shows two Guardrails price families (for example content filters at both
  $0.15 and $0.07 per 1K units). Estimates use the higher, documented per-1K figures.
* The Price List has **no per-call fee for `Retrieve`** on a customer-managed vector store such
  as S3 Vectors. The "$1.00 per 1,000 retrieve calls" on the Bedrock pricing page applies to
  the separate *Managed Knowledge Base* product, which this project does not use.

## 3. Resource-by-resource cost (what each billable thing costs idle)

| # | Resource | Created in | Idle $/hour | Idle $/month | Usage price |
|---|---|---|---|---|---|
| 1 | AWS Budget + e-mail alerts | Phase 1 | $0 | $0 | $0.00 per budget-day |
| 2 | DynamoDB table, on-demand | Phase 2 | $0 | about $0 (KBs of data) | $0.625 / $0.125 per 1M writes / reads |
| 3 | 3 Lambda functions + log groups | Phase 2 | $0 | $0 | Free tier, then per GB-second |
| 4 | S3 bucket with doc excerpts | Phase 3 | about $0 | well under $0.01 | S3 standard rates (not re-verified; tens of KB) |
| 5 | S3 Vectors bucket + index | Phase 3 | about $0 | about $0.00006 per MB stored | $0.06/GB-mo, $2.50 per 1M queries |
| 6 | Bedrock Knowledge Base | Phase 3 | $0 (no hourly fee in the Price List) | $0 | Titan V2 embedding: about $0.0005 for the whole corpus |
| 7 | Bedrock Guardrail | Phase 4 | $0 | $0 | Per 1K text units (section 2) |
| 8 | AgentCore Gateway + targets | Phase 4 | $0 | $0 | $0.005 per 1K invocations |
| 9 | AgentCore Harness (managed memory **off**) | Phase 4 | $0 | $0 | Only while a session is active (section 2) |
| 10 | CloudWatch log groups, metric filters, alarm, 1 dashboard | Phase 4 | about $0 | $0 inside the free tier | Beyond free tier (section 2) |

**Everything idle: $0.00/hour.** Forgetting to tear down for a month would cost well under
$1. The expensive mistake in this space is a vector store with an hourly floor (OpenSearch
Serverless), which this project deliberately avoids by using S3 Vectors.

I will restate the line for each resource, with its price, immediately before asking you to
approve a `terraform apply`.

## 4. Per-brief and whole-build projection

Assumptions (replaced by **measured** token usage in Phase 4): 6 model calls per brief,
about 5,000 input tokens each (30K in total), 4,000 output tokens, 4 characters per token,
one guardrail text unit per 1,000 characters, 60 s of runtime at 1 vCPU with 2 GB held for
60 s plus a 120 s idle timeout, 5 gateway calls.

| Model for the agent | Model cost | All-in per brief (best-worst) | Briefs per $25 |
|---|---|---|---|
| Nova Micro | $0.002 | $0.03-$0.04 | about 630 |
| Nova Lite | $0.003 | $0.03-$0.04 | about 610 |
| **Nova 2 Lite (proposed)** | **$0.021** | **$0.05-$0.06** | **about 425** |
| Claude Haiku 4.5 | $0.055 | $0.08-$0.09 | about 270 |

Guardrail evaluation ($0.02-$0.03) costs as much as the Nova 2 Lite tokens themselves. That
is a real design lesson: **safety controls are a first-class line item.**

Projected spend by phase (Nova 2 Lite, conservative):

| Phase | Activity | Estimate |
|---|---|---|
| 1-2 | Budget, Lambdas, unit tests (tests run locally against mocks) | $0 |
| 3 | Knowledge base ingestion and retrieval tests | under $0.05 |
| 4 | Deploy, about 20 smoke-test briefs | about $1.2 |
| 5 | Evaluation: about 15 runs of 12 prompts (many are refused cheaply) | about $6 |
| 5 | One model comparison (Haiku 4.5 vs Nova 2 Lite) | about $1.2 |
| 6 | Demo rehearsal and recording, about 10 briefs | about $0.6 |
| | **Expected total** | **about $9-10** |
| | **With a 2x safety margin** | **about $20, under the $25 ceiling** |

## 5. Where this differs from what I said earlier in the session

1. Claude on Bedrock is **10 % dearer on the US geo profile** than the first-party list
   price I quoted ($1.10/$5.50 for Haiku 4.5 vs $1/$5; $2.20/$11 for Sonnet 5.5 vs $2/$10). The
   global profile matches first-party.
2. My open question "is there a per-call `Retrieve` charge on S3 Vectors?" is answered: no
   such line exists in the Price List (see the notes in section 2).
3. All other figures I quoted (S3 Vectors, Guardrails, AgentCore, Titan) match.

## 6. Teardown

| Command | Effect | Available |
|---|---|---|
| `make bootstrap-destroy` | Removes the free budget only | Phase 1 |
| `make destroy` | Removes the whole main stack, keeps the budget | Added with the main stack |
| `make destroy-all` | Removes the main stack, then the budget | Added with the main stack |

After Phase 2, `make destroy` removes the 15 Phase 2 resources (table, rows, 2 Lambdas, roles, policies, log groups,
budget guard). All of them cost $0 while idle; the budget stays.

## 7. Actual spend log

Estimates are only useful if they are checked against the bill. Cost Explorer lags by up to a day, so each line is
completed the next day.

| Date | What changed | Expected | Actual (from Cost Explorer) |
|---|---|---|---|
| 2026-10-05 | Account baseline before the project | n/a | about $0.105 for the month |
| 2026-10-07 | Phase 2 applied: DynamoDB table (5 rows), 2 Lambdas, 2 log groups, IAM; about 12 smoke-test invocations | $0.00 | *check 2026-10-08* |
