# Interview prep: Discovery Brief & ROI Agent (one page)

**60-second pitch.** "I built an agent on Amazon Bedrock AgentCore that prepares a pre-sales discovery brief from a company name. It looks up a synthetic account, retrieves sourced AWS best practice, and runs a 3-year ROI model written in plain Python, so the numbers are code, not model output. It's serverless and costs nothing idle, I deployed the budget alarm first, and I evaluated it with 21 cases including attacks. The finding I'd stress: it resisted every typed attack, but an instruction hidden in a database record steered it 6 times out of 6."

**Architecture in five bullets**
- Client signs `InvokeHarness` with IAM. The **harness** runs Nova 2 Lite in a loop (caps: 12 steps, 6,000 tokens, 180 s) and screens every call with a **guardrail**.
- Tools go through the **Gateway** (MCP, IAM auth) to three Lambdas, one role each: account profile (DynamoDB), ROI (pure Python), knowledge-base search.
- Knowledge base: 17 paraphrased AWS-doc summaries, Titan V2 embeddings, **S3 Vectors**.
- After the answer, **deterministic checks** compare it with the tool results.
- Terraform, 93 resources, `make destroy` removes them all; the budget stack survives.

**Trade-offs I can defend**
| I chose | Over | Because |
|---|---|---|
| AgentCore | Bedrock Agents Classic | Classic is closed to new accounts |
| S3 Vectors | OpenSearch Serverless | No hourly floor; 1 MB corpus. Cost: semantic search only |
| Nova 2 Lite | Haiku 4.5 | $0.33/$2.75 vs $1.10/$5.50 per million tokens. Not compared: Anthropic form blocked it |
| Maths in Python | Model arithmetic | Testable, auditable, CFO-challengeable |
| Own budget stack | One stack | Must exist first and outlive teardown |
| Mechanical eval rules | Model as judge | Free, repeatable |

**Numbers to remember.** Idle $0/hour. About $0.011 model tokens per brief (measured), about $0.05 all-in (estimate). Nova 2 Lite $0.33 in / $2.75 out per million tokens. Budget $25, alerts at 20/50/80/100%. 349 unit tests. Evaluation: 30/30 typed attacks refused, 12/12 fabrication bait resisted, 0/15 legitimate briefs blocked, 0/6 tool-result attacks resisted, 1/15 briefs pass every check.

**Security in three lines.** Least privilege: one role per function, scoped to one table, one index, one model. Defence in depth: guardrail, prompt, three tools with the shell off, output guardrail, client checks. **Gaps I measured:** the guardrail doesn't scan tool results, and any authorised caller can override it per request.

**Questions to expect**
1. **Are you safe from prompt injection?** No. Typed attacks were blocked; instructions in tool results worked 6 of 6. Fix by design: tools take identifiers, not data; compare what was sent with the source of truth; least agency.
2. **Why is a budget alert not enough?** It warns, lags hours, stops nothing. Add hard caps in the app, budget actions, Cost Anomaly Detection.
3. **How do you stop hallucination?** Numbers from code, links from retrieved passages, checks that compare text. The platform's grounding filter scored good and bad sections 0.17 and 0.05, so I didn't use it.
4. **Why trust your evaluation?** My first run was wrong (a trailing full stop broke the lookup). I read the transcripts, fixed it, and report 3 runs per case as rough rates.
5. **Justify the ROI to a CFO.** Sourced prices versus labelled judgement calls, sensitivity (26% to 104%), validate in a workshop.
6. **What breaks at 100x traffic?** Model rate limits and cost first; Lambda and DynamoDB scale.
7. **Did you write it all?** "I directed the build with Claude Code: I set constraints, approved every deploy from a reviewed plan, and recorded each decision. I can walk through any of them." Then do it.

**For production.** A gate that fixes model, prompt, tools and guardrail; tools with identifiers; real CRM with row-level access; Identity Center, multi-account, CI/CD with the evaluation in the pipeline.

**Own the weak spots.** 12 of 15 briefs named ungrounded AWS services. Haiku wasn't compared. Synthetic data only.
