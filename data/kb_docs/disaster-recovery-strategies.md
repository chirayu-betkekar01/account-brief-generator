# Disaster recovery strategies on AWS

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- There are four approaches, from cheapest and simplest to most capable: backup and restore, pilot light, warm standby, and multi-site active/active.
- Backup and restore protects against data loss and needs infrastructure as code so the environment can be redeployed quickly. Pilot light keeps data replicated and core infrastructure ready, with application servers switched off until needed.
- Warm standby keeps a scaled-down but fully working copy that can serve traffic at reduced capacity straight away. Multi-site active/active serves traffic from several Regions and is the most complex and costly, with recovery time near zero for most disasters.
- Choose using recovery time objective (how fast you must recover) and recovery point objective (how much data loss is acceptable), and test the strategy regularly.
- AWS Elastic Disaster Recovery uses the pilot-light pattern to replicate servers from on premises or another cloud into AWS.

Useful when: a customer asks how to improve resilience or retire a secondary data centre, and you need to match the cost to the recovery target.

Source: https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html (checked 2026-10-07)
