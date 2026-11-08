# DEC-03 — Session authority

The Product Owner selected the proposed direction on 2026-11-08. Security and Backend review the design before WP-03 implementation.

Use PostgreSQL as the authoritative store for digests of opaque session tokens, expiration and revocation. All replicas resolve session validity against the same authority. Redis may serve shared rate limits and caches.

Process-local sessions make restart and revocation inconsistent across replicas. Redis as the sole session authority adds persistence and failover requirements. PostgreSQL reuses the existing durable store and adds session lookup and cleanup load. WP-03 must verify restart, revocation across replicas, cookie and CSRF rules, and migration compatibility.
