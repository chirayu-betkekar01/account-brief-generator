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
| **Embedding** | A text's meaning turned into a list of numbers (1,024 for Titan V2). Similar meanings give similar lists. |
| **Vector / cosine similarity** | A vector is that list of numbers; cosine similarity measures how closely two vectors point the same way. |
| **Semantic vs hybrid search** | Semantic ranks by meaning only; hybrid adds keyword matching. S3 Vectors is semantic-only, so a literal term can lose to a closer-in-meaning document. |
| **RAG** | Retrieval-augmented generation: fetch relevant passages first, then let the model answer from them. The main defence against invented facts. |
| **Chunking** | Cutting documents into pieces that are each about one thing, with a little overlap. Ours stay whole (about 200 tokens against a 512 limit). |
| **Knowledge Base (Bedrock)** | The managed pipeline: read S3 files, chunk, embed, store vectors, answer `Retrieve` calls. |
| **Ingestion job** | The run that reads the documents, embeds them and fills the index. Terraform cannot start it; `make ingest` does. |
| **Metadata file** | `<doc>.metadata.json` beside a document; its attributes (title, source_url...) come back with each passage so the agent can cite. |
| **S3 Vectors** | Vector storage inside S3: pay per use, no hourly floor, semantic search only. |
| **Non-filterable metadata** | Metadata stored with a vector but not usable in filters. Bedrock needs its two bookkeeping keys marked this way. |
| **Relevance score** | How close a passage is to the question (0 to 1 here). Search always returns something, so the score is how you tell relevant from irrelevant. |
| **Agent vs workflow** | A workflow is steps you wrote; an agent is a loop where a model decides the next step. More flexible, less predictable, so it needs limits and checks. |
| **AgentCore harness** | The managed agent loop: model, system prompt, tools and limits as configuration. Runs each session in an isolated micro virtual machine and streams events back. |
| **AgentCore gateway** | A front door that publishes Lambdas (and APIs) as tools over MCP, with IAM sign-in. The model sees each tool as `target___tool`. |
| **MCP (Model Context Protocol)** | A standard way for agents to discover and call tools, so tools are not tied to one agent framework. |
| **Guardrail policies** | The checks inside a Bedrock guardrail. We use four: sensitive information (PII), denied topics, a prompt-attack content filter, and contextual grounding. |
| **Denied topic** | A subject the guardrail refuses. It can only deny; it cannot say "allow only this". Detection is semantic and imperfect (it missed a pizza question). |
| **Prompt attack filter** | A guardrail content filter for jailbreaks and "ignore your instructions" on what the user types. Input only. |
| **Contextual grounding check** | Scores whether an answer is supported by a source. Needs the source and question tagged, so it runs via `ApplyGuardrail` after the answer. On our task it could not tell faithful from fabricated. |
| **`ApplyGuardrail`** | Runs a guardrail on text you supply, without calling a model. Returns which policy matched which text, which is how we found the headquarters false positive. |
| **Allow-list (`allowedTools`)** | Which tools the model is offered. Harness sessions include a bash shell and a file editor unless you restrict them. |
| **Per-call override** | Anything the harness is configured with (model, system prompt, tools, guardrail) can be replaced by the caller in one request. IAM cannot stop it. |
| **Confused deputy** | Tricking a service that has your permissions into acting for the wrong party. Defence: `aws:SourceAccount` and `aws:SourceArn` conditions in the trust policy. |
| **Eventual consistency (IAM)** | A new role takes a second or two to be usable everywhere. "Not authorised" right after creating it usually means wait and retry. |
| **Metric filter** | A rule that turns matching log lines into a CloudWatch metric (for example, every `ERROR` line becomes a 1). |
| **Deterministic check** | Plain code comparing an answer with the tool results (links, service names, numbers). No AI, so no AI errors. |
| **Tainted resource (Terraform)** | A resource marked for destroy and rebuild on the next apply, often after a half-failed apply. `terraform untaint` clears the mark without touching AWS. |

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
| 19 | **A `kb_retrieve` Lambda, not the Gateway's knowledge-base connector** | The built-in connector | AWS documents the connector as supported only for Bedrock *Managed* Knowledge Bases, a different, dearer product than our S3 Vectors one. | Moving to a Managed Knowledge Base (then drop the Lambda). |
| 20 | **Index: float32, 1024 dimensions, cosine; FIXED_SIZE chunks of 512 tokens, 10% overlap** | 256/512 dimensions, hierarchical or semantic chunking | Matches Titan V2's default quality; hierarchical chunking can exceed S3 Vectors' metadata limit; our documents are short anyway. | Much larger or structured documents. |
| 21 | **Paraphrased, sourced, dated documents with metadata sidecars** | Copying AWS text verbatim; unsourced notes | Avoids misquoting and copyright issues, and every passage can be traced and re-checked. | A licensed documentation mirror. |
| 22 | **Test what the agent receives (default 4 passages), not an arbitrary top-3** | Loosening the test silently | The right document ranked #4 for one question; the honest test is whether it is among the passages the agent reads. The finding is recorded, not hidden. | n/a |
| 23 | **KB role scoped to the `docs/` prefix, one model, one index; no `ListFoundationModels`** | AWS's broader example policy | Least privilege: read-only on one prefix, five documented vector actions on one index. It worked first time without the extra list actions. | A failure traced to a missing permission. |
| 24 | **AgentCore harness (configuration) for the agent loop** | AgentCore Runtime with our own code, Step Functions, Bedrock Agents Classic | Least code; managed loop, isolation and limits. Classic is closed to new accounts. | Needing custom control flow, multi-agent patterns or hooks the harness lacks. |
| 25 | **`allowed_tools` leaves only the gateway; shell and file tools off** | Leave the defaults | A brief writer needs neither, and a shell is what a prompt-injection attack wants. Proven by A/B: default = no shell offered, override = `echo` ran. | A genuine need for code execution (then sandbox and scope it). |
| 26 | **ADDRESS blocked in prompts, masked in answers** | Block both ways | The detector flagged a company's "City, State" headquarters; blocking a whole brief over a city name is the worse failure. | A false-positive rate measured near zero, or real personal addresses in the data. |
| 27 | **Deterministic checks (links, service names, ROI figures) as the hallucination detector; grounding scores informational** | The guardrail's grounding filter | Measured: it scored a faithful section 0.17 and one with five invented services 0.05. The checks separated all four sample briefs. | A tuned grounding setup that separates cases on our data. |
| 28 | **Numbered guardrail version, new one cut when the policy fingerprint changes** | Point the harness at DRAFT | An edit cannot silently change production behaviour. | n/a |
| 29 | **Separate gateway and harness roles; confused-deputy conditions on the gateway role** | One shared role; unconditioned trust | Different jobs, different badges; only a gateway in this account named like ours can assume the gateway role. | n/a |
| 30 | **Treat the guardrail as a default for honest callers, not a control; production needs a gate in front** | Claim the guardrail "enforces" safety | Measured: a per-call `model` override removed it; `allowedTools` can re-enable the shell. IAM does not inspect request bodies. | Building the gate (an API in front, or a harness lifecycle hook that denies overrides). |
| 31 | **Service-name check compares words, so it can over-flag** | An alias table (IAM = Identity and Access Management) | A false alarm costs a glance; a missed invention costs credibility. Pinned by a test. Phase 5 measures the false-alarm rate. | A measured false-alarm rate high enough to hide the real findings. |

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

### Phase 3: knowledge base *(deployed 2026-10-07; full notes in `docs/learning/phase-3-knowledge-base.md`)*
- Built and **applied** (48 resources, under $0.01, $0 idle): docs bucket + 34 files, S3 Vectors bucket and index, least-privilege service role, Bedrock knowledge base and data source, the `kb_retrieve` Lambda.
- `make ingest`: 17 of 17 documents indexed, 0 failed. Smoke test: 22 of 22. IAM read back from AWS matched the design.
- Retrieval experiment: expected document ranked #1 for four of five questions and #4 for the fifth; an off-topic question still scored 0.534 (relevant 0.7 to 0.84).
- Lessons banked:
  1. Semantic search ranks by intent; search always returns something, so use the score.
  2. Verify SDK field names against the service model (the ingestion statistics names in a first draft did not exist).
  3. Stage commits by path; a `git add -A` earlier in a command swallowed three commits into one (fixed with a soft reset, local only).
  4. Source content must be checked against the live page: Mainframe Modernization is closed to new customers, which changes the advice.
  5. A Gateway connector's name ("Knowledge Bases") can hide a restriction ("Managed" only); read the fine print.

### Phase 4: agent, guardrail and monitoring *(deployed 2026-10-07; full notes in `docs/learning/phase-4-agent.md`)*
- Built and **applied** in two steps (12 + 12 resources, 87 in the main stack, $0 idle): guardrail and a numbered version, gateway role and gateway with three Lambda targets, harness role and harness, an unattached invoker policy, then monitoring (log retention, 6 metric filters, 4 alarms, a dashboard). The command-line client and its checks are committed (243 tests, six deliberate breaks all caught).
- Verified: IAM read back from AWS matched the design; the live client ran a full brief (8 of 10 checks passed, both failures real); adversarial prompts were each stopped by at least one layer; an A/B test proved the tool allow-list removes the shell.
- What went wrong, in order: IAM propagation (retry fixed it); a provider bug that tainted a working harness (declared the default, untainted, deleted nothing); the answer cut off at 1,000 tokens (per-call limit never set); the PII filter flagged a headquarters city; the model invented AWS services in 3 of 4 briefs; the grounding filter could not tell faithful from fabricated; a wrong claim of mine about `skip_destroy`.
- Lessons banked:
  1. Safety controls must be tested against your own realistic outputs: `ApplyGuardrail` tells you exactly what matched.
  2. A small model follows formatting rules reliably and "don't invent" rules unreliably; prompts reduce the rate, detection is not optional.
  3. Test any control against known-good and known-bad inputs before trusting it. The grounding filter failed that test.
  4. A measurement that matches to two decimals after you changed something is a bug until proven otherwise (a patch silently did not apply).
  5. Everything the harness is configured with can be overridden per call, and IAM cannot prevent it.
  6. When Terraform and reality disagree, check the real resource first; prefer the fix that deletes nothing.
  7. Verify a claim before saying it (`skip_destroy`), and correct it plainly when wrong.

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
| 3 | Why S3 Vectors for the knowledge base? | *(model answer)* | | Pay-per-use with no hourly floor, so idle is about $0 (OpenSearch Serverless has a minimum that would dominate the budget); corpus is about 4,000 tokens. Trade-off: semantic-only, measured (a keyword-heavy question ranked the best document 4th). |
| 3 | When would you outgrow it? | *(model answer)* | | Hybrid search, richer metadata filtering than 35 keys, or low latency at high query rates; or when retrieval hit-rate plateaus. Keep chunking and the evaluation set constant to compare fairly. |
| 3 | How do you keep RAG answers trustworthy? | *(model answer)* | | Curated, cited, dated sources; use the relevance score with a threshold; make 'not found' an explicit answer; evaluate with fixed questions and fabrication traps; add a post-answer grounding check. |
| 3 | The model says something your documents do not support. What do you do? | *(model answer)* | | Decide whether retrieval missed or generation drifted by checking the passages returned; fix corpus/query or tighten instructions and add a grounding check; add the case to the evaluation set. |
| 4 | Walk me through the architecture and where the security boundaries are. | *(model answer)* | | Client signs a request; harness runs the model in a loop with a guardrail on every call; tools only via an IAM-authenticated gateway to three Lambdas, each with its own role; harness role scoped to one model, one guardrail, one gateway; allow-list removes the default shell. Weak spot: callers can override guardrail and allow-list per request, so real customers need a gate in front. |
| 4 | Guardrails are on. Are you safe from prompt injection? | *(model answer)* | | No. The prompt-attack filter screens only what the user types, not tool results; the corpus is small and curated; the prompt treats tool output as data; the model has three tools and no shell; hard caps; checks on the finished answer; and a caller can override the guardrail entirely. |
| 4 | The model sometimes invents things. What do you do? | *(model answer)* | | Measure (3 of 4 briefs had invented services), tighten the prompt, test the platform's grounding filter (it could not separate cases), then use deterministic checks against the retrieved passages and tool results. Keep them blunt: false alarm beats a miss. Compare a stronger model with the same checks. |
| 4 | A safety filter blocked your own legitimate output. How do you handle it? | *(model answer)* | | Find exactly what matched (`ApplyGuardrail` reports it), decide block vs degrade per control (ADDRESS: block in prompts, mask in answers), change the prompt to avoid the trigger, and test filters against realistic outputs before launch. |

---

## 5. Open questions

- Does the AgentCore harness expose tool results in its stream (needed for the post-answer grounding check)? *(Phase 4)*
- Which AgentCore microVM generation (v1 or v2) does the harness bill at? *(measure in Phase 4)*
- **Data provenance and ranges.** Should each ROI input carry a source label (customer-stated / benchmark / unknown) and should the tool return low/base/high cases, with the most sensitive assumption driving the first discovery question? *(proposed for Phase 4; add a provenance note to the overview limitations)*
- Phase 1 leftovers: the IAM statement (E1) and Q2 remain open in `docs/learning/exercises.md`.
- **Relevance threshold.** An off-topic question scored 0.534 and relevant ones 0.7 to 0.84. Where should the cutoff live (the Lambda, the agent's instructions, or both) and what value? About 0.6 on this corpus; re-measure after any corpus or model change. *(decided in Phase 4: 0.60 in the system prompt and in the client's link check; the model obeys it imperfectly; measure in Phase 5)*
- **Closing the guardrail bypass.** Per-call overrides let a caller drop the guardrail or re-enable the shell. Would a harness `before_invocation` lifecycle hook (a Lambda that denies requests carrying overrides) fully close it, and what does it add in cost and latency? *(documented in the harness docs, not built; candidate for Phase 6 or "what I would do for production")*
- **Denied-topic coverage.** The CLASSIC tier let "best pizza topping" through. Would the STANDARD tier (needs a cross-Region guardrail profile) catch it, and is the extra setup worth it? *(measure in Phase 5)*
- **Does a stronger model obey "only name services you were given"?** Nova 2 Lite did not, reliably. *(Phase 5: Haiku 4.5 on the same checks)*
- **Alias handling in the service-name check.** Exercise E8. How much does it reduce false alarms without letting a real invention through?
- **Real cost per brief.** Model tokens measured at about $0.011; guardrail and runtime shares come from Cost Explorer. *(check 2026-10-08, then after the Phase 5 batch)*
