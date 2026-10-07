## 1. Account summary
Summit Ridge Retail is a specialty retailer with 2,900 employees, running a monolithic e-commerce platform on a hosted private cloud. The environment includes 150 servers and 60 TB of storage, with an annual infrastructure cost of $1.8 million. Workloads include an e-commerce storefront, inventory sync, and a loyalty programme. The company faces compliance requirements under PCI DSS and is in the early stages of cloud maturity.

## 2. Likely pain points
- Holiday traffic forces year-round over-provisioning  
- Releases take weeks  
- Inventory data arrives hours late  
- **Inferred**: High operational overhead from managing a monolithic application  
- **Inferred**: Limited agility and scalability for seasonal demand spikes  

## 3. Discovery questions
### Business
1. How much of your current infrastructure spend is tied to peak holiday capacity versus average daily demand?  
2. What is your target time-to-market for new features or promotions during critical sales periods?  

### Technical
3. What percentage of your servers are running at or below 50 % CPU utilisation during non-peak periods?  
4. How much of your inventory data pipeline can be decoupled from the main e-commerce application?  
5. What is your current change-control process for deploying updates to the e-commerce platform?  

### Security and compliance
6. Which AWS services are you currently using, and do any of them handle cardholder data?  
7. Do you have a current PCI DSS assessment, and what gaps does it highlight?  

### Financial
8. What fraction of your current $1.8 million annual infrastructure bill represents hardware refresh, facility costs, and staff time versus software licences and network fees?  
9. What would you consider an acceptable one-time migration spend to achieve a 20 % reduction in annual infrastructure costs?  

## 4. Recommended first workload and architecture
A good first workload to migrate is the **inventory sync service**, because it is a discrete component that can be decoupled from the monolithic platform and offers immediate ROI through faster data availability.  

A minimal viable architecture could include:  
- **AWS Application Migration Service to lift and shift the inventory sync servers with minimal downtime** [AWS Transform MGN (formerly Application Migration Service)](https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html)  
- **Amazon RDS for PostgreSQL to host the inventory database, enabling automated backups and point-in-time recovery** (supported by the general guidance on migration strategies)  
- **AWS Lambda with Amazon EventBridge to trigger sync jobs on demand, reducing always-on compute costs** (implied by the need for flexibility and cost control)  
- **Amazon CloudWatch for monitoring and alarms to ensure data freshness and system health** (standard for any AWS workload)  

## 5. ROI (3-year, preliminary)
**Preliminary estimate based on the stated inputs and the listed assumptions**  

| Year | On-premises cost (USD) | AWS cost (USD) | Savings (USD) |
|------|------------------------|----------------|---------------|
| 1    | 1,800,000              | 1,404,840      | 395,160       |
| 2    | 1,962,000              | 959,026        | 1,002,974     |
| 3    | 2,138,580              | 1,045,338      | 1,093,242     |
| **Total** | **5,900,580**      | **3,409,204**  | **2,491,376** |

- **ROI:** 73.1 %  
- **Breakeven year:** 1  

**Assumptions**  
- AWS cost per server-year: $1,168 (one m7i.xlarge on 1-year Reserved Instance, compute only)  
- Rightsizing factor: 0.7 (AWS needs 70 % as many servers as on-premises)  
- AWS cost per TB-year: $620 (blended EBS gp3 and S3 Standard)  
- Migration cost per server: $3,500 (one-off assessment, move, test and cutover)  
- Retained cost fraction: 0.4 (40 % of current on-premises bill remains after migration)  

## 6. Risks and open items
- The rightsizing factor and retained cost fraction are judgement calls; actual utilisation and bill split must be validated.  
- Migration costs could vary widely depending on application complexity and testing requirements.  
- PCI DSS compliance responsibilities: AWS is compliant, but the customer must manage configuration and data protection.  
- The inventory sync service may have hidden dependencies on the monolithic platform that require refactoring.  
- Holiday traffic patterns may need auto-scaling policies and possibly a different instance family for cost optimisation.