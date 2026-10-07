## 1. Account summary
Harborview Health is a regional healthcare network with 6,800 employees, running a mixed cloud environment. Its current footprint is one primary data centre plus a disaster recovery site, with a large on-premises imaging archive. Workloads include Imaging archive (PACS), Patient scheduling and Analytics warehouse. The organization faces challenges with imaging storage growth, long disaster recovery test times, and slowing analytics queries at month end.

## 2. Likely pain points
- Imaging storage grows faster than the budget (stated)
- Disaster recovery tests take two days (stated)
- Analytics queries slow down at month end (stated)
- **Inferred**: High on-premises infrastructure cost relative to growth
- **Inferred**: Limited agility for scaling analytics workloads

## 3. Discovery questions
### Business
1. How much of the imaging archive is considered active versus cold or archive data?
2. What is your current budget growth target for IT over the next three years?

### Technical
3. What percentage of the 520 servers are virtualized today?
4. How much of the analytics workload could be moved to a managed service without re-architecting?
5. What is the current RTO and RPO for the imaging archive?

### Security and compliance
6. Do you have a current Business Associate Agreement (BAA) with any cloud provider?
7. What are the top three compliance controls you need to enforce for PHI in the cloud?

### Financial
8. What fraction of your current $7.4 M annual infrastructure spend is hardware, facilities, staff, licences and network?
9. Do you have a migration partner in mind, or would you like a quote for migration services?

## 4. Recommended first workload and architecture
The Imaging archive (PACS) is the most compelling first workload because it directly addresses the fastest-growing cost and the longest recovery time. A first architecture could be:
- Store and analyse medical images at petabyte scale using **AWS HealthImaging**, which is HIPAA-eligible and offers DICOMweb-conformant APIs for interoperability with existing applications [AWS HealthImaging for medical image archives](https://docs.aws.amazon.com/healthimaging/latest/devguide/what-is.html)
- Automate lifecycle management with intelligent tiering to reduce storage costs
- Use **Amazon S3** for cold or archive tiers of the imaging data, leveraging its durability and scalability
- Deploy a **disaster recovery** strategy using **AWS Backup** for automated cross-region backups

## 5. ROI (3-year, preliminary)
**Preliminary estimate based on the stated inputs and the listed assumptions**

| Year | On-premises cost (USD) | AWS cost (USD) | Savings (USD) |
|------|------------------------|----------------|---------------|
| 1    | 7,400,000              | 5,763,152      | 1,636,848     |
| 2    | 8,732,000              | 4,652,919      | 4,079,081     |
| 3    | 10,303,760             | 5,490,445      | 4,813,315     |
| **Total** | **26,435,760** | **15,906,516** | **10,529,244** |

- **ROI:** 66.2 %
- **Breakeven year:** 1

**Assumptions**
- AWS cost per server-year: $1,168 (4 vCPU / 16 GiB general-purpose instance, 1-year standard Reserved Instance, no upfront) — judgement call; validate with real utilisation
- Rightsizing factor: 0.7 (AWS needs 30% fewer servers) — judgement call; validate with CPU/memory utilisation data
- AWS cost per TB-year: $620 (blended EBS gp3 and S3 Standard) — does not include requests, retrieval or snapshots
- Migration cost per server: $3,500 (one-off engineer time, tooling, dual-run) — judgement call; validate with a migration partner quote
- Retained cost fraction: 0.4 (40% of on-prem bill remains) — judgement call; validate by splitting the current bill

## 6. Risks and open items
- The rightsizing factor and retained cost fraction are judgement calls; real utilisation and a bill split are needed
- Migration cost depends on application complexity; a partner assessment is recommended
- Disaster recovery strategy may need additional services or testing
- Analytics workload may need data transformation or modelling before moving
- Customer must confirm they can accept AWS as a business associate under HIPAA (BAA already available)