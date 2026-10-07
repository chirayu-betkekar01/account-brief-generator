## 1. Account summary
Northwind Logistics is a logistics and freight company with 4,200 employees, operating two colocated data centres running VMware with nightly batch jobs for route planning. It runs three main workloads: route optimisation batch, warehouse management system, and customer tracking portal. The company is early in its cloud maturity, with a data centre lease renewing in 18 months and a stated need to improve peak-season capacity and deployment speed for new tracking features.

## 2. Likely pain points
- Peak-season capacity has to be bought a year ahead (inferred)
- The data centre lease renews in 18 months
- New tracking features take months to ship
- Nightly batch jobs may create timing constraints (inferred)
- VMware environment may limit agility and scalability (inferred)

## 3. Discovery questions
### Business
1. How much of the current on-premises bill do you think is hardware, facilities, staff, licences and network?
2. What is your expected growth over the next three years in employees, shipments, and data volume?

### Technical
3. What percentage of your VMware estate runs at less than 70 % CPU utilisation?
4. How many of the 340 servers are database servers, and what databases do they run?
5. What is the average age of your servers and their warranty status?

### Security and compliance
6. Do you need any specific certifications beyond SOC 2, such as ISO 27001 or GDPR?
7. How do you currently manage encryption at rest and in transit for the customer tracking portal?

### Financial
8. What would you budget for a migration partner to move the estate, per server?
9. Do you have a target date for moving off the current data centre lease?

## 4. Recommended first workload and architecture
The route optimisation batch workload is a good first candidate because it is already a nightly batch job and can be containerised for AWS. A first architecture could:
- Use AWS Transform MGN (formerly Application Migration Service) to lift and shift the VMware VMs with minimal downtime [AWS Transform MGN (formerly Application Migration Service)](https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html)
- Run the batch jobs on Amazon EC2 with a spot fleet for cost savings during off-peak hours [AWS migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)
- Store results in Amazon S3 with lifecycle policies to move older data to cheaper storage classes [AWS Migration Evaluator: building a data-driven business case](https://aws.amazon.com/migration-evaluator/features/)

## 5. ROI (3-year, preliminary)
**Preliminary estimate based on the stated inputs and the listed assumptions**

| Year | On-premises cost (USD) | AWS cost (USD) | Savings (USD) |
| :--- | ----------------------: | -------------: | -------------: |
| 1 | 3,900,000 | 3,139,584 | 760,416 |
| 2 | 4,368,000 | 2,183,534 | 2,184,466 |
| 3 | 4,892,160 | 2,445,558 | 2,446,602 |
| **Total** | **13,160,160** | **7,768,676** | **5,391,484** |

- **ROI percentage:** 69.4 %
- **Break-even year:** 1

Assumptions:
- AWS cost per server-year: $1,168 (4 vCPU / 16 GiB instance on 1-year Reserved Instance) [AWS Price List API, AmazonEC2, us-east-1, Linux, shared tenancy, m7i.xlarge]
- Rightsizing factor: 0.7 (AWS needs 70 % as many servers as on-premises) (Planning assumption – validate with utilisation data)
- AWS cost per TB-year: $620 (half EBS gp3, half S3 Standard) [AWS Price List API, us-east-1]
- Migration cost per server: $3,500 (one-off engineer time and tooling) (Planning assumption – validate with a partner quote)
- Retained cost fraction: 0.4 (40 % of today’s bill stays: staff, licences, network, support) (Planning assumption – validate by splitting the bill)

## 6. Risks and open items
- The rightsizing factor and retained cost fraction are judgement calls; actual utilisation and bill split must be confirmed.
- Migration costs depend on application complexity; a detailed assessment is needed.
- The current VMware environment may need additional licensing or tooling for AWS.
- SOC 2 compliance will need to be maintained in AWS; the shared responsibility model must be understood.
- The three-year growth rate of 12 % may change with market conditions.