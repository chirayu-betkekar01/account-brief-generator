# Architecture (draft v1, updated as we build)

Renders on GitHub. In VS Code, install the "Markdown Preview Mermaid Support" extension to preview it.

```mermaid
flowchart LR
    user(["You<br/>CLI or Streamlit"])

    subgraph agentcore["Amazon Bedrock AgentCore"]
        harness["Harness<br/>agent loop, system prompt<br/>Nova 2 Lite<br/>caps: iterations, tokens, timeout"]
        gateway["Gateway<br/>MCP, IAM auth"]
    end

    guardrail["Bedrock Guardrail<br/>PII block, denied topics,<br/>grounding filter"]

    subgraph tools["Action Lambdas (one IAM role each)"]
        l1["account_profile"]
        l2["roi_estimator"]
        l3["kb_retrieve"]
    end

    ddb[("DynamoDB<br/>synthetic accounts")]
    cfg["assumptions.json<br/>bundled with the Lambda"]
    kb["Bedrock<br/>Knowledge Base"]
    vec[("S3 Vectors<br/>index")]
    docs[("S3 bucket<br/>excerpts + source links")]
    titan["Titan Text<br/>Embeddings V2"]

    subgraph ops["Observability and cost"]
        cw["CloudWatch<br/>logs, metric filters,<br/>dashboard, alarm"]
        budget["AWS Budget<br/>25 USD, email alerts<br/>LIVE"]
    end

    user -->|"InvokeHarness, SigV4"| harness
    harness -->|"each model call"| guardrail
    harness -->|"tool calls"| gateway
    gateway --> l1
    gateway --> l2
    gateway --> l3
    l1 --> ddb
    l2 --> cfg
    l3 -->|"Retrieve"| kb
    kb --> vec
    docs -->|"ingest"| kb
    kb -->|"embed"| titan
    user -.->|"post-answer grounding check<br/>ApplyGuardrail"| guardrail
    harness -.-> cw
    l1 -.-> cw
    l2 -.-> cw
    l3 -.-> cw
```

## One request, step by step

1. You ask the CLI: "Prepare me for a meeting with Northwind Logistics" (a fictional company).
2. The CLI calls `InvokeHarness`, signed with your AWS credentials. Only IAM principals allowed to invoke this harness get in.
3. The harness runs the agent loop: the model reads the system prompt and decides which tools to call. Every model call passes through the Guardrail (PII and denied topics).
4. Tool calls go to the Gateway, which invokes the right Lambda: the account profile, the knowledge base lookup, the 3-year ROI estimate.
5. The model assembles the structured brief from those results: account summary, pain points, 8-10 discovery questions, first-workload architecture, ROI with assumptions, risks.
6. The client optionally runs a grounding check (`ApplyGuardrail`) comparing the answer with the tool results, and reports pass or fail.

## Identities (who may do what)

| Identity | Allowed to | Phase |
|---|---|---|
| `chirayu-admin` (you, via `aws login`) | Deploy everything. Admin, sandbox only. | done |
| Lambda role: `account_profile` | Read one DynamoDB table; write its own logs | 2 |
| Lambda role: `roi_estimator` | Write its own logs only | 2 |
| Lambda role: `kb_retrieve` | Call `Retrieve` on one knowledge base; write its own logs | 2/3 |
| Knowledge Base service role | Read the docs bucket; call the Titan model; read and write the one S3 Vectors index | 3 |
| Gateway service role | Invoke exactly the three Lambdas | 4 |
| Harness execution role | Invoke the one model profile; apply the one guardrail; invoke the one gateway; write logs and traces | 4 |

Exact action names are verified against AWS docs at build time, not from memory.

## Terraform layout

| Stack or module | Holds | Phase |
|---|---|---|
| `infra/bootstrap` + `modules/budget` | The cost alarm. Own state; survives `make destroy` | 1 (applied) |
| `modules/storage_data` | DynamoDB table with seed data; S3 docs bucket | 2-3 |
| `modules/lambdas` | 3 functions, 3 roles, log groups with retention | 2 |
| `modules/knowledge_base` | S3 Vectors bucket + index, Knowledge Base, data source | 3 |
| `modules/guardrails` | PII, denied topics, grounding filter | 4 |
| `modules/agent` | Gateway, 3 targets, harness, roles | 4 |
| `modules/monitoring` | Metric filters, dashboard, alarm | 4 |

## Known gaps and open items

- **Grounding check is partial.** Guardrails' grounding filter needs a tagged source and query, and does not support conversational use, so it cannot run automatically inside the harness. The client and evaluation script run it after the fact instead.
- **Off-topic blocking is a deny-list.** Guardrails can block listed topics, not allow only one topic. The system prompt and the evaluation cover the rest.
- **Open:** whether the harness stream exposes tool results (needed for the grounding check). To be tested in Phase 4.
