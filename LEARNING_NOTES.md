# Learning notes: Discovery Brief & ROI Agent

A living study guide. Each phase adds glossary terms, decisions and tradeoffs, and interview Q&A.
At the end it is distilled into `docs/interview-prep.md` (one page).

---

## 1. Glossary (plain English)

| Term | Plain-English meaning |
|---|---|
| **AWS account** | The billing and security boundary. Everything you create lives in one; the bill goes to it. |
| **Region** | A physical cluster of AWS data centres (e.g. `us-east-1`, N. Virginia). Most resources live in exactly one. |
| **IAM** | Identity and Access Management: who (identity) can do what (actions) on which things (resources). |
| **IAM role** | A set of permissions that something can *assume* temporarily, like a visitor badge. Lambdas and agents each get their own. |
| **Least privilege** | Grant only the exact permissions needed, on only the exact resources. A bug or attacker can then only do that much damage. |
| **IAM Identity Center (SSO)** | Sign in once in a browser and get short-lived credentials, instead of long-lived access keys sitting on your disk. |
| **Terraform** | Describes infrastructure in text files and makes AWS match them ("infrastructure as code"). Reviewable, repeatable, deletable. |
| **Provider** | The Terraform plug-in that knows how to talk to one platform (here: AWS). |
| **Resource** | One thing Terraform manages, e.g. an S3 bucket or a budget. |
| **Variable / output** | An input to a configuration / a value it publishes for others to use. |
| **Module** | A reusable bundle of resources, like a function in code. |
| **State** | Terraform's record of what it has built. Lets it compute the difference between your files and reality. Contains account IDs, so it is never committed. |
| **Plan / apply** | `plan` = show what *would* change (read-only). `apply` = make it so. We always read the plan first. |
| **Lock file** | `.terraform.lock.hcl` pins the exact provider version and checksums so every machine builds the same thing. Committed on purpose. |
| **Saved plan** (`-out`) | A plan written to a file so `apply` runs exactly that and nothing recomputed. A plan alone is only a prediction. |
| **ARN** | Amazon Resource Name: the unique address of any AWS thing, e.g. `arn:aws:budgets::<account>:budget/<name>`. IAM policies point at ARNs. |
| **Tags / `default_tags`** | Key-value labels on resources (here `Project=...`). The Terraform provider can stamp them on everything; tagging has its own IAM permissions. |
| **AWS Budgets** | Watches spending and e-mails you at thresholds. A smoke alarm, not a sprinkler: it warns, it does not stop spending. |
| **Serverless / pay-per-use** | You pay only while something runs. Idle cost is about zero. |
| **TCO** | Total cost of ownership: all costs of an option over its life, not just the sticker price. |
| **IAM Action** | One specific operation a caller may ask AWS to perform, written `service:Operation` (e.g. `s3:GetObject`, `lambda:InvokeFunction`). Least privilege starts with listing only the actions needed. |
| **IAM statement** | One permission sentence: Effect (Allow/Deny) + Actions + Resources. A policy is a list of statements. |
| **Lambda** | Code that runs only when called and bills per millisecond; $0 while idle. A vending machine, not a server. |
| **Lambda runtime / architecture** | The language version (`python3.14`) and the CPU type (`arm64`, about 20% cheaper per GB-second than `x86_64`). |
| **Event contract** | What a Lambda receives and returns. For a Gateway tool the event IS the tool's arguments and the return value goes back to the model. |
| **DynamoDB** | Key-value database: look up one item by its key. Billed per read/write ("on-demand"), so idle cost is about $0. |
| **Partition key** | The label on a DynamoDB folder. Here, the lower-cased company name. |
| **DynamoDB types** | Items store typed values: S = string, N = number, L = list. boto3 returns numbers as `Decimal`, which `json.dumps` rejects. |
| **pytest / moto** | pytest runs tests; moto is a fake AWS held in memory, so tests cost nothing and cannot touch the real account. |
| **Test-first (red, then green)** | Write failing tests that describe correct behaviour, then the code that passes them. Commit `61019a4` is the red state of the ROI model. |
| **Smoke test** | A short check against the DEPLOYED system. Unit tests prove the code is right; the smoke test proves the deployment is right. |
| **Retained cost** | The share of the on-prem bill that survives migration (staff, licences, network). Leaving it out inflates ROI absurdly. |
| **Outside-in vs inside-out** | Pre-sales estimate from public info and benchmarks (low confidence) vs from the customer's own measured data (high confidence). |

*(More terms are added as each phase introduces them: Lambda, DynamoDB, embeddings, RAG, Guardrails, AgentCore, MCP, inference profile, ...)*

---

## 2. Decisions and tradeoffs

| # | Decision | Alternatives considered | Why | What would change my mind |
|---|---|---|---|---|
| 1 | **AgentCore harness + Gateway** instead of Bedrock Agents | Bedrock Agents "Classic" | AWS closed Classic to new accounts on 2026-07-30 (`CreateAgent` returns 403, no exceptions) and freezes its model catalog. AgentCore is the supported successor and has native Terraform resources. | If the account had used Agents in the last 12 months *and* a customer needed Classic parity. |
| 2 | **S3 Vectors** as the vector store | OpenSearch Serverless, Aurora PostgreSQL, Managed Knowledge Base | Pay-per-use ($0.06/GB-month, $2.50 per 1M queries), no hourly floor, native Terraform. Our corpus is about 1 MB, so storage cost is fractions of a cent. | Need hybrid (keyword + semantic) search, metadata filtering beyond 35 keys, or very low latency at high QPS. |
| 3 | **Nova 2 Lite** as the agent model | Claude Haiku 4.5, Nova Lite/Micro | About $0.05-0.06 per full brief; Amazon models need no Marketplace subscription or use-case form. Model ID is a variable, so we measure alternatives in Phase 5. | Evaluation shows it fails tool use or format rules more than Haiku does. |
| 4 | **`us.` inference profile** (not `global.`) | `global.` profile (about 10% cheaper) | Keeps inference in three US regions and lets IAM name exact destination regions (least privilege). Cost difference is under a tenth of a cent per brief. | A customer with no residency constraints and very high volume. |
| 5 | **Separate bootstrap stack** for the budget | One stack for everything | The cost alarm must exist before anything billable, and must survive `make destroy` of the main stack. | A team with a landing-zone account factory that creates budgets centrally. |
| 6 | **Budget tracks gross cost** (credits excluded) | Net cost | Promotional credits must not hide a runaway bill. | None; it is a safety choice. |
| 7 | **Budget is a warning, not a brake** | Budget actions (auto-apply a deny policy) | AWS refreshes Budgets up to 3x/day, 8-12 h apart; spend can pass a threshold before the alert. So hard limits live in the harness (`max_iterations`, `max_tokens`, `timeout`). | Production: add budget actions plus Cost Anomaly Detection. |
| 8 | **Serverless-only design** | EC2/containers, always-on search | Idle cost is $0/hour, so forgetting to tear down costs cents, not dollars. | Sustained high traffic where reserved capacity is cheaper. |
| 9 | **Local Terraform state (for now)** | S3 backend with locking | One person, one sandbox. State is git-ignored. | Any team use: S3 + DynamoDB/S3 locking, per-environment state. |
| 10 | **Lock file committed, LF line endings pinned** | Ignore both | Reproducible provider versions; CRLF would break `make` and Linux CI. | n/a |
| 11 | **Maths in plain Python, not in the model** | Let the LLM calculate the ROI | Deterministic, unit-testable, auditable; a model can mis-multiply or invent a figure. | A tool that cannot be expressed as code (e.g. free-text risk judgement). |
| 12 | **Assumptions in a file, returned with every answer** | Hard-coded constants | A skeptical CFO can challenge each number; each has value, unit, rationale and source. | n/a |
| 13 | **Retained-cost assumption in the ROI model** | Compare full on-prem bill to bare AWS compute | Without it ROI looks like 500%+ and no one believes it. | A customer whose staff and licences genuinely disappear (rare). |
| 14 | **One reusable `lambda_function` module** | Copy-paste per Lambda | Every tool gets its own role, log group with retention, and least-privilege policy the same way. | Functions with very different shapes (VPC, layers, containers). |
| 15 | **`python3.14` on `arm64`, 128 MB, 10 s timeout** | x86_64, bigger memory | arm64 is 20% cheaper per GB-second (Price List, 2026-10-07); runtime supported to 2029-06-30; short timeout is a cost cap. | A dependency with no arm64 build. |
| 16 | **Terraform creates the log groups (14-day retention)** | Let Lambda create them | Auto-created groups never expire (billed forever) and the role would need `CreateLogGroup`. | n/a |
| 17 | **Native DynamoDB attributes** | One JSON blob per item | Real types and future queryability; teaches the Decimal pitfall. | Truly schemaless payloads. |
| 18 | **Apply from a saved plan; verify after** | `apply` with auto-approve | Executes exactly what was reviewed; post-apply read-back covers what a plan cannot show (IAM JSON). | n/a |

---

## 3. Phase log

### Phase 1: budget alarm and foundations *(applied; IAM exercise and Q2 parked, revisit after Phase 2)*
- Built and **applied**: one `aws_budgets_budget` ($25/month, 4 actual + 1 forecast alert, 1 e-mail subscriber). Cost: $0. Verified from AWS's side with `aws budgets describe-budget`, not just Terraform's own report.
- Tooling: Terraform 1.16.4, GNU make 4.4.1, AWS CLI 2.37.9, Python venv with pytest/boto3/moto/pre-commit/streamlit.
- Sign-in: IAM user + MFA, `aws login` (short-lived credentials, nothing long-lived on disk). Terraform picked the profile up via `AWS_PROFILE`; no workaround was needed.
- Workflow learned: `plan -out=tfplan` saves exactly what you reviewed; `apply tfplan` then executes only that. The plan is a preview, never a file you edit.
- **Your exercise:** IAM policy statement allowing a deployer to manage only this budget. *(parked: you asked what an "Action" is; revisit with the Service Authorization Reference)*
- Lessons banked:
  1. An unverified summary (the Budgets IAM action list) was wrong; the verified list came from AWS's own policy dataset. Verify, then trust.
  2. The `.example` template is tracked by git; real values belong in the git-ignored copy. A real e-mail was typed into the template and caught before it was committed.
  3. The account already showed about $0.10 of spend this month before we created anything, and the account-wide budget counts it against the $25.
  4. A script that "works" can still be wrong: the first price check returned a plausible but incorrect Haiku price until it was made to reject ambiguous matches.

### Phase 2: Lambdas, DynamoDB, tests, main stack *(deployed 2026-10-07; full notes in `docs/learning/phase-2-lambdas-and-data.md`)*
- Built and **applied** (15 resources, $0 idle): accounts table with 5 synthetic companies, `account_profile` and `roi_estimator` Lambdas, each with its own role and 14-day log group, behind a budget guard that fails the plan if the alarm is missing.
- Tests: 79 unit tests (fake AWS) plus a 12-check smoke test against the real functions. All pass.
- Process change: from this phase the build leads and teaching is documented in `docs/learning/` for later conversations; exercises are no longer gated (see `docs/learning/exercises.md`).
- Verified after apply with `aws iam get-role-policy`, `aws lambda get-function-configuration`, a table scan and the logs: everything matched the plan's intent.
- Lessons banked:
  1. A plan cannot show values that are "known after apply" (the IAM policy JSON); review the intent, then verify the result.
  2. boto3 needs `botocore[crt]` to use `aws login` credentials.
  3. DynamoDB `ItemCount` lags about six hours; count with a scan.
  4. Git Bash rewrites `/aws/...` paths; set `MSYS_NO_PATHCONV=1`.
  5. A pre-sales ROI is a hypothesis with a confidence level, not a result (see open questions).

---

## 4. Interview Q&A

*(Format: question, your answer, feedback, a stronger answer.)*

| Phase | Question | Your answer | Feedback | Stronger answer |
|---|---|---|---|---|
| 1 | A customer's finance lead is nervous about a surprise AWS bill. What do you put in place? | A budget limit that caps spend, plus alerts at several thresholds. | Alerts are right. **A budget does not cap spending**; it only warns. Know your own thresholds (20/50/80/100% actual + 100% forecast). | Be honest that a budget is a warning, then layer: tags + Cost Explorer + actual and forecast alerts to finance and engineering; Cost Anomaly Detection for spikes; hard limits (budget actions with a deny policy, limits on what can be created, app-level caps); pay-per-use design and a cost-per-request figure for forecasting. |
| 1 | Why isn't a budget alert enough, and what would you add? | *(parked)* | | Alerts lag by hours (Budgets refreshes up to 3x/day) and do not stop anything. Add anomaly detection, budget actions, and caps inside the application. |
| 1 | What does `terraform plan` guarantee, and what doesn't it? | A preview of what the infrastructure will look like once applied. | Right idea. Missing the "doesn't guarantee" half, which interviewers press on. It applies to any environment, not just production. | A saved plan (`-out`) makes apply execute exactly that diff. It does not guarantee success (permissions, quotas, name conflicts surface at create time), shows no cost, can't show "known after apply" values, and can't see anything outside state. |
| 2 | Why does each Lambda get its own IAM role? | *(not asked live; model answer)* | | Blast radius and clarity: a shared role needs the union of everyone's permissions, so a bug in one function could read another's data. One role each: `roi_estimator` can only write logs, `account_profile` can only `GetItem` on one table. |
| 2 | What breaks at 100x traffic? | *(model answer)* | | Lambda scales itself; check account concurrency, DynamoDB hot keys (ours is one lookup per request), the model's rate limits (the real constraint), and cost (tokens dominate). Alarm on throttles and errors, and load-test the whole chain. |
| 2 | How do you justify ROI assumptions to a skeptical CFO? | *(model answer)* | | Separate sourced numbers (price list) from judgement calls (right-sizing, retained cost, migration effort); show sensitivity (26% to 104% ROI across one assumption); propose validating in a workshop; report losing cases honestly. |
| 2 | Where does the customer's data come from in real pre-sales? | *(discussed live)* | You were right to challenge it: an SE rarely has accurate numbers before the first meeting. | Start outside-in (public info, benchmarks, low confidence); get ballparks in the meeting; move inside-out with their inventory and finance data or an assessment tool; present ranges, and use sensitivity to choose which discovery question to ask first. |

---

## 5. Open questions

- Does the AgentCore harness expose tool results in its stream (needed for the post-answer grounding check)? *(Phase 4)*
- Which AgentCore microVM generation (v1 or v2) does the harness bill at? *(measure in Phase 4)*
- **Data provenance and ranges.** Should each ROI input carry a source label (customer-stated / benchmark / unknown) and should the tool return low/base/high cases, with the most sensitive assumption driving the first discovery question? *(proposed for Phase 4; add a provenance note to the overview limitations)*
- Phase 1 leftovers: the IAM statement (E1) and Q2 remain open in `docs/learning/exercises.md`.
