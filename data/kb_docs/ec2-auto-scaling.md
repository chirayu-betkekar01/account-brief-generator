# Amazon EC2 Auto Scaling for variable demand

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- Instances are organised into Auto Scaling groups with a minimum, desired and maximum size; scaling policies add or remove instances as demand changes.
- The service replaces unhealthy instances and balances capacity across Availability Zones.
- A group can mix instance types and purchase options, combining On-Demand with Spot, and with Reserved Instance or Savings Plans discounts.
- Capacity can follow demand, which avoids buying for the peak all year. There is no extra charge for Auto Scaling itself; you pay for the resources it runs.

Useful when: customers with seasonal or spiky traffic, such as peak-season logistics or holiday retail, who over-provision today.

Source: https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html (checked 2026-10-07)
