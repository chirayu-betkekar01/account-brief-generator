# Learning guide: Presales Accelerator (Account Brief Generator)

This folder turns the project into a course. The build moves fast; the teaching is kept here so you can
study it later, in conversation with Claude, at your own pace.

## How to use it with Claude

Open a Claude Code session in this repo and say one of:

| You say | What Claude does |
|---|---|
| "Teach me phase 2 from `docs/learning/`." | Walks the phase file: concept primer with analogies, then the code, then quizzes you. |
| "Run exercise E2." | Sets up the exercise from `exercises.md`, lets you attempt it, then reviews it (good / improve / improved version). |
| "Quiz me on phase 1." | Asks the interview questions from that phase file, waits for your answers, gives honest feedback. |
| "Explain this file: `infra/modules/lambda_function/main.tf`." | Line-by-line walkthrough in plain English. |
| "Mock interview: I'm the interviewer, you're the candidate / the other way round." | Role-play using `LEARNING_NOTES.md` and the phase Q&A. |

Claude is told (in its project memory) to teach from these files, so they are written to stand alone.
Ask for **more depth** or **faster** at any point.

## Index

| File | What it teaches | Time |
|---|---|---|
| [../project-overview.md](../project-overview.md) | **Start here.** What we are building, why, the features, the architecture diagrams, safety, cost and limits | 30 min |
| [phase-1-foundations.md](phase-1-foundations.md) | AWS accounts, IAM, Terraform basics, the budget alarm, why a budget is a warning not a brake | 45 min |
| [phase-2-lambdas-and-data.md](phase-2-lambdas-and-data.md) | Lambda, DynamoDB, one IAM role per function, test-first development, the ROI model | 60 min |
| [phase-3-knowledge-base.md](phase-3-knowledge-base.md) | Embeddings, vector search, RAG, S3 Vectors vs alternatives, the knowledge-base IAM role, and a real retrieval experiment | 60 min |
| [phase-4-agent.md](phase-4-agent.md) | Agents vs workflows, AgentCore (harness, gateway), guardrail policies, confused deputy, deterministic checks, and nine things that went wrong with the evidence for each | 75 min |
| [phase-5-evaluation.md](phase-5-evaluation.md) | Evaluating an LLM app: non-determinism, mechanical rules, layers, indirect prompt injection (measured: it worked), why a red test is not a finding until you read it | 60 min |
| [phase-6-docs-and-demo.md](phase-6-docs-and-demo.md) | Writing for four audiences, claims you can re-run (and the audit that caught our own errors), the demo script, disclosing AI-assisted work, the web page | 45 min |
| [exercises.md](exercises.md) | Every hands-on exercise (done and not yet done), with hints, model answers and review rubrics | varies |
| [../../LEARNING_NOTES.md](../../LEARNING_NOTES.md) | Glossary, decision table (what we chose, what else we considered, what would change our mind), interview Q&A log | reference |
| [../costs.md](../costs.md) | Verified prices and the cost model; a good case study in "how do I justify a number" | 20 min |
| [../architecture.md](../architecture.md) | The architecture diagram and request flow | 15 min |

The final write-ups are outside this folder: [../../README.md](../../README.md), [../demo-script.md](../demo-script.md), [../blog-draft.md](../blog-draft.md) and [../interview-prep.md](../interview-prep.md).

## Suggested study order

1. Read `phase-1-foundations.md`, then have Claude quiz you on it (the three interview questions).
2. Do exercise **E1** (the IAM statement). It is short and teaches the single most-asked AWS concept.
3. Read `phase-2-lambdas-and-data.md`, then do **E4** (read the code) and **E2** (the ROI function, test first).
   Read `phase-4-agent.md` section 4 (what went wrong) before **E7** (the layers detective).
4. Do **E3** (defend the assumptions out loud). This is the interview skill that matters most for a value engineer.
5. Revisit the decision table in `LEARNING_NOTES.md` and try to argue *against* each decision.

## The rule that runs through all of it

For every choice in this project you should be able to say four things:
**what** we chose, **what else** we could have chosen, **why** this one here, and **what would change my mind**.
That is the shape of a good architecture answer, and the decision table is built that way.
