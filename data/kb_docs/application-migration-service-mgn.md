# AWS Transform MGN (formerly Application Migration Service)

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- MGN automates moving physical, virtual and cloud servers to AWS with minimal downtime; cutover windows are typically minutes.
- It continuously replicates the source servers at block level and converts them to launch on AWS, so large numbers of servers can move without compatibility or performance disruption.
- It works across many operating systems, including Windows Server and common Linux distributions.
- Three templates (replication, launch and post-launch) control how servers are replicated and configured; servers can be grouped into applications and applications into waves for bulk operations.
- Rehosting this way is described as a fast first step: replatform or refactor afterwards using AWS services.

Useful when: a rehost (lift-and-shift) strategy for many servers, with a short cutover.

Source: https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html (checked 2026-10-07)
