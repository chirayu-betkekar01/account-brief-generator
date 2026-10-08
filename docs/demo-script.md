# Two-minute demo script

**Goal:** in two minutes, show that the agent is useful, that every number and claim can be traced, and that you know where it breaks. The honest ending is the point; interviewers remember "and here is what does not hold".

**Narration budget:** about 300 words, which fills two minutes at 150 words a minute, so there is no slack. Rehearse once with a timer. If you run long, trim the 0:20 line, not the ending.

## Before you record (10 minutes, costs about $0.10)

The stack costs $0 idle but `make destroy` removes it, so after a break it has to come back first.

1. `aws login --profile discovery-sandbox`, then `export AWS_PROFILE=discovery-sandbox` (Windows PowerShell: `$env:AWS_PROFILE = "discovery-sandbox"`).
2. If you ran `make destroy`: `make plan`, read it, `make apply`, `make ingest` (a few minutes). Otherwise skip.
3. `make smoke` should print every check as passing. If it does not, fix that before recording.
4. Do one dry run: `make ui`, ask for Northwind Logistics, wait for the brief. A live brief takes about 30 to 60 seconds, so rehearse what you say while it runs.
5. Open these in tabs: the web page, the README diagram, and `docs/evaluation-baseline.md`.
6. **Fallback if AWS misbehaves:** `tests/fixtures/briefs/northwind.answer.md` is a real answer from the live agent. Say that it is a recording.

## The script

| Time | On screen | Say |
|---|---|---|
| 0:00 | README title, then the diagram | "Before a first customer meeting, a solutions architect spends hours on the same questions: who are they, what do they run, what should I ask, what could the cloud save them. This agent, Presales Accelerator, does that first pass, and I built it so that every number and claim can be traced." |
| 0:20 | Point at the diagram: harness, gateway, three Lambdas | "It runs on Amazon Bedrock AgentCore. The model never calculates and never remembers facts: it calls three tools. One looks up a synthetic account, one searches seventeen sourced AWS documents, and one is plain Python that does the ROI maths. Everything is serverless, so it costs nothing while idle." |
| 0:40 | Web page: pick `Northwind Logistics` from the dropdown, click **Prepare brief**. While it runs, show the terminal or spinner. | "I ask for a brief on a fictional company. You can see it calling the profile tool, searching the knowledge base twice, then the ROI tool." |
| 1:00 | The brief appears. Scroll to section 4, then section 5. | "Six sections. Every architecture bullet links to the document it came from. And the ROI is labelled preliminary, with the table and the five assumptions underneath. Three of them are judgement calls, and the brief says to validate them. Moving one of them swings the ROI from about 26 to about 104 percent, which is the real conversation with a customer." |
| 1:30 | Open the **Checks** panel. | "After the answer, code checks the brief against what the tools returned: links, ROI figures, whether the maths tool got the profile's real numbers. Here it [passes everything / flags a service the documents never mention]. That second case is common: in my evaluation, twelve of fifteen briefs named AWS services the sources did not support." |
| 1:50 | `docs/evaluation-baseline.md`, the headline table | "I measured it, including attacks. Thirty of thirty requests for personal data, off-topic answers and typed injections were refused. But instructions hidden inside a database record steered the agent six times out of six. That is my next fix: tools that take an identifier, not data. Cost per brief is about a cent in model tokens, and `make destroy` removes all 93 resources." |
| 2:00 | Stop | |

## Optional beats (only if you have 10 seconds to spare; pick one)

**The honest loss.** Ask the page for `Lighthouse Archive Trust`. It is a storage-heavy archive that is cheap to run on premises, so the ROI tool returns about -11.7% with no breakeven, and the brief reports that plainly (live run, 2026-10-07: the brief was correct; an earlier version of the ROI-figure check wrongly flagged its negative figures, which is fixed). "The numbers come from code, and code is allowed to say no."

**The unknown company.**
Choose **Other** in the dropdown and type `Acme Rocketry` (tested in the evaluation: refused to invent a profile in 3 of 3 runs). It is not in the database; the agent should say so instead of inventing a profile. "An unknown company gets 'not in the database', never a made-up one."

## What to say if you are asked

- **"Is it using real customer data?"** No. Nine fictional companies, by design.
- **"Where does the ROI input come from in real life?"** An SE rarely has accurate numbers before the first meeting. This starts outside-in and its job is to choose which question to ask first; the next version would carry a provenance label on each input and return low, base and high cases.
- **"Did you write all of it?"** The README's last section is honest about that: I directed the build with Claude Code as pair programmer and recorded every decision. Be ready to explain any of them.

## What not to claim

- Do not say the guardrail makes it safe. It stopped every typed attack, but a caller can override it and it does not scan tool results.
- Do not promise the checks will pass on a live run. Models are not deterministic; the baseline pass rate for "every check passes" is 1 of 15.
- Do not quote a total bill until you have read Cost Explorer. The per-brief model cost is measured; the all-in figure is an estimate.
- Do not mention Haiku 4.5 results. That comparison was not run.

## After you finish

`make destroy`, type `yes`, and confirm it lists 93 resources. The budget alarm stays. Check Cost Explorer the next day and fill in the Actual column of [docs/costs.md](costs.md), section 7.
