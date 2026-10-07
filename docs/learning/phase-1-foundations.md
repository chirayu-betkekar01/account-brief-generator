# Phase 1: foundations and the budget alarm

**What we built:** one free AWS resource, a monthly budget with e-mail alerts, plus the tooling and sign-in around it.
**Why first:** the project rule is "the cost alarm exists before anything billable". Everything later depends on that.
**Cost:** $0.

---

## 1. Concepts, in plain English

**AWS account and region.** An account is the billing and security boundary: everything you create lives in one and
the bill goes to it. A region is a physical cluster of data centres (we use `us-east-1`, N. Virginia). Most resources
live in exactly one region.

**IAM (Identity and Access Management).** The rule book for *who* may do *what* to *which things*. Three nouns matter:
- **Action:** one operation, written `service:Operation`, e.g. `s3:GetObject`.
- **Resource:** the thing it applies to, identified by an **ARN** (the unique address of any AWS thing).
- **Effect:** Allow or Deny.
A **statement** is "Effect + Actions + Resources"; a **policy** is a list of statements.

**IAM role.** A set of permissions something can *assume* temporarily, like a visitor badge. People and services
wear roles instead of holding permanent keys.

**Least privilege.** Grant only the exact actions needed on only the exact resources, so a bug or an attacker can do
only that much damage. It is half "short action list" and half "specific resource ARN".

**Why we did not use the root user.** Root can do everything, cannot be restricted, and is for account recovery. We
use an IAM user (`chirayu-admin`, with MFA) and `aws login`, which hands out short-lived credentials from a browser
sign-in, so no long-lived access key sits on disk. (Production answer: IAM Identity Center with per-person roles.)

**Terraform (infrastructure as code).** You describe the infrastructure in text files; Terraform makes AWS match.
Vocabulary:
| Term | Meaning |
|---|---|
| provider | the plug-in that knows one platform (here AWS) |
| resource | one managed thing, e.g. a budget |
| variable / output | an input / a published value |
| module | a reusable bundle of resources, like a function |
| state | Terraform's record of what it built; contains the account ID, so never committed |
| plan | a read-only preview of what would change |
| apply | make it so |
| saved plan (`-out`) | apply runs *exactly* the reviewed plan and nothing recomputed |
| lock file | pins the exact provider version and checksums; committed on purpose |

**AWS Budgets.** Watches spending and e-mails you at thresholds. Analogy: **a smoke alarm, not a sprinkler.** It warns;
it does not stop anything. AWS documents that budget data updates up to three times a day, 8-12 hours apart, so spend
can pass a threshold before the alert arrives.

---

## 2. The code

[`infra/modules/budget/main.tf`](../../infra/modules/budget/main.tf) is one resource, `aws_budgets_budget`:
- `budget_type = "COST"`, `time_unit = "MONTHLY"`, limit `$25`.
- `cost_types { include_credit = false  include_refund = false }`: track **gross** spend, so promotional credits cannot
  hide a runaway bill.
- Notifications: four `ACTUAL` alerts at 20 / 50 / 80 / 100 % of the limit, plus one `FORECASTED` alert at 100 %
  (AWS predicts you will cross the line before you do).

[`infra/bootstrap/main.tf`](../../infra/bootstrap/main.tf) calls that module. It is a **separate root module with its
own state** so that (a) the alarm exists before any billable resource can be created, and (b) `make destroy` of the
main stack leaves the free alarm in place.

The workflow we used: `plan -out=tfplan` (read it) then `apply tfplan`. Then we checked from AWS's side with
`aws budgets describe-budget`, because "Terraform says success" is not the same as "AWS agrees".

---

## 3. Decisions and trade-offs
See the table in [LEARNING_NOTES.md](../../LEARNING_NOTES.md), rows 5, 6, 7, 9 and 10. The headline ones:
- **Separate bootstrap stack** over one big stack: the alarm must come first and outlive the rest.
- **Gross cost tracking** over net: safety over tidiness.
- **A budget is a warning, not a brake.** Hard limits live elsewhere: the agent's own iteration/token/time caps now,
  budget *actions* and Cost Anomaly Detection in production.

---

## 4. Gotchas we hit (each one is a real-world lesson)

1. **An unverified summary was wrong** (the IAM action list for Budgets). The right list came from AWS's own policy
   data. *Verify, then trust.*
2. **A script that "works" can still be wrong.** The first price check returned a plausible but incorrect Haiku price
   because several models share a billing key. The script now refuses ambiguous matches.
3. **The `.example` template is tracked by git.** A real e-mail address was typed into it and caught before commit.
   Real values belong only in the git-ignored copy.
4. **The account already had about $0.10 of spend** before we began. An account-wide budget counts it.
5. **Windows quirks:** PowerShell 5.1 strips double quotes when passing JSON to programs (use `TF_VAR_*` environment
   variables); a new install needs a new terminal for PATH; CRLF line endings break `make` and Linux CI, so
   `.gitattributes` forces LF.
6. **Sessions expire.** `aws login` credentials last hours, not days; re-run it before a plan or apply.

---

## 5. Interview questions, with model answers

**Q1. A customer's finance lead is nervous about a surprise AWS bill. What do you put in place?**
> "First I'd be honest that a budget is a warning, not a cap. So I'd layer controls. For visibility: cost-allocation
> tags, Cost Explorer, and budget alerts on both actual and forecast spend, sent to finance as well as engineering.
> For spikes: Cost Anomaly Detection, because a monthly threshold notices late. For hard limits: budget actions that
> attach a deny policy at 100%, limits on what can be created at all, and caps inside the application. And I'd design
> for pay-per-use so idle cost is near zero, and give finance a cost-per-request number they can forecast with."

*Common wrong answer:* "I'd set a budget limit so spending is capped." (A budget never stops spending.)

**Q2. Why isn't a budget alert enough on its own, and what would you add?**
> "Alerts lag by hours and stop nothing. By the time the email lands the money may be spent. I'd add an anomaly
> detector for sudden spikes, a budget action that automatically restricts permissions at the limit, quotas and
> permission guardrails that prevent expensive resources from being created, and caps in the application itself, like
> maximum tokens and iterations per request."

**Q3. What does `terraform plan` guarantee, and what doesn't it?**
> "A plan is a preview computed from my code, the state file and a refresh of the real resources. If I save it with
> `-out`, apply executes exactly that diff and nothing else. It does not guarantee the apply will succeed: missing
> permissions, quotas, name conflicts and API validation errors often only appear at create time. It doesn't tell me
> the cost. It can't show values that are 'known after apply'. And it can't see anything outside Terraform's state."

---

## 6. Check yourself
- Explain `s3:GetObject` to a non-technical colleague using the keycard analogy.
- Why does the Terraform provider's `default_tags` setting change the IAM permissions you need?
- Name two reasons the budget is in its own stack.
- What is the difference between an ACTUAL and a FORECASTED alert?

Exercise for this phase: **E1** in [exercises.md](exercises.md).
