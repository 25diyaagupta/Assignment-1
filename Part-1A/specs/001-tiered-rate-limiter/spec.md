# Feature Specification: Tiered Token-Bucket Rate Limiter

**Feature Branch**: `main` (spec directory `001-tiered-rate-limiter`; no feature branch created)

**Created**: 2026-11-22

**Status**: Approved

**Input**: User description: "Tiered token-bucket rate limiter (Python library plus a function that
maps results to HTTP 200/429 with Retry-After)."

## User Scenarios & Testing *(mandatory)*

Actors: the **integrator**, a developer who embeds the limiter in a service, and the **client**,
the caller whose requests are being limited, identified by a client key.

Notation used in the acceptance criteria: "t = 2.5" means the injected clock reads 2.5 seconds.
"Free" and "Pro" are example tiers. Unless an AC says otherwise:

- Free has one limit: capacity 5 tokens, refill 1 token per second.
- Pro has one limit: capacity 20 tokens, refill 10 tokens per second.
- Every request costs 1 token.

Each AC is binary: the stated outcome either happens exactly or the AC fails.

### User Story 1 - Limit a client with a token bucket (Priority: P1)

An integrator sets a capacity and a refill rate. Each request from a client either goes through or
is refused. Short bursts are allowed up to the capacity, and over time throughput settles at the
refill rate.

**Why this priority**: This is the core mechanism. Without it nothing else has value.

**Independent Test**: Configure a single tier with one limit, drive requests with a scripted clock,
and compare the allow/deny sequence with the expected one.

**Acceptance Scenarios**:

1. **AC-001**: **Given** a new Free client, **When** it makes 5 requests at t = 0, **Then** all 5
   are allowed.
2. **AC-002**: **Given** a Free client that has made 5 requests at t = 0, **When** it makes a 6th
   request at t = 0, **Then** the request is denied.
3. **AC-003**: **Given** a Free client whose bucket is empty at t = 0, **When** it requests at
   t = 0.999, **Then** it is denied. **When** it requests at t = 1.0 instead, **Then** it is
   allowed.
4. **AC-004**: **Given** a Free client that is idle from t = 0 to t = 1000, **When** it makes 6
   requests at t = 1000, **Then** exactly the first 5 are allowed. Tokens never build up beyond
   the capacity.
5. **AC-005**: **Given** a Free client holding 3 tokens, **When** it makes a request costing 4,
   **Then** the request is denied and no tokens are taken. A following request costing 3 at the
   same time is allowed.
6. **AC-006**: **Given** Free clients A and B, **When** A uses up its bucket at t = 0, **Then** a
   request from B at t = 0 is allowed.
7. **AC-007**: **Given** a Free client whose bucket is empty at t = 10, **When** the clock next
   reads t = 5 (it went backwards), **Then** the request is denied, no error is raised and no
   tokens are added. **When** the clock then reads t = 11, **Then** a request is allowed, because
   refill is measured from t = 10.

---

### User Story 2 - Apply different limits per tier, including layered limits (Priority: P1)

An integrator defines named tiers, such as Free and Pro, and assigns each client to one. A tier
can have more than one limit, for example a short burst limit plus a sustained limit. A request is
allowed only when every limit of the client's tier allows it.

**Why this priority**: The "tiered" part is what makes this feature different from a plain token
bucket.

**Independent Test**: Configure two tiers, one of them layered. Script requests and check
decisions and remaining capacity.

**Acceptance Scenarios**:

1. **AC-008**: **Given** a new Free client and a new Pro client, **When** each makes 21 requests
   at t = 0, **Then** the Free client gets exactly 5 allowed and the Pro client gets exactly 20.
2. **AC-009**: **Given** a tier "Layered" with limit A (capacity 5, refill 5 tokens per second)
   and limit B (capacity 10, refill 1 token per 6 seconds), and a new client on it, **When** it
   makes 6 requests at t = 0, then 6 at t = 1, then 1 at t = 2, **Then** the outcomes are:
   - t = 0: 5 allowed, 1 denied (limit A).
   - t = 1: 5 allowed, 1 denied.
   - t = 2: the request is denied (limit B).
3. **AC-010**: **Given** the denial at t = 2 in AC-009, **When** the limiter is checked, **Then**
   limit A still holds 5 tokens. A request denied by any one limit takes nothing from any limit.
4. **AC-011**: **Given** a configuration that has no tier named "Gold", **When** a client is
   evaluated against "Gold", **Then** an error naming the unknown tier is raised and no decision
   is returned.

---

### User Story 3 - Turn a decision into an HTTP response (Priority: P1)

An integrator passes a limiter decision to the mapping function and gets back the HTTP status
and headers to send: 200 when allowed, or 429 with `Retry-After` when denied.

**Why this priority**: This is half of the stated deliverable. Clients depend on `Retry-After` to
back off correctly.

**Independent Test**: Feed decisions with known waits into the mapping function and compare the
status and headers.

**Acceptance Scenarios**:

1. **AC-012**: **Given** an allowed decision, **When** it is mapped, **Then** the status is 200
   and there is no `Retry-After` header.
2. **AC-013**: **Given** denied decisions whose exact waits are 1, 0.75, 2 and 2.0001 seconds,
   **When** they are mapped, **Then** each status is 429 and the `Retry-After` values are "1",
   "1", "2" and "3". The wait is always rounded up to a whole second.
3. **AC-014**: **Given** a denied decision whose exact wait is 0.001 seconds, **When** it is
   mapped, **Then** `Retry-After` is "1". The value is never below 1.
4. **AC-015**: **Given** the denial at t = 2 in AC-009, where limit B needs 2/3 token at 1/6
   token per second, **When** it is mapped, **Then** `Retry-After` is exactly "4". With layered
   limits, the longest wait among the limits that block the request decides the value.
5. **AC-016**: **Given** a denied Free client with `Retry-After` = N and no other traffic,
   **When** it retries exactly N seconds after the denial, **Then** the request is allowed.
6. **AC-017**: **Given** any 429 response, **When** the `Retry-After` value is inspected,
   **Then** it contains only decimal digits, without sign, decimal point or units.

---

### User Story 4 - Reject invalid configuration early (Priority: P2)

An integrator who sets up a limit, tier or request wrongly gets a clear error straight away.
Values are never quietly corrected.

**Why this priority**: Misconfiguration silently weakens protection, but this story adds no new
capability.

**Independent Test**: Construct each invalid configuration and confirm it is rejected with an
error that names the faulty field.

**Acceptance Scenarios**:

1. **AC-018**: **Given** a limit with capacity 0 or a negative capacity, **When** it is
   configured, **Then** it is rejected.
2. **AC-019**: **Given** a limit with a refill rate of 0 or a negative rate, **When** it is
   configured, **Then** it is rejected.
3. **AC-020**: **Given** a capacity or refill rate that is not a finite number (NaN or
   infinity), **When** it is configured, **Then** it is rejected.
4. **AC-021**: **Given** a tier with no limits, **When** it is configured, **Then** it is
   rejected.
5. **AC-022**: **Given** two tiers with the same name, **When** they are configured together,
   **Then** the configuration is rejected.
6. **AC-023**: **Given** a request cost of 0, a negative cost or a non-whole-number cost, **When**
   it is evaluated, **Then** it is rejected and no tokens are taken.
7. **AC-024**: **Given** a request whose cost is larger than the capacity of a limit in the
   client's tier (for example, cost 6 on Free), **When** it is evaluated, **Then** an error naming
   the cost and the capacity is raised, no decision is returned and no tokens are taken.

---

### User Story 5 - Get the same decisions on every run (Priority: P2)

An integrator or tester replays a recorded sequence of (time, client, tier, cost) inputs and gets
exactly the same decisions every time.

**Why this priority**: The constitution (Principle IV) requires reproducible tests and audits.

**Independent Test**: Run the same scripted sequence twice on fresh limiters and compare the
outputs.

**Acceptance Scenarios**:

1. **AC-025**: **Given** a fixed configuration and a fixed sequence of 1,000 scripted inputs,
   **When** the sequence is run twice on fresh limiters, **Then** both runs give identical
   decisions and identical retry waits.
2. **AC-026**: **Given** any limiter decision, **When** it is produced, **Then** the limiter has
   not read the system clock. Time comes only from the clock the integrator supplied.

### Edge Cases

- **Clock goes backwards**: covered by AC-007. There is no refill and no error.
- **Long idle period**: covered by AC-004. Tokens are capped at the capacity.
- **Cost exactly equal to the tokens available**: allowed, and leaves 0 tokens (AC-005 second
  half).
- **Request cost larger than capacity**: covered by AC-024. An error is raised.
- **Boundary rounding of the wait**: waits of exactly whole seconds must not round up to the next
  second (AC-013, AC-015).
- **Many distinct clients**: each client is independent (AC-006). Idle clients are not evicted
  in this version (see Assumptions).
- **Concurrent requests for the same client**: out of scope. The caller serialises access
  (FR-012).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep a separate token balance for each client and each limit
  (AC-006).
- **FR-002**: A client's bucket MUST start full, at its capacity (AC-001).
- **FR-003**: Balances MUST refill continuously in proportion to elapsed time and MUST never
  exceed the capacity (AC-003, AC-004).
- **FR-004**: A request MUST be allowed only when every limit of the client's tier holds at least
  the request's cost. When it is allowed, the cost MUST be taken from every limit. When it is
  denied, no limit changes (AC-005, AC-009, AC-010).
- **FR-005**: The system MUST support named tiers. Each tier has one or more limits, and each
  limit has a capacity and a refill rate (AC-008, AC-009).
- **FR-006**: A denied decision MUST report the exact time until the request could be allowed.
  With layered limits, this is the longest wait among the limits that block it (AC-015, AC-016).
- **FR-007**: The mapping function MUST return status 200 with no `Retry-After` for allowed
  decisions. For denied decisions it MUST return 429 with `Retry-After` set to the wait rounded
  up to a whole number of seconds, with a minimum of 1 (AC-012 to AC-017).
- **FR-008**: The system MUST take time only from a clock the integrator supplies, and MUST treat
  a clock that goes backwards as zero elapsed time (AC-007, AC-026).
- **FR-009**: The system MUST reject invalid limits, tiers and costs with an error that names the
  faulty field. It MUST NOT clamp or correct values (AC-018 to AC-023).
- **FR-010**: The system MUST raise an error for an unknown tier name (AC-011).
- **FR-011**: The same configuration and the same input sequence MUST give identical decisions
  (AC-025).
- **FR-012**: The limiter is not thread-safe. The integrator MUST serialise access to a limiter
  instance, and the public documentation MUST say so. No concurrency guarantees are tested in v1.
- **FR-013**: A request whose cost exceeds the capacity of any limit in its tier MUST be rejected
  with an error, not denied with a decision (AC-024).

### Key Entities

- **Limit**: one token bucket rule, made of a capacity (maximum tokens) and a refill rate (tokens
  per second).
- **Tier**: a named set of one or more limits that applies to every client assigned to it.
- **Client key**: an opaque identifier chosen by the integrator. Each client key has its own
  balance for each limit of its tier.
- **Bucket state**: a client's current balance for one limit, plus the latest clock reading
  applied to it.
- **Decision**: the outcome of evaluating one request: allowed or denied, plus, when denied, the
  exact wait until it could be allowed.
- **HTTP outcome**: the status code (200 or 429) and the headers (`Retry-After` when 429)
  produced from a decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a scripted run of 10,000 requests across 100 clients, no client ever gets more
  than capacity + rate × T accepted cost in any time window of length T, for every limit. The
  target is 0 violations.
- **SC-002**: Every denial (100 %) tells the client when to retry. In single-client scenarios,
  waiting the advertised time and retrying succeeds every time (100 %).
- **SC-003**: 100 repeated runs of the same scripted scenario give byte-identical decision
  sequences.
- **SC-004**: An integrator can define a new tier and use it to decide a request, then produce
  its HTTP outcome, in no more than 10 lines of integration code.
- **SC-005**: 100,000 decisions spread across 10,000 clients complete in under 1 second on the
  reference machine.
- **SC-006**: Every invalid configuration listed in User Story 4 (100 %) is rejected before any
  decision is made.

## Assumptions

- Client keys and tier assignments are given by the integrator on every evaluation. The limiter
  does not authenticate clients or store a client-to-tier directory.
- Every limiter instance holds its state in memory for a single process. Distributed or shared
  limiting, persistence across restarts and eviction of idle clients are out of scope for v1.
- Request costs are whole numbers ≥ 1, and the default cost is 1.
- Clock readings are in seconds and may include fractions of a second.
- The mapping function produces only the status and headers. Integrating with a specific web
  framework, the response body and the informational `RateLimit-*` headers are out of scope.
- An allowed decision adds no headers. A later version may add remaining-token information.

## Change Notes

- **2026-11-22** (Deepanshi Bansal, with Claude): resolved the three open questions on the
  recommended options. The user said: "ok do which you think is sufficient".
  - Q1 → C: named tiers, each with one or more layered limits (FR-005; AC-008 to AC-011,
    AC-015 kept).
  - Q2 → A: not thread-safe; the caller serialises access (FR-012).
  - Q3 → A: a cost above capacity raises an error (AC-024, new FR-013).

## Addendum: review additions (2026-11-22)

### Added Functional Requirements

- **FR-014**: Capacity and request cost MUST be whole numbers of type int. Refill rates, clock readings and reported waits MUST be exact rationals (int or Fraction). float, bool, strings and None MUST be rejected for any of these fields, with an error naming the field.
- **FR-015**: The limiter MUST offer a read-only inspection function that returns a client's current balance for each limit of its tier at a given clock reading, without changing any balance.
- **FR-016**: Client keys and tier names MUST be non-empty strings.

### Added Acceptance Criteria

- **AC-027**: Given the AC-009 scenario after the denial at t = 2, when balances are inspected at t = 2, then limit A holds exactly 5 and limit B holds exactly 1/3.
- **AC-028**: Given True or False as a capacity, rate or cost, when configured or evaluated, then it is rejected and no tokens are taken.
- **AC-029**: Given a string or None as a capacity, rate or cost, then it is rejected with an error naming the field.
- **AC-030**: Given a capacity of 5/2 or a float such as 2.5, then it is rejected. Given a cost of 2.0 (a float), then it is rejected even though it is a whole value.
- **AC-031**: Given an empty client key, an empty tier name, or a non-string for either, then it is rejected and no tokens are taken.
- **AC-032**: Given time.time, time.monotonic and datetime.now patched to raise an error when called, when the limiter makes decisions with an injected clock, then every decision succeeds and none of the patched functions is called.

### Success criteria notes

- SC-005 is a reported metric and does not gate acceptance.
- SC-001 is checked by a property test over the scripted run.

### Change Notes entry

- **2026-11-22** (Deepanshi Bansal): added FR-014 to FR-016 and AC-027 to AC-032 after reviewing gaps in testability, numeric exactness and input validation. Status set to Approved. Reason: I founf the new rules more effective
