# Phase 6: communicating the project (README, demo, blog, interview sheet, web page)

**What we built:** a README for strangers, a 2-minute demo script, a blog draft (872 words), a one-page interview sheet, and a Streamlit web page on top of the same client code.
**What we learned:** the same facts have to be told four different ways, and the most valuable sentences in all four are the ones about what does not work.
**Cost:** about $0.05 of model tokens for one live check of the web page; $0.00 an hour idle.

---

## 1. Concepts, in plain English

**Write for one reader at a time.** A README, a demo, a blog post and an interview sheet contain mostly the same facts, but each has a different reader who
is deciding something different. Analogy: **one set of ingredients, four menus.** The README's reader is an engineer deciding whether to trust the repo
(so: how to run it, what it costs, what is broken). The demo's reader is a person with two minutes (so: one story and one honest ending). The blog's reader is a
practitioner who wants a lesson (so: the finding, with the surprise). The interview sheet's reader is you, under pressure (so: numbers and answers you can say aloud).

**Claims need evidence you can re-run.** "383 unit tests" is a claim; `python -m pytest -o addopts="" -v | grep -c PASSED` is the evidence. "93 resources" is a claim;
`terraform -chdir=infra/main state list | grep -vE '(^|\.)data\.' | wc -l` is the evidence (and a first attempt at that filter gave 110, because it
counted module-level data sources; the number was right, the filter was wrong). Before you publish a number, run the command that produces it.

**Measured, estimated, designed.** Every number in the docs is one of three kinds, and a good reader wants to know which. *Measured:* about $0.011 of model tokens per brief.
*Estimated:* about $0.05 all-in per brief, until Cost Explorer confirms it. *Designed:* $0 idle, because nothing in the design bills while unused. Mixing the kinds
is how a portfolio project loses credibility in one interview question.

**Limitations are a feature.** A README that lists what does not work reads as senior. "Instructions hidden in data steered the agent 6 of 6 times" costs you nothing
with an interviewer who works in security, and it saves you from the question you would otherwise be asked.

**Disclose how it was built.** This project was built with an AI coding assistant. Saying so, and saying what you did (constraints, approvals, decisions), is
honest and defensible; claiming you typed every line is neither. The rule that protects you in an interview: only claim what you can explain, and be ready to explain it.

**A demo is a story, not a tour.** Two minutes allows one problem, one run, one proof that the output can be trusted, and one honest ending. The narration budget is about
150 words a minute, so the script is about 300 words. Prepare a fallback (a recorded real answer) because live demos fail.

**A UI is a thin layer.** The web page calls the same `invoke` and the same `run_checks` as the command line. There is one path to the agent, so a fix or a test
covers both. The page adds presentation only.

**A diagram that cannot go stale.** A hand-drawn diagram is wrong the day after it is drawn. `scripts/make_diagram.py` draws the picture from code and reads its numbers (companies, documents, harness limits, model) from the data files and the Terraform, and tests check it: every component is present, no boxes overlap, text fits its box, every arrow starts and ends on a box edge. Those tests cannot see how the picture *looks*, though: the first render had no icons on four cards, because AWS's `_Dark` icon variants are white glyphs for dark backgrounds. Only opening the PNG showed it. Test what a machine can check, then look at the result yourself.

**The dollar-sign trap.** Streamlit (like many Markdown renderers) typesets text between two `$` signs as a maths formula. A brief full of prices ("$1,168 ... $620") turns into
garbled italics unless every `$` is escaped as `\$`. A test pins it.

---

## 2. The alternatives, honestly

| Option | Good | Bad | Chosen? |
|---|---|---|---|
| **Streamlit page run locally** | 90 lines, reuses the client, uses *your* IAM credentials | Not shareable; no login | Yes |
| Gradio | Similar | Same limits; no advantage here | No |
| A hosted site (API Gateway + Lambda + Cognito) | Shareable | Needs real auth and a gate in front, because anyone who can call the harness can override the guardrail (Phase 4). More to build, more to secure, more to bill | No; it is in "what I would do for production" |
| Publish the Streamlit page to a public URL | Easy to demo | **Would expose `InvokeHarness` to the internet or hand out credentials. Don't.** | No |
| Only a README and screenshots | Zero risk | Weaker demo | No |

---

## 3. The code

- [client/app.py](../../client/app.py): the company dropdown is built from `brief.demo_companies()`, which re-reads `data/accounts.json` on every page run (so a new company appears on refresh) and ends with an "Other (type a name)" choice for untested names; `harness_arn()` takes `HARNESS_ARN` or `terraform output` and shows the error in the page instead of exiting;
  `show_run()` handles four outcomes (withheld by the guardrail, cut off or errored, a good brief, nothing); `show_checks()` lists the deterministic checks and opens the panel when one fails.
- [client/brief.py](../../client/brief.py): `company_error()` was split out of `clean_company()`. The command line exits with the message; the page shows it. One rule, two presenters.
- [tests/unit/test_brief_app.py](../../tests/unit/test_brief_app.py): Streamlit's `AppTest` runs the real script in-process with the AWS call stubbed. Cases: opens without calling the agent; shows the brief and checks; escapes dollar signs;
  says so when the guardrail withheld the answer; warns on a cut-off brief; rejects bad names before any AWS call.
- [scripts/make_diagram.py](../../scripts/make_diagram.py): builds `docs/images/architecture.svg` and `.png` with the official AWS Architecture Icons (downloaded once into the git-ignored `.cache/`; only the finished picture is committed). `read_facts()` pulls the numbers from the repo, `layout()` holds every box and arrow as data, `build_svg()` draws them, and headless Chrome takes the PNG. Run it with `make diagram`.
- Housekeeping: the harness role still carried a permission to call Claude Haiku 4.5 for a comparison that was skipped. The default of `comparison_model_ids` is now `[]`, and the apply removed the unused statement (0 to add, 1 to change, 0 to destroy; read back from IAM, re-plan clean, one brief run afterwards still worked). Unused permissions are risk with no benefit.

---

## 4. What happened, in order

1. The comparison was skipped by choice, so it is recorded as "not run: blocked by the Anthropic account form; skipped" everywhere, never as a result.
2. **Web page, test first.** The first test run failed for the wrong reason: the stub fixture tried to attach an attribute to a plain Python list. A red test is only useful if it is red for the right reason, so
   the fixture was fixed and the tests re-run until they failed because the page did not exist.
3. **One live run** of the real page through `AppTest`: 31 seconds, no errors, brief and checks rendered. (The overview says "about a minute"; the one measurement said 31 s, so the demo script says 30 to 60.)
4. **A claims audit while writing.** Each of these was caught by checking the claim against the repo, not by rereading prose:
   - "eight modules" in the README: the folder has seven.
   - "Nova 2 Lite is 3x cheaper": true for input tokens (3.3x), false for output (2x). The tables now give both prices.
   - "the ROI model is 100 lines": the file is 131. The blog now says about 130.
   - A sentence about enabling model access in the console: unverified, removed.
   - The blog's first count was 902 words, over its 900-word limit; trimmed to 872 (834 without headings).
   - The unknown-company example in the demo used a name nobody had tested; it now uses "Acme Rocketry", which the evaluation refused to invent a profile for in 3 of 3 runs.
5. Everything above went through the leak scan (no account ID, no e-mail) before each commit.
6. **More accounts, and a bug.** Four more demo companies were added (one Terraform apply, 4 rows, $0). One of them, Lighthouse Archive Trust, is deliberately a loser: the ROI model returns -11.7% and no breakeven. The first live brief for it was correct, and the client's `roi_numbers_match_tool` check failed on every figure. The check read numbers without their minus signs while the tool's figures were negative. No earlier account had lost, so the check had never seen a negative number. It was fixed test-first from the real brief; a deliberate break showed the new hyphen test really guards the regex. Left open on purpose: a loss written as a plain positive number still passes (exercise E12).
7. **The architecture diagram.** Drawn with the official icons from code. The layout tests passed on the first run and the picture still had four invisible icons (the `_Dark` variants are white glyphs), a label crossing the AWS Cloud border and a cramped caption; all three were found by looking at the PNG. AWS has no dedicated icon for Guardrails, Knowledge Bases or Titan, so the Bedrock icon is used with a plain label rather than inventing artwork.

---

## 5. Decisions and trade-offs
See [LEARNING_NOTES.md](../../LEARNING_NOTES.md) rows 37 to 40. Headlines: the web page runs locally and is never published; one code path for command line and page; disclose AI-assisted authorship in the README and blog; remove the unused Haiku permission.

---

## 6. Interview questions, with model answers

**Q1. Walk me through the project in two minutes.**
> Use the pitch on [../interview-prep.md](../interview-prep.md): problem, three rules (numbers from code, advice from sources, "I don't know" is an answer), the serverless design with the budget first, the evaluation, the one finding you want remembered.

**Q2. What would you tell a customer about this system's limits?**
> "It is a first draft, not an answer. The numbers are only as good as the inputs, and three of the five assumptions are judgement calls we validate together. The model can recommend services from memory instead of from the
> sources, so we check every brief against the sources. And an attacker who can edit the data the agent reads can steer it, so before it touches real customer data we change the tool design and put a gate in front."

**Q3. How much of this did you write yourself?**
> "I directed it with Claude Code as pair programmer. I set the constraints (sandbox, budget ceiling, no apply without a reviewed plan, evidence over assertion), approved each deploy from a saved plan, and chose what to measure and what to skip. The code
> and the documents are in the repo with the decisions and the reasons, and I can walk through any of them." Then walk through one for real. If you cannot, say which parts you are still learning.

**Q4. How would you let a customer's sales team use this?**
> "Not by publishing the local page. I would put an API in front that fixes the model, prompt, tools and guardrail, authenticate with the customer's identity provider, give each user a role limited to their accounts, log every brief, and keep a human reviewing output until the evaluation shows the error rate is acceptable."

**Q5. Present a bad result to a non-technical executive.**
> "Lead with the decision, then the evidence. 'It refused every typed attack, but a hidden instruction steered it six times out of six. We can fix that by design, and we should not connect it to real data until we have.' Numbers, one plain-language cause, one fix, one date."

**Q6. Your checker flagged a brief that was right. What do you do?**
> "Read the brief and the tool result side by side before changing either. Here the brief matched the tool exactly; the checker dropped minus signs and the tool's figures were negative. I reproduced it as a failing test using the real brief, fixed the code, added the neighbouring cases (a Unicode minus, a hyphen in a range, a wrong figure that must still fail), and broke the fix on purpose to prove the tests guard it. Then I wrote down what the fix still cannot catch."

---

## 7. Check yourself
- Which of these numbers are measured, which estimated, which designed: $0.011 per brief, $0.05 per brief, $0 idle, 93 resources, 30 of 30?
- Why must the web page never be published to a public URL while it can call the harness?
- What did the dollar-sign test protect against, and how would you notice without it?
- Name three claims in the first drafts that the repo contradicted, and the command that settles each.
- Why remove the Haiku permission when it was already working and harmless?
- Why did a correct brief fail a check, and why had it never failed before?
- Why does the check accept "a loss of $219,288" and what does that let through?

Exercises for this phase: **P6** (the "why this vector store" paragraph), **E10** (same facts, three audiences), **E11** (audit the README) and **E12** (close the sign-flip gap) in [exercises.md](exercises.md).
