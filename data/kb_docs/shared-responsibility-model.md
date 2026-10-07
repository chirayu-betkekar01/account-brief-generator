# The AWS shared responsibility model

Plain-English summary of the linked AWS page, written for this demo (paraphrased, not a quotation). Check the source for current detail.

Key points

- AWS is responsible for security of the cloud: the hardware, software, networking and facilities that run AWS services.
- The customer is responsible for security in the cloud: guest operating system patches, installed applications, security group configuration, data (including encryption choices), and IAM permissions.
- Some controls are shared, such as patching (AWS patches the infrastructure, the customer patches the guest OS and applications) and training.
- The split depends on the service chosen. With Amazon EC2 the customer manages more; with abstracted services such as Amazon S3 or DynamoDB, AWS operates more layers and the customer manages data and access.

Useful when: any security or compliance discussion; it sets expectations about who does what.

Source: https://aws.amazon.com/compliance/shared-responsibility-model/ (checked 2026-10-07)
