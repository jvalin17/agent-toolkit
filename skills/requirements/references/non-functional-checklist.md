# Non-Functional Requirements Checklist

## Performance
- [ ] Response time targets (p50, p95, p99)
- [ ] Throughput (requests per second)
- [ ] Concurrent users expected
- [ ] Page load time targets
- [ ] API response time targets
- [ ] Background job completion time

## Scalability
- [ ] Current user base
- [ ] Expected growth rate (3mo, 6mo, 1yr)
- [ ] Peak vs average load ratio
- [ ] Horizontal scaling needs (add more servers)
- [ ] Vertical scaling needs (bigger servers)
- [ ] Data growth rate

## Availability & Reliability
- [ ] Uptime target (99%, 99.9%, 99.99%)
- [ ] Acceptable downtime window (maintenance)
- [ ] Disaster recovery requirements
- [ ] Data backup frequency
- [ ] Recovery Time Objective (RTO) — how fast to recover
- [ ] Recovery Point Objective (RPO) — max data loss acceptable

## Security
- [ ] Authentication method (password, OAuth, SSO, MFA)
- [ ] Authorization model (RBAC, ABAC)
- [ ] Data encryption (at rest, in transit)
- [ ] Sensitive data identified (PII, financial, health)
- [ ] Compliance requirements (GDPR, HIPAA, PCI-DSS, SOC2)
- [ ] API security (rate limiting, API keys, JWT)
- [ ] Input validation requirements

## Data
- [ ] Consistency model (strong, eventual)
- [ ] Data retention period
- [ ] Data deletion / right-to-be-forgotten
- [ ] Data export capabilities
- [ ] Audit logging requirements
- [ ] Data partitioning strategy needs

## Usability
- [ ] Supported platforms (web, mobile, desktop)
- [ ] Supported browsers / OS versions
- [ ] Accessibility requirements (WCAG level)
- [ ] Internationalization / localization
- [ ] Offline capability

## Observability
- [ ] Logging requirements
- [ ] Monitoring / alerting needs
- [ ] Metrics to track
- [ ] Tracing / debugging needs
- [ ] Error reporting
