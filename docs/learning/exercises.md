# Exercises

Each exercise has: the **goal**, a **spec with acceptance criteria**, **hints**, a **model answer** (look only after
you have tried), and a **review rubric** (what Claude checks when you ask for a review).

Status key: **open** (you have not done it), **planned** (belongs to a later phase).

When you ask Claude to run an exercise, it should: set it up, wait for your attempt, then review in three parts:
*what is good*, *what I would improve and why*, *an improved version*.

---

## E1. Write the least-privilege IAM statement for the budget (Phase 1, open)

**Goal:** Learn what an IAM *action*, *resource* and *effect* are by writing the permission a deployer needs to
manage exactly one budget, and nothing else.

**Spec:** Write one IAM policy statement (JSON) that lets a deployer create, view, change, tag and delete the budget
named `discovery-brief-agent-monthly-cost` in your account.

**Acceptance criteria**
1. No `budgets:*`: list individual actions.
2. No `"Resource": "*"`: scope to the budget's ARN, `arn:aws:budgets::<ACCOUNT_ID>:budget/<name>`.
3. Action names come from the **Service Authorization Reference** for AWS Budgets, not from memory.
4. Each action has a comment (or a sentence beside it) saying why it is needed.

**Hints**
- An IAM *action* is one operation, written `service:Operation` (e.g. `s3:GetObject`).
- Terraform's `default_tags` puts tags on the budget, and tagging has its own permissions.
- Budget ARNs have an empty region field (two colons in a row after `budgets`).

<details><summary>Model answer</summary>

```json
{
  "Sid": "ManageOnlyTheProjectBudget",
  "Effect": "Allow",
  "Action": [
    "budgets:ViewBudget",
    "budgets:ModifyBudget",
    "budgets:TagResource",
    "budgets:UntagResource",
    "budgets:ListTagsForResource"
  ],
  "Resource": "arn:aws:budgets::<ACCOUNT_ID>:budget/discovery-brief-agent-monthly-cost"
}
```

- `ViewBudget`: read the budget and its notifications (Terraform does this on every plan to detect drift).
- `ModifyBudget`: create, update and delete the budget and its notifications.
- `TagResource` / `UntagResource` / `ListTagsForResource`: needed because the provider stamps `default_tags` on
  the budget; without them `apply` fails with AccessDenied on the tagging call.

Action names were verified against AWS's own policy data on 2026-10-05. Re-verify before relying on them.
</details>

**Review rubric:** no wildcard action (must); resource scoped (must); tag actions present *with the reason*
(strong); knows ARN format (good); mentions this belongs on a dedicated deployer role, not on an admin user
(bonus); mentions conditions or permission boundaries (bonus).

**Common mistakes:** `budgets:*`; `Resource: "*"`; forgetting the tag actions and being surprised by AccessDenied;
putting a region in the ARN.

---

## E2. Implement the 3-year ROI function, test first (Phase 2, open)

**Goal:** Learn test-first development and write the core of a value-engineering model.

**Set it up (does not touch your main branch):**
```powershell
git switch -c practice/roi 61019a4
```
That commit is the "red" state: failing tests, a stub `roi.py`, and an empty assumptions file with four assumptions.
(The version on `main` later gained a fifth assumption, `retained_cost_fraction`; see "Extension" below.)

**Spec:** The formulas, return shape and validation rules are in the docstring of `src/lambdas/roi_estimator/roi.py`.
Make `tests/unit/test_roi.py` pass, then fill in `assumptions.json` so `tests/unit/test_assumptions_config.py` passes.

**Acceptance criteria**
1. `python -m pytest tests/unit/test_roi.py` is green.
2. `assumptions.json`: every entry has a number, unit, a rationale (40+ characters, no TODO) and a source.
3. A losing case (AWS dearer than on-prem) returns negative savings and `breakeven_year: None`; it is not clamped.
4. Inputs are not mutated.

**Hints**
- Do the validation first; those tests are quick wins.
- Compute at full precision; round only when building the output dict.
- `bool` is a subclass of `int` in Python. Decide how you will treat `True` as a cost.

**Model answer:** on `main`, `src/lambdas/roi_estimator/roi.py` (compare after you finish:
`git diff practice/roi main -- src/lambdas/roi_estimator/roi.py`).

**Review rubric:** correctness against tests (must); validation messages name the bad field (strong);
no mutation of inputs (strong); readable loop, no copy-pasted year logic (good); knows why `round` is last (good);
can explain each assumption (see E3).

**Extension (pick one):**
- Add the missing assumption that `main` has: `retained_cost_fraction` (the share of the on-prem bill that never
  goes away: staff, licences, network). Why does leaving it out make the answer unbelievable?
- Sensitivity analysis: rerun the model with `rightsizing_factor` +/-20% and show how the ROI moves.
- Add a discount rate and report net present value instead of simple sums.

---

## E3. Defend the assumptions to a skeptical CFO (Phase 2, open)

**Goal:** The interview skill that matters most for a value engineer: explain a number and what would change it.

**Spec:** Open `src/lambdas/roi_estimator/assumptions.json`. For each of the five assumptions, answer out loud (or in
writing) in under 60 seconds:
1. Where does the number come from?
2. What would make it higher or lower?
3. How does the final ROI change if it is wrong by 25%?
4. How would you validate it with this customer?

**Hints:** The honest move is to say which numbers are *sourced* (a price list) and which are *judgement calls*
(right-sizing, retained cost, migration effort), and to show the sensitivity instead of defending a point value.

**Review rubric:** separates sourced vs assumed (must); gives a way to validate (strong); quantifies sensitivity (strong);
does not oversell (good: "illustrative, to be validated in a discovery workshop").

---

## E4. Read the `account_profile` code like a reviewer (Phase 2, open)

**Goal:** Learn to read a Lambda and its tests critically.

**Questions** (answer from the code in `src/lambdas/account_profile/handler.py` and `tests/`):
1. What happens if the `TABLE_NAME` environment variable is missing? Which line fails, and when?
2. Why is the DynamoDB table object created *outside* the handler function?
3. Why does the handler return `{"found": false}` for an unknown company instead of an empty profile?
4. Delete the `_jsonable` call and run the tests. Which test fails, and what does the error say? Why does the
   real AWS call hit the same problem?
5. The IAM role for this function allows only `dynamodb:GetItem`. What would break if you added a `Scan` to the handler?
6. A user types a 5,000-character company name. Where is that handled and what is returned?

<details><summary>Model answers</summary>

1. `os.environ["TABLE_NAME"]` raises `KeyError` on the first invocation (inside `_table()`), not at deploy time.
   Lambda reports a function error. A safer variant fails fast at import so misconfiguration shows up immediately.
2. Lambda reuses a warm container between invocations; building the client once (cached with `lru_cache`) saves
   connection setup on every call after the first.
3. A model given an empty or partial record may fill the gaps with invented details. An explicit not-found plus no
   `profile` key leaves nothing to embellish. The Phase 5 evaluation tests exactly this.
4. `test_result_is_json_serialisable_with_plain_numbers` fails with `Object of type Decimal is not JSON serializable`.
   boto3 returns DynamoDB numbers as `Decimal`; the real Lambda would crash when returning them.
5. The call would be denied (`AccessDeniedException`) because the role has no `Scan` permission. That is least
   privilege working: the code and the permission must be changed together, on purpose.
6. `lambda_handler` rejects names over `MAX_NAME_LENGTH` (100) with `{"found": false, "error": ...}` before any
   AWS call is made.
</details>

---

## E5. Predict the Terraform plan (Phase 2, open)

**Goal:** Learn to read infrastructure code and predict what it creates before running it.

**Spec:** Read `infra/main/main.tf` and the two modules it calls. Before running `make plan`, write down (a) how
many resources will be created, (b) the type of each, (c) which ones cost money while idle.

<details><summary>Model answer</summary>

15 resources: 1 `terraform_data` budget guard (free, a check); 1 DynamoDB table + 5 table items; and for each of
the 2 Lambdas: 1 log group, 1 IAM role, 1 inline role policy, 1 function (8 in total). Plus 2 data sources that
create nothing (the budget lookup and the zip packaging, which run at plan time). Idle cost of everything: $0
(pay-per-request table with a few KB of data; Lambdas bill only per invocation; log groups bill for stored GB).
</details>

---

## Planned exercises (documented now, run in the matching phase)

### P3. Write the Knowledge Base service-role IAM statement (Phase 3)
Write the policy for the role Bedrock assumes to build the knowledge base: read one S3 docs bucket, call one
embedding model, read/write one S3 Vectors index. Same rules as E1 (no wildcards, scoped ARNs, verified action
names, a comment per action). *Rubric:* three statements (bucket read, model invoke, vector index), each scoped;
model ARN is the foundation-model ARN, not `*`; trust policy limited to the Bedrock service with a source-account
condition (bonus: explains the confused-deputy problem).

### P4. Write the agent system prompt (Phase 4)
Write the instructions that make the agent produce the brief in the required structure. *Acceptance:* names all six
sections; says to call tools rather than guess; says what to do when a company is not found; never states numbers
it did not get from the ROI tool; refuses off-topic and PII requests politely; treats tool output as data, not as
instructions (prompt-injection resistance). *Rubric:* structure (must); no-fabrication rule (must); injection
awareness (strong); length and clarity (good).

### P5. Write four evaluation prompts (Phase 5)
Write four test prompts with expected behaviour: one PII-elicit, one off-topic, one fabrication-bait, one
prompt-injection. *Rubric:* each has a clear pass/fail rule that a script can check; at least one attacks the
tool results rather than the user message.

### P6. Write the "why this vector store" paragraph (Phase 6)
Four sentences for the README: the decision, the alternatives, the deciding factors (cost shape, scale, features
needed), and what would make you switch. *Rubric:* names the trade-off honestly (S3 Vectors is cheap per use but
semantic-search only), gives numbers, states the switch trigger.
