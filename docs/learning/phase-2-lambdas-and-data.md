# Phase 2: the action Lambdas, the data, and the tests

**What we built:** a DynamoDB table of five fictional companies; two Lambda functions (`account_profile`,
`roi_estimator`), each with its own IAM role and log group; 65+ unit tests; the main Terraform stack; a smoke test.
The third tool (`kb_retrieve`) arrives in Phase 3 with the knowledge base.
**Cost:** about $0 idle (see section 6).

---

## 1. Concepts, in plain English

**Lambda: a vending machine that only runs when someone presses a button.** You upload a small piece of code; AWS runs
it when something calls it and bills for the milliseconds used. The alternative is a server (EC2 or a container) that
runs, and bills by the hour, even when nobody uses it. We chose Lambda because **idle cost is $0** (decision 8).
Free tier: 1M requests and 400,000 GB-seconds a month (checked in the Price List on 2026-10-07).

**DynamoDB: a filing cabinet where every folder has a label.** The label is the *partition key* (here the company name
in lower case). `get("northwind logistics")` returns that folder fast. *On-demand* billing means you pay per read and
write, with nothing to size. Aurora/RDS would bill hourly for an instance; JSON files in S3 would work for tiny data but
a keyed lookup is the standard pattern. Items store typed values: S = string, N = number, L = list.

**One IAM role per Lambda: one badge per employee, not a shared master key.**
- `account_profile` gets exactly one DynamoDB action (`GetItem`) on exactly one table, plus permission to write its own logs.
- `roi_estimator` gets only its own logs, because it is pure arithmetic and calls no AWS service.
If a function has a bug or is attacked, the damage is limited to what its badge opens.

**The Gateway contract.** In Phase 4 the AgentCore Gateway will invoke each Lambda. For a Lambda target the *event is the
tool's arguments* (e.g. `{"company_name": "Northwind Logistics"}`), and whatever the function returns goes back to the
model as the tool result. The tool name arrives in the context (`client_context.custom`), as `target___tool`. Our handlers
serve one tool each, so they ignore it. (Re-verified in Phase 4.)

**pytest and moto: test without AWS.** pytest runs the tests. moto is a fake AWS held in memory: a test creates a pretend
DynamoDB table, calls our code, checks the answer. Nothing is billed and nothing leaves the laptop. An autouse fixture
removes `AWS_PROFILE` and sets fake credentials so a unit test *cannot* reach the real account by accident.

**Test-first ("red, then green").** Write failing tests that describe correct behaviour, then write the code that makes
them pass. The git history shows it: commit `61019a4` is the red state of the ROI model.

---

## 2. The code, file by file

### `src/lambdas/account_profile/handler.py`
1. **The event is the tool's arguments.** `lambda_handler(event, context)` reads `event["company_name"]`.
2. **Validate first.** The value came from a user, through a model. Reject missing, empty, non-string and over-100-character
   input with `{"found": false, "error": ...}`: a message the agent can act on, not a crash.
3. **`normalise()`** strips, collapses whitespace and lower-cases, so `"  northwind   LOGISTICS "` finds the same row.
   Terraform seeds the key as `lower(trimspace(name))`; a test fails if the data ever breaks that agreement.
4. **`@lru_cache` on `_table()`:** the DynamoDB connection is built once per warm container and reused.
5. **`_jsonable()`:** boto3 returns numbers as `Decimal`, which `json.dumps` rejects. Without this the function would pass a
   quick look and crash on the first real call.
6. **Explicit not-found.** An unknown company returns `found: false` with no `profile` key, so a model has nothing to embellish.
7. **One AWS call (`get_item`).** That is why its role needs exactly one DynamoDB action.

### `src/lambdas/roi_estimator/roi.py` (the model) and `handler.py` (the wrapper)
The model is plain Python with the formulas in its docstring. For each of 3 years:
`on_prem = cost x growth`, `aws_run = growth x (servers x rightsizing x server_cost + TB x TB_cost)`,
`retained = on_prem x retained_fraction`, `migration = servers x cost (year 1 only)`,
`aws_total = run + retained + migration`, `savings = on_prem - aws_total`. Then totals, `roi_pct = savings / aws_cost x 100`,
and `breakeven_year` (first year cumulative savings is >= 0, else `None`).
- **Retained cost** is the share of the on-prem bill that does not go away after migrating (staff, licences, network).
  Without it the model compares a *full* on-prem bill with bare AWS compute and shows an absurd 500% ROI that a CFO
  would reject on sight. Adding it was a deliberate honesty fix.
- **A losing case is reported as it is** (negative savings, no breakeven). A model that can only say yes has no credibility.
- **Assumptions live in `assumptions.json`, never in code**, and every one carries a value, unit, rationale and source.
  The handler returns them with each answer, so the brief shows what the numbers rest on.
- **The handler** loads the file, calls the model, turns `ValueError` into `{"ok": false, "error": ...}` (truncated to 200
  characters so a hostile input can't flood the agent's context), and echoes inputs and assumptions back.

### Tests
`tests/conftest.py` (isolation + moto table), `test_account_profile.py`, `test_seed_data.py` (the data stays synthetic:
no emails, phone numbers or SSN-like strings, and I checked those patterns catch planted examples),
`test_roi.py` (hand-computed numbers), `test_assumptions_config.py` (the file a CFO reads must be complete),
`test_roi_handler.py`. **A test that cannot fail proves nothing:** for each new check I confirmed it fails when it should.

### Terraform (`infra/main` plus two modules)
- [`modules/storage_data`](../../infra/modules/storage_data/main.tf): the table (pay-per-request, no deletion protection and no
  point-in-time recovery because it is regenerable demo data) and one item per account, read from `data/accounts.json`.
- [`modules/lambda_function`](../../infra/modules/lambda_function/main.tf): the reusable unit. Zips the code, creates a log group
  with retention, a role that only the Lambda service can assume, an inline policy (logs for this group only, plus any extra
  statements passed in), and the function (`python3.14`, `arm64`, 128 MB, 10 s timeout, JSON logs).
- [`infra/main/main.tf`](../../infra/main/main.tf): the **budget guard** (asks AWS whether the budget exists; the plan fails
  if not), then the table, then the two functions. Each permission carries a comment saying why.

---

## 3. Decisions and trade-offs
- **Native DynamoDB attributes** over one JSON-blob attribute: slightly more Terraform, but real types, and it teaches the
  Decimal pitfall that bites everyone once.
- **`arm64` over `x86_64`:** 20% cheaper per GB-second ($0.0000133334 vs $0.0000166667, Price List 2026-10-07), same request
  price, and all managed runtimes support it. Pure-Python code needs no changes.
- **`python3.14`:** supported until 2029-06-30 (Lambda runtimes page, 2026-10-07) and matches the laptop's Python.
- **One reusable `lambda_function` module** over copy-paste: every function gets a role, a log group and a least-privilege
  policy the same way, so a new tool cannot be added "the lazy way".
- **Log groups created by Terraform with retention:** otherwise Lambda creates them with *never expire*, which quietly bills
  forever, and the role would need `CreateLogGroup`.
- **No reserved concurrency:** a new account has a low default concurrency limit, and reserving some can fail. The cost
  protection is the harness caps in Phase 4.

---

## 4. Gotchas
1. `Decimal` vs JSON (see `_jsonable`).
2. DynamoDB through boto3 rejects Python `float`; tests parse the seed JSON with `parse_float=Decimal`.
3. Python caches `__pycache__` folders; they must be excluded from the zip or the package hash changes for no reason.
4. A Lambda deployed as a flat zip has no package name, so `handler.py` imports `roi` directly; under pytest it is a package.
   The `try/except ImportError` in `roi_estimator/handler.py` handles both.
5. Windows quoting and expired sessions (see Phase 1).

---

## 5. Interview questions, with model answers

**Q1. Why does each Lambda get its own IAM role?**
> "Blast radius and clarity. If every function shared one role it would need the union of everyone's permissions, so a bug
> in the pricing function could read the customer table. With one role each, `roi_estimator` can only write logs and
> `account_profile` can only call `GetItem` on one table. It also makes audits readable: the role's name tells you what
> it's for and the policy tells you exactly what it can do."

**Q2. What breaks at 100x traffic?**
> "Lambda scales out on its own, so the compute isn't the first problem. I'd check, in order: the account concurrency
> limit; DynamoDB (on-demand scales, but a hot partition key could throttle, though ours is one lookup per request); the
> downstream model's rate limits, which are the real constraint; and cost, because the model and guardrail tokens dominate,
> not Lambda. I'd also want alarms on throttles and errors, and I'd load-test the whole chain rather than assume."

**Q3. How do you justify the ROI assumptions to a skeptical CFO?**
> "I don't defend a single number; I show where each came from and how sensitive the answer is. Prices are sourced from the
> public price list. Right-sizing, retained cost and migration effort are judgement calls, and I say so, show the ROI at
> plus and minus 25% on each, and propose validating them in a discovery workshop with the customer's real data. The model
> also reports a losing case honestly. That candour is what makes the winning case believable."

**Q4. Why test with a fake AWS instead of the real one?**
> "Speed, cost and safety: unit tests run in a couple of seconds, cost nothing, and cannot damage a real account. But they
> only prove the code is right. A separate smoke test against the deployed functions proves the deployment is right: the
> zip, the role, the seed data, the environment variable. You need both."

---

## 6. Deployment record
*Filled in after `make apply`: plan summary (resources to create), idle cost, smoke-test result, anything unexpected.*

---

## 7. Check yourself
- Why does a Lambda with a bug in it matter less when it has a one-action role?
- What does `lru_cache` buy you in a Lambda, and when does it NOT help?
- Why does `retained_cost_fraction` exist? What happens to ROI if you set it to 0?
- What would you change to support 5,000 companies instead of 5?

Exercises for this phase: **E2, E3, E4, E5** in [exercises.md](exercises.md).
