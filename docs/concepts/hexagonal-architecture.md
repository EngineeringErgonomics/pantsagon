# Hexagonal architecture (generated repos)

Generated repos follow a strict layering model:

- `domain`: pure rules and types (no IO)
- `application`: use-cases (no concrete integrations)
- `adapters`: integrations and IO (SDKs, HTTP, DB, etc.)
- `entrypoints`: wiring (CLI/HTTP/workers)

The critical property is dependency direction:

- domain depends only on itself (+ foundation)
- application depends on domain (+ foundation)
- adapters depend on application/domain (+ allowlisted shared adapters)
- entrypoints depend on adapters/application/domain
