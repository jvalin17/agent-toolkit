# Scaling Progression Reference

## ByteByteGo's Zero to Millions Stages

Use this as a guide. Only present stages relevant to the user's current and NEXT scale level.

### Stage 1: Single Server (0 - 1K users)
```
User → [Web Server + DB + App — all on one machine]
```
- Everything on one box
- SQLite or PostgreSQL on same server
- Local file storage
- **Cost:** $5-20/month (single VPS or free tier)
- **Bottleneck that triggers Stage 2:** DB and app compete for CPU/RAM

### Stage 2: Separate Web & Data Tiers (1K - 10K users)
```
User → [Web Server] → [Database Server]
```
- Split web and database to separate machines
- Each scales independently
- **Decision:** SQL vs NoSQL (see data-layer-options.md)
- **Cost:** $20-50/month
- **Bottleneck:** Single web server can't handle all traffic

### Stage 3: Load Balancer + Multiple Servers (10K - 100K users)
```
User → [Load Balancer] → [Web Server 1]  → [Database]
                        → [Web Server 2]
```
- Minimum 2 web servers for redundancy
- Load balancer distributes traffic
- Web servers must be stateless (no session on server)
- **Cost:** $50-200/month
- **Bottleneck:** Database becomes the bottleneck (reads)

### Stage 4: Database Replication (100K - 500K users)
```
User → [LB] → [Web Servers] → [DB Primary (writes)]
                              → [DB Replica 1 (reads)]
                              → [DB Replica 2 (reads)]
```
- Primary handles writes, replicas handle reads
- Typical read:write ratio is 10:1
- **Trade-off:** Slight delay in replica consistency (replication lag)
- **Cost:** $200-500/month
- **Bottleneck:** Frequent queries are slow even with replicas

### Stage 5: Caching Layer (500K - 1M users)
```
User → [LB] → [Web Servers] → [Cache (Redis)] → [DB Primary]
                                                 → [DB Replicas]
```
- Cache frequently accessed data (80/20 rule)
- Cache-aside pattern: check cache first, DB on miss
- **Decisions:** What to cache, TTL, invalidation strategy
- **Cost:** $300-800/month
- **Bottleneck:** Static content (images, CSS, JS) is slow for distant users

### Stage 6: CDN (1M+ users, media-heavy)
```
User → [CDN (static)] → [LB] → [Web Servers] → [Cache] → [DB]
```
- Static assets served from CDN (geographically close)
- Reduces load on web servers
- **Cost:** $500-2000/month (depends on bandwidth)
- **Bottleneck:** Long-running tasks block web servers

### Stage 7: Message Queues / Async Processing (1M+ users)
```
User → [LB] → [Web Servers] → [Message Queue] → [Workers]
                              → [Cache] → [DB]
```
- Decouple heavy work (email, image processing, scraping) from web requests
- Workers process queue independently
- **Trade-off:** Eventual consistency for async operations
- **Cost:** $800-3000/month
- **Bottleneck:** Single database can't handle write volume

### Stage 8: Database Sharding (10M+ users)
```
[DB Shard 1 (users A-M)] [DB Shard 2 (users N-Z)]
```
- Split data across multiple database servers
- **Challenges:** Cross-shard queries, resharding, hotspots
- **Only when:** Single DB truly can't handle the load
- **Cost:** $3000-10000+/month

## Local/Cheap Alternatives at Each Stage

| Stage Component | Production | Local/Cheap Alternative |
|----------------|-----------|----------------------|
| Database | PostgreSQL (managed) | SQLite (file) |
| Cache | Redis (managed) | In-memory dict / lru_cache |
| Load balancer | AWS ALB / nginx | Not needed (single server) |
| CDN | CloudFront / Cloudflare | Local static file serving |
| Message queue | RabbitMQ / SQS | Python queue / Celery with SQLite |
| Object storage | S3 | Local filesystem / MinIO |
| Monitoring | Datadog / New Relic | Python logging + Prometheus (free) |
| Search | Elasticsearch | SQLite FTS5 / Whoosh |
| Auth service | Auth0 / Clerk | Self-built JWT + bcrypt |

## Key Rule
**"Don't add a component until you can name the bottleneck it solves."**
— ByteByteGo
