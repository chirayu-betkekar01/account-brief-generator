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

---

## 3. Phase log

### Phase 1: budget alarm and foundations *(applied; exercise and interview Qs pending)*
- Built and **applied**: one `aws_budgets_budget` ($25/month, 4 actual + 1 forecast alert, 1 e-mail subscriber). Cost: $0. Verified from AWS's side with `aws budgets describe-budget`, not just Terraform's own report.
- Tooling: Terraform 1.16.4, GNU make 4.4.1, AWS CLI 2.37.9, Python venv with pytest/boto3/moto/pre-commit/streamlit.
- Sign-in: IAM user + MFA, `aws login` (short-lived credentials, nothing long-lived on disk). Terraform picked the profile up via `AWS_PROFILE`; no workaround was needed.
- Workflow learned: `plan -out=tfplan` saves exactly what you reviewed; `apply tfplan` then executes only that. The plan is a preview, never a file you edit.
- **Your exercise:** IAM policy statement allowing a deployer to manage only this budget. *(pending)*
- Lessons banked:
  1. An unverified summary (the Budgets IAM action list) was wrong; the verified list came from AWS's own policy dataset. Verify, then trust.
  2. The `.example` template is tracked by git; real values belong in the git-ignored copy. A real e-mail was typed into the template and caught before it was committed.
  3. The account already showed about $0.10 of spend this month before we created anything, and the account-wide budget counts it against the $25.
  4. A script that "works" can still be wrong: the first price check returned a plausible but incorrect Haiku price until it was made to reject ambiguous matches.

---

## 4. Interview Q&A

*(Format: question, your answer, feedback, a stronger answer.)*

| Phase | Question | Your answer | Feedback | Stronger answer |
|---|---|---|---|---|
| | | | | |

---

## 5. Open questions

- Does the AgentCore harness expose tool results in its stream (needed for the post-answer grounding check)? *(Phase 4)*
- Which AgentCore microVM generation (v1 or v2) does the harness bill at? *(measure in Phase 4)*
