# Type-System Design Guidance

**Anti-patterns, Failure Modes, and Corrective Patterns**

At a high level, every type-system smell reduces to one root cause:

> **Domain information is being carried in values instead of types.**

The following anti-patterns describe *how* that information is lost, *why* it matters, and *how* to restore it.

---

## 1. Primitive Obsession

**Definition**
Using raw language primitives (`string`, `int`, `float`) to represent semantically rich domain concepts.

**What’s actually wrong**
The compiler sees *representation*, not *meaning*. Two values that share a machine representation but differ semantically become indistinguishable.

**Failure mode**

```text
UserId = int
TemperatureCelsius = int
```

The compiler cannot prevent:

```text
sendEmail(temperature);
```

**Corrective pattern: Value Objects / Opaque Types**

Encode *meaning* into the type:

```text
type UserId
type TemperatureCelsius
type EmailAddress
```

Benefits:

* Compile-time enforcement of domain boundaries
* Localized validation (constructor-level invariants)
* Self-documenting APIs

**Rule of thumb**
If a primitive has *domain rules*, *constraints*, or *identity*, it deserves its own type.

---

## 2. “Stringly Typed” Systems

**Definition**
Control flow, configuration, or business logic depends on raw strings instead of types.

**What’s actually wrong**
The type system has been bypassed in favor of ad-hoc symbolic encoding.

**Failure mode**

```text
if (role == "admin") { ... }
```

This makes correctness dependent on:

* spelling
* casing
* convention
* runtime tests

**Corrective pattern: Closed Sets**

Use the strongest construct your language offers:

* Enums
* Union types
* Sealed classes / ADTs

```text
Role = Admin | Editor | Viewer
```

Benefits:

* Exhaustiveness checking
* Refactor safety
* Compiler-assisted navigation

**Rule of thumb**
If a string controls behavior, it should almost certainly be a type.

---

## 3. Boolean Blindness

**Definition**
Using booleans where meaning is not self-evident at the call site.

**Failure mode**

```text
createUser("jdoe", true, false, true);
```

The call site encodes *intent* only in argument order.

**Corrective patterns**

1. Replace booleans with enums:

```text
EmailVerification = Verified | Unverified
```

2. Or introduce a configuration object:

```text
UserCreationOptions {
  role: Role
  status: AccountStatus
  notifications: NotificationPolicy
}
```

**Rule of thumb**
A function with more than one boolean parameter is almost always underspecified.

---

## 4. Data Clumps

**Definition**
Repeatedly passing the same group of parameters together.

**What’s actually wrong**
Cohesion exists but is not modeled.

**Failure mode**

```text
move(x, y, z)
rotate(x, y, z)
scale(x, y, z)
```

**Corrective pattern: Aggregate Types**

```text
Vector3 { x, y, z }
```

Benefits:

* Reduced parameter noise
* Invariant enforcement (e.g., normalization)
* Clear semantic grouping

**Rule of thumb**
If parameters travel together, they should live together.

---

## 5. The “God Type” (Blob)

**Definition**
A single type that mixes unrelated responsibilities.

**What’s actually wrong**
The type violates *both* cohesion and dependency direction.

**Failure mode**

```text
User {
  passwordHash
  saveToDatabase()
  formatForDisplay()
  isAdmin()
}
```

**Corrective pattern: Responsibility Segmentation**

Split by axis of change:

* Data representation
* Persistence
* Behavior
* Presentation

Example:

* `User`
* `UserRepository`
* `UserAuthPolicy`
* `UserViewModel`

**Rule of thumb**
If a type changes for multiple reasons, it is already broken.

---

## 6. Illegal States Are Representable

**Definition**
The type system permits states that cannot exist in reality.

**Failure mode**

```text
isLoading = true
isError = true
isSuccess = true
```

The state space is larger than the real domain.

**Corrective pattern: Sum Types / Discriminated Unions**

```text
RequestState =
  | Loading
  | Success(data)
  | Error(message)
```

Benefits:

* Impossible states are unrepresentable
* Exhaustive handling is enforced
* Logic becomes declarative instead of defensive

**Rule of thumb**
If you need comments to explain valid combinations, the type is wrong.

---

## 7. Null / Optional Abuse

**Definition**
Using `null` (or equivalent) to encode multiple meanings.

**What’s actually wrong**
Absence, failure, and incompleteness are being conflated.

**Failure modes**

* Not loaded
* Optional by design
* Error occurred
* Value intentionally missing

**Corrective patterns**

* `Option<T>` → “may not exist”
* `Result<T, E>` → “may fail”
* State types → lifecycle modeling

**Rule of thumb**
`null` should mean *only* “this value does not exist”.

---

## 8. Inheritance for Code Reuse

**Definition**
Using inheritance to share implementation instead of modeling a true “is-a” relationship.

**What’s actually wrong**
The subtype contract is being violated.

**Failure mode**

```text
Banana extends Context
```

**Corrective pattern: Composition**

* Extract reusable behavior into components
* Inject dependencies explicitly
* Prefer interfaces + delegation

**Rule of thumb**
If removing the parent class wouldn’t break conceptual meaning, inheritance is wrong.

---

## 9. The Casting Crutch (Downcasting)

**Definition**
Manually overriding the compiler’s understanding of types.

**What’s actually wrong**
You are asserting correctness without proof.

**Failure mode**

```text
animal as Dog
```

**Consequences**

* Runtime failures
* Fragile refactors
* Local correctness depending on distant assumptions

**Corrective patterns**

* Polymorphism (push behavior down)
* Pattern matching with exhaustiveness checks

**Rule of thumb**
If you need to cast, your abstraction boundary is wrong.

---

## 10. The “Any” Trap (Type Erasure)

**Definition**
Using top types (`Any`, `Object`, `interface{}`) inside domain logic.

**What’s actually wrong**
Type information is discarded prematurely.

**Failure mode**

```text
process(input: Any): Any
```

**Consequences**

* No IDE support
* Forced casting downstream
* Runtime type inspection
* Reintroduction of stringly-typed logic

**Corrective patterns**

* Generics to preserve relationships
* Union types for bounded variability
* Boundary typing (decode once, strongly type internally)

**Rule of thumb**
`Any` is acceptable only at system boundaries—and should be eliminated immediately after.

---

## Why These Anti-Patterns Cluster

They reinforce each other:

1. Use `Any` to avoid modeling.
2. Recover meaning with casts.
3. Encode logic with strings and booleans.
4. Add null checks everywhere.
5. End up with defensive, brittle code.

This is not accidental—it is the predictable result of *value-level programming in a type-capable language*.

---

## Core Design Heuristics (Summary)

Use these as review gates:

1. **Types should carry intent, not just data**
2. **If it can’t exist, don’t model it**
3. **Prefer closed worlds over open strings**
4. **Move invariants into constructors**
5. **Model states, not flags**
6. **Boundary chaos, internal order**

A well-designed type system is not “ceremonial”; it is executable documentation and a static verification engine. The closer your types align with reality, the less work your runtime code has to do.
