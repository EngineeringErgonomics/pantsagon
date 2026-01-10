# Trust and security

Packs are treated as untrusted content by default.

- hook execution is disabled unless explicitly allowed (or pack is trusted)
- v1 supports only bundled and local packs (no network fetching)

Future:

- trust allowlist (local file)
- signed pack metadata
- registry-based distribution
