# Infrastructure Requirements Checklist

> **Our synthesis.** Compiled from system design and cloud architecture best practices.
> Last verified: 2026-04-24

## Sources
- [Scale from Zero to Millions — ByteByteGo](https://bytebytego.com/courses/system-design-interview/scale-from-zero-to-millions-of-users)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [System Design Handbook](https://www.systemdesignhandbook.com/guides/system-design/)
- [Infrastructure Checklist — System Design Checklist](https://evelyne24.github.io/system-design-checklist/)

---

## Compute
- [ ] Application server count and spec
- [ ] Background worker count and spec
- [ ] Auto-scaling rules (min/max instances, triggers)
- [ ] Container orchestration needs (Kubernetes, ECS)
- [ ] Serverless candidates (Lambda, Cloud Functions)

## Database
- [ ] Primary database type (relational, document, key-value, graph)
- [ ] Read replicas needed (count)
- [ ] Write throughput requirements
- [ ] Storage capacity (current + projected)
- [ ] Backup strategy (frequency, retention)
- [ ] Multi-region replication

## Caching
- [ ] Cache layer needed (Redis, Memcached)
- [ ] Cache size (memory)
- [ ] Cache invalidation strategy
- [ ] Cache hit rate target
- [ ] Session storage needs

## Load Balancing
- [ ] Load balancer type (L4/L7)
- [ ] SSL termination
- [ ] Health check configuration
- [ ] Sticky sessions needed
- [ ] Geographic load balancing

## Storage
- [ ] Object storage needs (S3, GCS)
- [ ] File storage capacity
- [ ] CDN for static assets
- [ ] Media processing (image resize, video transcode)
- [ ] Backup storage

## Messaging & Queues
- [ ] Message queue needed (RabbitMQ, SQS, Kafka)
- [ ] Event streaming needs
- [ ] Pub/sub requirements
- [ ] Dead letter queue handling
- [ ] Message retention period

## Search
- [ ] Full-text search needed (Elasticsearch, Algolia)
- [ ] Search index size
- [ ] Search latency target
- [ ] Faceted search / filtering

## Networking
- [ ] VPC / private network setup
- [ ] API gateway needs
- [ ] Rate limiting configuration
- [ ] WAF (Web Application Firewall)
- [ ] DDoS protection
- [ ] DNS configuration

## CI/CD & DevOps
- [ ] Deployment strategy (blue-green, canary, rolling)
- [ ] CI pipeline needs
- [ ] Environment count (dev, staging, prod)
- [ ] Infrastructure as Code (Terraform, CloudFormation)
- [ ] Secret management (Vault, AWS Secrets Manager)

## Monitoring & Observability
- [ ] APM tool (Datadog, New Relic, Grafana)
- [ ] Log aggregation (ELK, CloudWatch)
- [ ] Alerting rules
- [ ] Uptime monitoring
- [ ] Cost monitoring
