# FAQ

## Does Pantsagon support languages other than Python?

Not in v1. The architecture supports multi-language packs later.

## Do I have to use Docker?

No. Docker is a feature pack.

## Why is layering enforced?

Because directory structure alone does not stop coupling. Enforcement makes the architecture real.

## Does Pantsagon run Pants during generation?

Only if you ask for it (for example, `validate --exec`), to keep init fast and predictable.
