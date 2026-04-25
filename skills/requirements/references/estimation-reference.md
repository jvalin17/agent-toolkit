# Back-of-Envelope Estimation Reference

> **This is our synthesis, not copied content.** Knowledge compiled from multiple sources, rewritten in our own words.
> Numbers like cloud costs and latency are approximations — check sources for latest.
> Last verified: 2026-04-24

## Sources
- [Back-of-the-Envelope Estimation — ByteByteGo](https://bytebytego.com/courses/system-design-interview/back-of-the-envelope-estimation)
- [Latency Numbers Every Programmer Should Know — Jeff Dean / Colin Scott](https://colin-scott.github.io/personal_website/research/interactive_latency.html)
- [AWS Pricing Calculator](https://calculator.aws/)
- [Back-of-the-Envelope Estimations — GeeksforGeeks](https://www.geeksforgeeks.org/system-design/back-of-the-envelope-estimation-in-system-design/)

---

## Power of 2

| Power | Value | Name |
|-------|-------|------|
| 2^10 | 1 Thousand | 1 KB |
| 2^20 | 1 Million | 1 MB |
| 2^30 | 1 Billion | 1 GB |
| 2^40 | 1 Trillion | 1 TB |
| 2^50 | 1 Quadrillion | 1 PB |

## Latency Numbers Every Developer Should Know

| Operation | Latency |
|-----------|---------|
| L1 cache reference | 0.5 ns |
| L2 cache reference | 7 ns |
| Main memory reference | 100 ns |
| SSD random read | 150 µs |
| HDD disk seek | 10 ms |
| Send packet within same datacenter | 0.5 ms |
| Read 1 MB from SSD | 1 ms |
| Read 1 MB from HDD | 20 ms |
| Send packet CA → Netherlands → CA | 150 ms |

## Availability Targets

| Availability | Downtime/year | Downtime/month |
|-------------|---------------|----------------|
| 99% | 3.65 days | 7.31 hours |
| 99.9% | 8.76 hours | 43.83 min |
| 99.99% | 52.60 min | 4.38 min |
| 99.999% | 5.26 min | 26.3 sec |

## Common Estimation Formulas

### QPS (Queries Per Second)
```
Average QPS = DAU × queries_per_user_per_day / 86,400
Peak QPS = Average QPS × 2  (typical)
Peak QPS = Average QPS × 3  (spiky traffic like events)
```

### Storage
```
Daily storage = new_items_per_day × avg_item_size
Yearly storage = daily × 365
Total = yearly × retention_years × replication_factor
```

### Bandwidth
```
Incoming = write_QPS × avg_request_size
Outgoing = read_QPS × avg_response_size
```

### Server Count
```
Servers needed = peak_QPS / QPS_per_server
Typical web server: 500-1000 QPS
Typical DB server: 1000-5000 read QPS (with cache)
Always minimum 2 for redundancy
```

### Cache Size (80/20 rule)
```
Cache = 20% of daily read data
Cache memory = read_QPS × avg_response_size × 86,400 × 0.20
```

## Typical Sizes

| Data Type | Typical Size |
|-----------|-------------|
| Short text (tweet, comment) | 200-500 bytes |
| Blog post / long text | 5-50 KB |
| User profile (metadata) | 1-5 KB |
| Thumbnail image | 10-50 KB |
| Standard image | 200 KB - 2 MB |
| HD image | 2-10 MB |
| Short video (1 min) | 5-20 MB |
| Long video (1 hour) | 500 MB - 2 GB |
| PDF document | 100 KB - 10 MB |

## Cloud Cost Benchmarks (2025-2026 rough estimates)

| Resource | AWS (approximate) |
|----------|-------------------|
| Small instance (2 CPU, 4GB) | $30-50/month |
| Medium instance (4 CPU, 16GB) | $100-150/month |
| Large instance (8 CPU, 32GB) | $200-300/month |
| RDS PostgreSQL (small) | $30-50/month |
| RDS PostgreSQL (medium) | $100-200/month |
| ElastiCache Redis (small) | $15-30/month |
| S3 storage (per TB) | $23/month |
| CloudFront CDN (per TB transfer) | $85/month |
| Load Balancer (ALB) | $20-30/month + traffic |
| Data transfer (per GB out) | $0.09 |
