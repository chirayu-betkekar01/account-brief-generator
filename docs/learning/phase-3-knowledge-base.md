# Phase 3: the knowledge base (search by meaning)

**What we built:** 17 short sourced documents, a Bedrock Knowledge Base that indexes them with an S3 Vectors index and
Titan embeddings, and the third tool (`kb_retrieve`) that the agent will call to get best-practice passages with source links.
**Cost:** well under $0.01 for the whole phase; $0.00 an hour idle.

---

## 1. Concepts, in plain English

**Embedding: a text's meaning turned into a list of numbers.** Titan Text Embeddings V2 reads a passage and returns 1,024
numbers. Passages about similar things get similar lists. Analogy: **a library indexed by meaning, not alphabet.** You ask "how do
I keep patient data compliant?" and the librarian walks to the shelf where compliance material sits, even if the word "compliant"
never appears in the book.

**Vector search.** Compare the question's numbers with each passage's numbers and return the closest. We use **cosine similarity**
(how closely two lists point in the same direction). It is *semantic* search: meaning matters, exact words matter less.

**RAG (retrieval-augmented generation).** Before the model answers, fetch relevant passages and hand them over, so the answer is
built from sourced material instead of memory. It is the main defence against invented facts.

**Chunking.** Long documents are cut into pieces so that each piece is about one thing. Ours are about 200 tokens, shorter than
the 512-token chunk size, so each document stays whole. Chunks overlap slightly (10%) so a sentence cut at the boundary is
still found.

**Knowledge Base (Bedrock).** The managed pipeline: read files from S3, chunk, embed, store vectors, answer `Retrieve` calls.
Terraform builds the pieces; an **ingestion job** (started with `make ingest`) does the reading and embedding.

**S3 Vectors.** A vector store built into S3: pay per use, no servers. Analogy: **a very cheap warehouse for the index.** Cost
shape: $0.06 per GB-month stored, $0.20 per GB uploaded, $2.50 per million queries (Price List, 2026-10-05; re-checked in
`scripts/price_check.py`).

**Metadata files.** Next to each document sits `<name>.md.metadata.json` with `title`, `topic`, `source_url`, `checked_on`.
Bedrock returns those attributes with each retrieved passage, which is how the agent can cite a source link.

---

## 2. Why S3 Vectors (the alternatives, honestly)

| Option | Idle cost | Why not (here) |
|---|---|---|
| **S3 Vectors** (chosen) | about $0 | Semantic search only; fine for a small corpus and a demo |
| OpenSearch Serverless | has an hourly minimum even when idle | Would dominate the whole project budget |
| Aurora PostgreSQL + pgvector | hourly instance cost | Same problem; more to operate |
| Bedrock *Managed* Knowledge Base | priced per GB-month and per retrieval | Simplest, and the Gateway has a built-in connector, but costs more and is a different product |

**What would change my mind:** needing keyword or hybrid search, filtering beyond 35 metadata keys, or very low latency at high
query volume. The retrieval experiment below shows a real case for hybrid search.

---

## 3. The code

### The module: [`infra/modules/knowledge_base/main.tf`](../../infra/modules/knowledge_base/main.tf)
1. **Docs bucket** with public access blocked, encryption on, HTTPS-only policy, and `force_destroy` so `make destroy` works.
   The bucket name includes the account ID (bucket names are global); it is computed at deploy time and never written to the repo.
2. **34 files** uploaded under `docs/`: 17 documents and 17 metadata files, with an `etag` so a changed file is re-uploaded.
3. **Vector bucket and index.** The index must match the embedding model: `float32`, 1024 dimensions, `cosine`. AWS also
   requires `AMAZON_BEDROCK_TEXT` and `AMAZON_BEDROCK_METADATA` to be **non-filterable metadata keys** (Bedrock stores each chunk's text
   and its own bookkeeping there; marking them non-filterable keeps them out of the filterable-size limit).
4. **The service role** (the exercise P3 target). Trust: only `bedrock.amazonaws.com`, only for this account, only for a knowledge
   base in this account and Region. The wildcard is on the knowledge-base ID because the role has to exist before the knowledge base.
   Permissions, each with a comment in the code:
   - `s3:ListBucket` on the bucket, and `s3:GetObject` on `docs/*` only, both limited by `aws:ResourceAccount`.
   - `bedrock:InvokeModel` on the one Titan V2 model ARN.
   - Five S3 Vectors actions (`PutVectors`, `GetVectors`, `DeleteVectors`, `QueryVectors`, `GetIndex`) on the one index ARN.
5. **Knowledge base and data source**, with `FIXED_SIZE` chunking (hierarchical chunking can exceed S3 Vectors' metadata limit)
   and a delete policy that removes vectors when the data source goes.

### The tool: [`src/lambdas/kb_retrieve/handler.py`](../../src/lambdas/kb_retrieve/handler.py)
- Validates the query (non-empty, at most 500 characters), clamps `max_results` to 1-8 (default 4), calls `Retrieve` once.
- Returns only `text`, `score`, `title`, `topic`, `source_url`, `checked_on`. **S3 locations and internal chunk IDs are deliberately
  not returned** (a test proves it), so bucket names never reach the model or the user.
- An AWS error becomes a plain "lookup failed, say so rather than guessing" message; the detail goes to the logs only.
- Its role: write its own logs and `bedrock:Retrieve` on this one knowledge base.

### Why not the Gateway's built-in knowledge-base connector?
AWS documents the connector as "supported only for Amazon Bedrock Managed Knowledge Bases", the separate paid product. Ours is a
standard knowledge base on S3 Vectors, so a small Lambda is the right bridge. (Decision recorded; revisit if the project ever moves to
a Managed Knowledge Base.)

### The corpus: [`data/kb_docs/`](../../data/kb_docs/)
Seventeen paraphrased summaries of official AWS pages (migration strategies, Well-Architected, cost, Savings Plans, Migration
Evaluator, MGN, disaster recovery, shared responsibility, HIPAA, PCI DSS, S3 storage classes, mainframe, VMware, auto scaling,
media transcoding, medical imaging, Control Tower). Each says it is a paraphrase, carries its source link and a check date. Tests
enforce official AWS hosts only, the metadata size limit, document length and no personal data.
**One content catch worth remembering:** the Mainframe Modernization page says both of its experiences are no longer open to new
customers. The document says so rather than recommending a service a new customer cannot buy.

---

## 4. Deployment record (2026-10-07)

- `make plan`: **48 to add, 0 to change, 0 to destroy.** After approval, `make apply`: 48 added, first try (no IAM-propagation retry needed).
- `make ingest`: job **COMPLETE**, 17 of 17 documents scanned and indexed, 17 metadata files, 0 failed.
- IAM read back from AWS and compared with the design: trust policy, the four service-role statements and the `kb_retrieve` role all matched exactly.
- **Smoke test: 22/22** after one honest adjustment (see below). Cost: under $0.01.

### The retrieval experiment (a real finding)
Five questions, rank of the expected document among the results:

| Question | Rank | Score |
|---|---|---|
| How should a hospital think about HIPAA when moving patient data to AWS? | 1 | 0.844 |
| What are the options for disaster recovery in the cloud? | 1 | 0.828 |
| Which storage class suits a huge media archive that is rarely read? | 1 | 0.707 |
| Can we migrate our mainframe applications to AWS? | 1 | 0.810 |
| How do we move a large VMware estate without rewriting applications? | **4** | 0.672 |

The first run of the smoke test used a top-3 cutoff and failed on the VMware question. Rephrasing it ("We run lots of VMware virtual
machines on premises. What are our options on AWS?") puts the EVS document at **#1 (0.795)**. The original wording is really a migration-strategy
question, so the 7 Rs and MGN documents rank above it. We did not weaken the test to hide this: we changed it to test what the agent will
actually receive (the default of 4 passages), and recorded why. Two lessons:
1. **Semantic search ranks by intent, not by keyword.** A literal term ("VMware") can lose to a closer-in-meaning document. Hybrid search would help; S3 Vectors does not offer it.
2. **Search always returns something.** An off-topic question ("What is the best pizza topping?") still scored **0.534**, against 0.7 to 0.84 for relevant questions.
   The score is the signal: the agent's instructions and the Phase 5 evaluation must use a relevance threshold (about 0.6 on this corpus) rather than treating any result as an answer.

### What surprised us
1. A script that "worked" in review used ingestion statistic names that do not exist (`numberOfNewDocumentsScanned`). Checking the SDK's own service model
   found the real ones (`numberOfNewDocumentsIndexed`, `numberOfDocumentsScanned`...). **Verify field names against the source of truth, not memory.**
2. A `git add -A` earlier in the same command staged everything, so the first of three planned commits swallowed all three. It was local and unpushed,
   so a soft reset re-split it. Habit: stage by path.
3. The Gateway connector for knowledge bases is for Managed Knowledge Bases only (above).

---

## 5. Decisions and trade-offs
See [LEARNING_NOTES.md](../../LEARNING_NOTES.md) rows 2 and 19 to 23. Headlines: S3 Vectors over OpenSearch; a Lambda instead of the Managed-KB connector;
paraphrased, sourced, dated documents instead of copied text; fixed-size chunking; the service role scoped to one prefix, one model, one index.

---

## 6. Interview questions, with model answers

**Q1. Why S3 Vectors for the knowledge base?**
> "Cost shape and scale. S3 Vectors is pay-per-use with no hourly floor, so an idle knowledge base costs essentially nothing, where OpenSearch
> Serverless has a minimum that would have dominated this project's budget. Our corpus is about 4,000 tokens, so storage is fractions of a cent.
> The trade-off is that it is semantic-only, which I measured: a keyword-heavy question ranked the best document fourth."

**Q2. When would you outgrow it?**
> "When I need hybrid search (keyword plus semantic), richer metadata filtering than 35 keys, or consistently low latency at high query rates.
> I'd also reconsider if retrieval quality, measured as how often the right document is in the top results, plateaus because of missing keyword matching.
> At that point I'd move to OpenSearch or Aurora and keep the same chunking and evaluation set so the comparison is fair."

**Q3. How do you keep RAG answers trustworthy?**
> "Four things. Curate and cite the sources, and date them, so every passage has a link someone can check. Return the relevance score and use a threshold,
> because search always returns something. Make 'not found' an explicit answer that the model must repeat, not paper over. And evaluate: a fixed set of
> questions with expected documents and fabrication traps, run on every change. I'd also add a grounding check after the answer."

**Q4. The model says something your documents don't support. What do you do?**
> "First find out whether retrieval missed (the right passage wasn't returned) or generation drifted (it was returned and ignored). Check the logs for the
> passages given. If retrieval missed, fix the corpus or the query. If generation drifted, tighten the instructions and add a grounding check. Either way, add the case to the evaluation set."

---

## 7. Check yourself
- Why must the vector index dimension match the embedding model, and what would happen if it didn't?
- Why does `kb_retrieve` not return the S3 URI of a passage?
- The off-topic question scored 0.534. Why is that a problem, and where would you handle it?
- What does `data_deletion_policy = "DELETE"` do, and why does it matter for `make destroy`?

Exercises for this phase: **P3** (write the service-role policy) and **E6** (the retrieval detective) in [exercises.md](exercises.md).
