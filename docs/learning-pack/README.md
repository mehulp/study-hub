# Study Hub — Learning Pack

A compact, interview-ready version of Study Hub's architecture — read this end to end in
roughly 30–45 minutes to revise the whole system before an interview. For the full detailed
history behind every decision here, see `../study-hub-architecture.md`'s Decision Log.

1. [Project Overview](00-project-overview.md) — what it is, why it exists, the 60-90s answer
2. [System Architecture](01-system-architecture.md) — the components, how they talk, where auth/authz live
3. [Service Boundaries](02-service-boundaries.md) — why these five services, what a monolith would lose
4. [Data Model & ERD](03-data-model-and-erd.md) — entities, soft refs vs. real FKs, denormalization
5. [Client/Server Request Flow](04-client-server-request-flow.md) — sequence diagrams for every real flow
6. [Authentication, Authorization & RBAC](05-authentication-authorization-rbac.md) — the full security model
7. [Deployment & Runtime](06-deployment-and-runtime.md) — Railway + Cloudflare, local vs. production
8. [Key Design Decisions](07-key-design-decisions.md) — the 15 worth defending cold
9. [Interview Project Walkthrough](08-interview-project-walkthrough.md) — 30s / 90s / 5-min / deep-dive
10. [System Design Interview Questions](09-system-design-interview-questions.md) — by category, with answers
11. [One-Page Cheatsheet](10-one-page-cheatsheet.md) — read this one 5 minutes before

**Reading order for a first pass:** top to bottom, 1 → 11. **Reading order the night
before an interview:** just 9 and 11.
