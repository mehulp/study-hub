# Bookmarks Hub × SailPoint System Design Prep — Coverage Map

**Purpose:** Track which topics from `SD_HelloInterview_Bytebytecode.docx` (SailPoint / IdentityIQ prep plan) get real, hands-on coverage through building the bookmarks hub, versus which need dedicated study time because the project genuinely can't teach them at this scale.

**Legend:** ✅ Covered — 🟡 Partial — ⚠️ Gap (study separately) — 📋 Gap, but plannable (could close via a backlog item)

**Working agreement:** from here on, whenever a build decision covers one of these topics, it gets flagged inline in our conversation and in the architecture doc's Decision Log — e.g. *"📚 SailPoint Prep — Topic 7 (CAP/consistency): this is an availability-over-consistency choice."* The goal is that by the time the project is in good shape, you can point to a specific decision as your answer to "tell me about a time you reasoned about X," not just recite the concept.

---

## B. Fundamentals

| # | Topic | Status | Notes |
|---|---|---|---|
| 0 | What is a System Design Interview | N/A | Meta/expectations-setting — a one-time read, not something a project teaches. |
| 1 | Delivery framework | N/A | A process to internalize for the interview itself — practice via mock runs, not via building. |
| 2 | Networking & API design | 🟡 Partial | Real REST contracts across Auth/Items/Board (Step 3), a real Gateway doing JWT validation + routing. Not covered: L4 vs L7 load balancing (no real LB at our scale), polling vs SSE vs WebSocket (touched conceptually in the real-time-sync backlog item, not built). |
| 3 | Data modeling | ✅ Covered | Steps 2 and 4 *are* this — entity extraction from journeys, then schema with deliberate FK-boundary reasoning (Decision #14). |
| 4 | Choosing & indexing databases | 🟡 Partial | Postgres was a deliberate choice, but we haven't explicitly done the SQL-vs-NoSQL trade-off conversation for this project, or discussed indexing beyond the dedup unique constraint on `items`. Worth a short dedicated pass when we build Items service's query patterns. |
| 5 | Caching | ⚠️ Gap → 📋 Plannable | Not built yet. Natural home: cache the Board→Items composition read (Decision #11) with a short TTL — same call path we already reasoned about for fault tolerance, now revisited for performance. |
| 6 | Sharding & Consistent Hashing | ⚠️ Gap | Not reachable at this project's scale — a personal single-user app will never need to shard. Study via the listed resources directly, no forced project tie-in. |
| 7 | CAP theorem & consistency trade-offs | ✅ Covered | Decision #11 (Board falls back to partial data if Items is down) *is* an explicit availability-over-consistency call, already reasoned through, not just named. |
| 8 | Async & messaging (queues) | ⚠️ Gap → 📋 Plannable | Not built yet. Natural home: the deferred real-time sync/alerts backlog item — a queue between the browser extension's push and the Items service would be a genuine, non-forced use of this pattern. |
| 9 | Reliability / fault tolerance / HA | ✅ Covered | Decision #11 again — timeout + graceful fallback is exactly the "judgment-level toolkit" this topic asks for. Circuit breaker named conceptually, not yet formalized in code. |
| 10 | Numbers to know (latency/throughput) | N/A | Pure memorization — not something a small project generates organically. Just learn the numbers directly. |
| 11 | Identity / IAM-specific | ✅ Strongest overlap | This is the deepest area of the whole project, and it's SailPoint's actual domain: real RBAC (Owner/Editor/Viewer), real OAuth2+PKCE (Twitter), OAuth2 client-credentials for service-to-service (Decision #12), our own session/JWT design (Decision #6), Zero Trust reasoning (Concepts Learned). |

## C. Core Components — Technology Deep Dives

| # | Topic | Status | Notes |
|---|---|---|---|
| 12 | Key Technologies overview | N/A | A map of what to reach for — skim directly, not project-derived. |
| 13 | Database: PostgreSQL | ✅ Covered | Actively in use, schema-per-service, FK-boundary discipline. Deliberately light on internals (MVCC/WAL) — which happens to match HelloInterview's own guidance to avoid over-indexing there. |
| 14 | Database: DynamoDB | ⚠️ Gap | Project uses only Postgres — forcing DynamoDB in would be artificial. Study this one directly from the deep dive. |
| 15 | Cache: Redis | ⚠️ Gap → 📋 Plannable | Tied to the Caching gap above — building that caching layer with Redis specifically would close this too. |
| 16 | Message Queue: Kafka | ⚠️ Gap → 📋 Plannable | Tied to the Async/messaging gap above — the real-time-sync backlog item is the natural home, though a lighter queue (Redis Streams, RabbitMQ) may make more sense than Kafka at this scale; worth discussing Kafka conceptually regardless since it's explicitly named in the prep plan. |
| 17 | Load Balancer / API Gateway | 🟡 Partial | Real API Gateway built (routing, JWT validation — Step 3). Load balancing itself isn't reachable at single-instance scale; stays conceptual/study. |
| 18 | Blob Storage & CDN | ⚠️ Gap → 📋 Plannable | Currently we just store favicon *URLs*, not our own blobs. If we ever store our own copies of preview images, that's a genuine, non-forced use of the presigned-URL pattern this topic cares about. |

## D. Practice Problems

Not mapped to this project — these are standalone guided breakdowns on unrelated domains (Ticketmaster, Dropbox, etc.). Tackle directly via HelloInterview, using the plan's own prioritization (Ticketmaster, Dropbox, Ad Click Aggregator, Web Crawler rank highest for transfer to IAM-flavored problems).

---

## Suggested backlog additions (to close real gaps, not forced)

Three natural extensions would meaningfully improve coverage without distorting the project's actual purpose:

1. **Redis cache on the Board→Items composition read** — closes Caching (5) + Redis (15). Directly extends Decision #11's exact call path.
2. **A real queue for the real-time-sync/alerts backlog item** — closes Async/Messaging (8) + Kafka (16). Already an open backlog item; just needs to be built with a real queue instead of staying conceptual.
3. **Store our own favicon/preview images via blob storage** — closes Blob Storage & CDN (18). Small, natural upgrade from "store a URL" to "store and serve our own copy."

Sharding/Consistent Hashing (6) and DynamoDB (14) are the two topics honestly best left to direct study — there's no non-artificial way to need either at this project's scale.
