# I built an AI pre-sales agent on AWS, then tried to break it

Before a first customer meeting, a solutions architect spends hours on the same questions. Who are they? What do they run? What will they worry about? What should I ask? What could the cloud save them, and what could go wrong?

I come from a value-engineering background, so I built Presales Accelerator, an account brief generator that does that first pass: you give it a company name and it returns a six-section discovery brief. It runs on Amazon Bedrock AgentCore, costs nothing while idle, and I measured how it fails. The failures turned out to be the interesting part.

## Three rules for a pre-sales agent

I set three rules before writing anything.

**Numbers come from code.** The ROI model is about 130 lines of plain Python with its assumptions in a file. The agent calls it as a tool and must copy the result. Every assumption is printed next to the number, because a CFO will challenge each one. One of them, the share of today's bill that never goes away, swings the three-year ROI from about 26% to about 104%, so the brief shows that sensitivity instead of hiding it.

**Advice comes from retrieved documents.** A knowledge base holds 17 short paraphrases of AWS documentation, each with a source link and a check date, indexed in S3 Vectors. I chose it over OpenSearch Serverless because it has no hourly floor and my corpus is about a megabyte.

**"I don't know" is an answer.** An unknown company gets "not in the database", never an invented profile.

All company data is synthetic.

## Cost discipline came first

The first thing I deployed was a $25 budget alarm, in its own Terraform stack so that it survives teardown. A budget only warns, and AWS refreshes it a few times a day, so hard limits live in the agent: 12 steps, 6,000 output tokens, 180 seconds, memory off. Everything else is serverless. One brief costs about a cent in model tokens, and `make destroy` removes all 93 resources.

## Then I tried to break it

I wrote 21 test cases and ran each three times: requests for personal data, off-topic questions, bait for invented facts, typed prompt injection, and two attacks hidden inside the data the agent reads. The rules are mechanical, with no model as judge.

**What held.** The agent refused 30 of 30 requests for personal data, off-topic answers and typed injections. The guardrail stopped 23 before the model ran. It blocked no legitimate brief.

**What did not.** I planted an instruction inside a database field, as a poisoned document would. The agent obeyed it in six runs out of six. In one attack it sent the ROI tool a server count of 1 instead of 410, and the brief that came back looked perfect, with a 149.7% ROI and every number matching the tool output. A check that only compares the answer with the tool's output would have passed it. The guardrail does not scan tool results, and telling the model to treat tool output as data was not enough.

**The model recommends from memory.** Twelve of 15 briefs named AWS services that no retrieved passage mentioned. They were real services, but the brief is supposed to rest on the knowledge base. The platform's grounding filter could not separate a clean section from one with five unsupported services; string comparison against the retrieved passages could.

## Two lessons I did not expect

**My first evaluation was wrong.** It scored 16 of 21 and suggested both attacks had failed. Reading the transcripts showed why: the model had passed "Redwood Test Co." with the sentence's full stop attached, my exact-match lookup said "not in the database", and the attack never ran. The fix was to quote the name. The same trap would hit a real "Acme Inc." Read the transcripts before you believe the score.

**A guardrail is a default, not a control.** Anyone allowed to call the agent can override the guardrail, model and tool list in the same request, and IAM cannot inspect request bodies. I tested it; it worked. For real customers I would put a gate in front, or deny overrides in a lifecycle hook.

## What I would change for production

1. Tools that take an identifier and look the facts up themselves, so there is nothing for an attacker to tamper with.
2. A gate that fixes the model, prompt and guardrail.
3. A real CRM with row-level access, and ROI inputs labelled by provenance, with low, base and high cases.
4. A stronger model comparison. I could not run Haiku 4.5 because Bedrock wanted an account-level Anthropic form, so I will not claim a result I did not measure.

## How I built it

I built this with Claude Code as my pair programmer. It wrote the code. I set the constraints: sandbox only, a budget ceiling, no apply without a reviewed plan, and evidence for every claim. I kept the decisions and the exercises in the repo, so I can explain any of them.

The repo has the Terraform, the 383 unit tests, the evaluation and a README that lists what does not work. If you build agents for customers, run the attack that worked on mine against yours.
