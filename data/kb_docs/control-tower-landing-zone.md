# AWS Control Tower and the landing zone

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- AWS Control Tower sets up and governs a multi-account AWS environment using prescriptive best practices, orchestrating AWS Organizations, AWS Service Catalog and IAM Identity Center.
- The landing zone is the well-architected multi-account container for organizational units, accounts and users; AWS says Control Tower can build one in under an hour.
- Controls (guardrails) provide ongoing governance and are preventive, detective or proactive. They help stop drift from best practice.
- Account Factory standardises how new accounts are created, and a dashboard shows accounts, enabled controls and non-compliant resources.
- It is most useful once an organisation has more than a handful of accounts.

Useful when: preparing the foundation before migrating workloads: accounts, guardrails and logging in place first.

Source: https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html (checked 2026-10-07)
