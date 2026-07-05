# Department Dispatcher Report

**Generated:** 2026-07-05

---

## 23 Departments Defined

| # | Department ID | Display Name | Processes | Max Concurrent |
|---|--------------|--------------|-----------|----------------|
| 1 | `deploy` | Deploy | deploy_production, deploy_staging | 1 |
| 2 | `testing` | Testing | test_suite, performance_test | 3 |
| 3 | `code_quality` | Code Quality | code_review, lint_check | 2 |
| 4 | `database` | Database | db_migration, db_backup | 1 |
| 5 | `security` | Security | security_scan, credential_rotation | 2 |
| 6 | `infrastructure` | Infrastructure | api_health_check, cache_invalidation, queue_drain, recovery_check | 5 |
| 7 | `monitoring` | Monitoring | log_analysis | 2 |
| 8 | `communication` | Communication | notification_dispatch | 3 |
| 9 | `analytics` | Analytics | report_generation | 2 |
| 10 | `integration` | Integration | data_sync, webhook_delivery | 3 |
| 11 | `storage` | Storage | file_processing | 2 |
| 12 | `ray_review` | Ray Review | escalation routing | 10 |
| 13 | `hermes` | Hermes | routing, classification | 10 |
| 14 | `devops` | DevOps | deploy, infrastructure (combined) | 2 |
| 15 | `data_engineering` | Data Engineering | data_sync, report_generation | 2 |
| 16 | `platform` | Platform | infrastructure, monitoring | 3 |
| 17 | `product` | Product | review, approval gates | 5 |
| 18 | `operations` | Operations | monitoring, notification | 3 |
| 19 | `compliance` | Compliance | security, audit | 2 |
| 20 | `sre` | SRE | recovery_check, queue_drain, health_check | 3 |
| 21 | `ml_ops` | MLOps | model_deploy, data_sync | 2 |
| 22 | `content` | Content | file_processing, report_generation | 2 |
| 23 | `support` | Support | notification_dispatch, report_generation | 3 |

## Routing Patterns

- **Primary routing:** Intent classifier matches patterns to departments
- **Fallback:** Unmatched intents go to `ray_review` for manual classification
- **Load balancing:** Departments with `max_concurrent > 1` process in parallel
- **Queuing:** Excess work orders queue in department inbox
- **Escalation:** Failed processes escalate to `ray_review`

## Process Mapping

| Process | Primary Dept | Backup Dept |
|---------|-------------|-------------|
| deploy_production | deploy | devops |
| deploy_staging | deploy | devops |
| security_scan | security | compliance |
| code_review | code_quality | product |
| test_suite | testing | sre |
| lint_check | code_quality | devops |
| db_migration | database | sre |
| db_backup | database | sre |
| api_health_check | infrastructure | sre |
| log_analysis | monitoring | operations |
| performance_test | testing | sre |
| credential_rotation | security | compliance |
| notification_dispatch | communication | support |
| report_generation | analytics | content |
| data_sync | integration | data_engineering |
| cache_invalidation | infrastructure | platform |
| webhook_delivery | integration | platform |
| file_processing | storage | content |
| queue_drain | infrastructure | sre |
| recovery_check | infrastructure | sre |

## Next Actions

1. Create Supabase `departments` table
2. Implement department queue system
3. Add load balancing logic
4. Wire department health to system health checks
5. Build department dashboard in Command Center
