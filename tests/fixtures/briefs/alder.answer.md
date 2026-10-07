## 1. Account summary
Alder & Finch Insurance is a property and casualty insurer with 3,500 employees. It runs a mainframe core policy system plus distributed claims applications, managing 410 servers and 120 TB of storage. Annual infrastructure costs are about USD 5.2 M, growing at 6 % per year. Workloads include claims intake, policy administration and actuarial modelling. The company faces challenges with retiring mainframe skills, slower-than-competitor claims turnaround, and limited capacity for actuarial runs.

## 2. Likely pain points
- Mainframe skills are retiring [stated]
- Claims turnaround is slower than competitors [stated]
- Actuarial runs are limited by available capacity [stated]
- **Inferred**: High infrastructure cost as a fraction of revenue, typical for mainframe-heavy estates
- **Inferred**: Need to modernise to retain talent and improve time-to-insurance

## 3. Discovery questions
### Business
1. What is the current annual revenue, and what percentage of it is technology spend?
2. What are the top three business outcomes you expect from modernising your IT estate?

### Technical
3. What is the current utilisation (CPU, memory, I/O) of the mainframe and distributed claims servers?
4. How much of the claims intake workload is batch versus real-time?
5. What database platforms are used in the current environment?

### Security and compliance
6. Which state insurance regulations apply to your claims and policy data?
7. Do you have any existing AWS accounts or security policies that would affect a migration?

### Financial
8. What fraction of the current on-premises bill could be validated as hardware and facilities cost?
9. What is your target timeline for completing the first workload migration?

## 4. Recommended first workload and architecture
Start with the **claims intake** workload because it directly impacts customer experience and competitive positioning. A first architecture could be:
- Rehost the claims intake application using **AWS Transform MGN** for fast, minimal-downtime migration of the existing servers [AWS Transform MGN (formerly Application Migration Service)](https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html)
- Run the migrated claims intake on **Amazon EC2** instances in a **VPC** with appropriate security groups and IAM roles [The AWS shared responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- Use **Amazon RDS** for any relational database components, enabling automated backups and scaling [not named in passages]

## 5. ROI (3-year, preliminary)
**Preliminary estimate based on the stated inputs and the listed assumptions**

| Year | On-premises cost (USD) | AWS cost (USD) | Savings (USD) |
| :--- | ----------------------: | -------------: | ------------: |
| 1 | 5,200,000 | 3,924,616 | 1,275,384 |
| 2 | 5,512,000 | 2,638,993 | 2,873,007 |
| 3 | 5,842,720 | 2,797,333 | 3,045,387 |
| **Total** | **16,554,720** | **9,360,942** | **7,193,778** |

- **ROI**: 76.8 %
- **Breakeven year**: 1

**Assumptions**
- AWS cost per server-year USD 1,168 (4 vCPU / 16 GiB instance, 1-year Reserved Instance, no upfront) [AWS Price List API, AmazonEC2, us-east-1, Linux, shared tenancy, m7i.xlarge]
- Rightsizing factor 0.7 (AWS needs 70 % as many servers as on-premises) [Planning assumption (judgement)]
- AWS cost per TB-year USD 620 (half EBS gp3, half S3 Standard) [AWS Price List API, us-east-1]
- Migration cost per server USD 3,500 (engineer time, tooling, dual-run) [Planning assumption (judgement)]
- Retained cost fraction 0.4 (40 % of on-premises bill remains) [Planning assumption (judgement)]

## 6. Risks and open items
- The mainframe core policy system may need a different strategy (retain, refactor) that is not covered in the current passages
- Rightsizing and retained-cost assumptions are judgement calls and must be validated with utilisation data and a bill split
- Migration cost per server depends on application complexity and may vary widely
- Compliance with state insurance regulations may require additional AWS services or partner expertise
- The current analysis does not include data transfer costs or support fees, which would affect the total AWS bill