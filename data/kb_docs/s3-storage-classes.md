# Amazon S3 storage classes and lifecycle

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- Every S3 object has a storage class. S3 Standard is the default for frequently accessed data with millisecond access.
- S3 Intelligent-Tiering moves objects between access tiers automatically when access patterns are unknown or changing, with no retrieval fees but a small monitoring fee. Objects under 128 KB are not auto-tiered.
- S3 Standard-IA and One Zone-IA suit infrequently accessed data (30-day minimum, retrieval fees). One Zone-IA keeps one copy in one Availability Zone, so use it only for data you can recreate.
- The Glacier classes suit archives: Instant Retrieval (millisecond access, about quarterly), Flexible Retrieval (minutes to hours, restore first), and Deep Archive (rarely accessed, hours to retrieve, 180-day minimum).
- Lifecycle rules can transition objects between classes as they age.

Useful when: large archives such as media libraries or imaging data, where cold data should not sit on the most expensive tier.

Source: https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html (checked 2026-10-07)
