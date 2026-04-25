# CAP Theorem Reference

> **Our synthesis.** CAP theorem explained in our own words with practical decision guide.
> CAP theorem was formally proven by Seth Gilbert and Nancy Lynch (2002), originally conjectured by Eric Brewer (2000).
> Last verified: 2026-04-24

## Sources
- [Brewer's CAP Theorem — Eric Brewer (2000)](https://en.wikipedia.org/wiki/CAP_theorem)
- [CAP Theorem Revisited — Robert Greiner](https://robertgreiner.com/cap-theorem-revisited/)
- [System Design Primer — CAP Theorem](https://github.com/donnemartin/system-design-primer#cap-theorem)
- [You Can't Sacrifice Partition Tolerance — Coda Hale](https://codahale.com/you-cant-sacrifice-partition-tolerance/)

---

## The Three Properties

You can only guarantee TWO of three in a distributed system:

| Property | What It Means | Example |
|----------|-------------|---------|
| **Consistency** | Every read gets the most recent write | Bank balance always shows latest transaction |
| **Availability** | Every request gets a response (may not be latest) | Search results always return, even if slightly stale |
| **Partition Tolerance** | System works even if network between nodes fails | App works even if one data center loses connection |

## The Real-World Choice

In practice, network partitions WILL happen. So the real choice is:

### CP (Consistency + Partition Tolerance)
- When partition happens: system rejects requests until consistent
- **Use for:** Financial transactions, inventory counts, user auth
- **Databases:** PostgreSQL, MySQL, MongoDB (default), HBase
- **Trade-off:** Some requests fail during network issues

### AP (Availability + Partition Tolerance)
- When partition happens: system serves potentially stale data
- **Use for:** Social feeds, product catalogs, analytics, caching
- **Databases:** Cassandra, DynamoDB, CouchDB, Redis
- **Trade-off:** Users may see slightly old data temporarily

## Decision Guide

| Your Data | Choose | Why |
|-----------|--------|-----|
| Money, payments, inventory | CP | Wrong balance = real damage |
| User authentication | CP | Stale auth = security risk |
| Social media posts/feeds | AP | Seeing a post 2 seconds late is fine |
| Product search results | AP | Slightly stale results are acceptable |
| Real-time chat messages | AP | Availability > perfect ordering |
| Medical records | CP | Stale data = safety risk |
| Analytics/metrics | AP | Eventual consistency is fine |
| Shopping cart | Depends | CP for checkout, AP for browsing |

## For Single-Server / Small Scale
**CAP doesn't apply.** It's only relevant for distributed systems (multiple database nodes). If you have one database server, you get all three by default. Don't over-engineer for CAP until you actually distribute.
