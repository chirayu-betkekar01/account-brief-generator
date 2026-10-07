# AWS migration strategies: the 7 Rs

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- There are seven strategies for moving an application to AWS: retire, retain, rehost, relocate, repurchase, replatform and refactor (re-architect).
- Rehost ("lift and shift") moves an application unchanged. Replatform ("lift, tinker and shift") adds targeted optimisation, such as moving a database to a managed service, switching to Graviton processors, or containerising a virtual machine.
- Relocate moves many servers at once to a cloud version of the same platform, such as VMware, without rewriting applications.
- Repurchase replaces the application with a SaaS or newer product. Retire switches off applications with no remaining value; unused "zombie" applications (average CPU and memory below 5 percent) are typical candidates.
- Retain leaves an application where it is, for example for data-residency rules, unresolved hardware dependencies, or mainframe and mid-range systems that need careful assessment first.
- Refactor is the most complex and costly strategy. For large migrations the guidance is to rehost, replatform or relocate first and modernise after the move.

Useful when: deciding what to do with each application in a customer's portfolio, and explaining why a full rewrite is rarely the first step.

Source: https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html (checked 2026-10-07)
