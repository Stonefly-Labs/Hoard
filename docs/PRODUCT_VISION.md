# Hoard — Product Vision

**Status:** Draft v0.1 · **Date:** 2026-10-19 · **Product name:** Hoard

## Vision statement
**Every dependency, one local destination.** Make package retrieval fast, predictable, and observable across programming ecosystems through an elegant open-source cache that developers can start in minutes and teams can share confidently.

## The future we want
A developer configures NuGet once and notices that subsequent restores are faster. Later, their team deploys the same product to a shared host, points CI builds at it, and gains insight into which dependencies are consuming bandwidth. Neither scenario requires replacing existing tooling or learning how to administer a full-fledged artifact manager.

## Why this matters
Modern applications span multiple ecosystems, yet teams maintain a patchwork of cache techniques and reliance on public registries. A universal pull-through cache reduces redundant work, creates operational visibility, and provides a dependable local copy of previously fetched artifacts when upstream services are temporarily unavailable.

## Product promise
- **Simple:** One instance, straightforward configuration, sensible defaults.
- **Universal:** One platform, multiple native registry protocols.
- **Fast:** Stream misses efficiently and serve hits locally.
- **Dependable:** Verify complete artifacts, handle concurrency, and state clearly when data is stale or absent.
- **Transparent:** Show what's cached, where it came from, why it was fetched, and what it saved.
- **Open:** MIT licensing and independently deployable, without paid feature tiers.

## Experience principles
### Personal developer
A single Docker command or executable launches a server that defaults to loopback, initializes a local SQLite database and storage directory, and displays ready-to-copy NuGet setup. The user gets an attractive dashboard with live activity and cache-hit metrics without having to configure an identity provider.

### Team and CI
An operator deploys the same software with persistent storage, an explicit network listener, and authenticated management access. CI agents use standard package-manager configuration. The dashboard shows ecosystem breakdowns, upstream health, storage, errors, and utilization. A single-node team installation is a first-class deployment, not a compromised demo.

## Positioning
**Category:** Universal self-hosted pull-through package cache.

**We are:** A developer infrastructure utility and cache appliance with exceptional usability.

**We are not:** A general-purpose binary repository, private package publisher, or full supply-chain governance suite.

**Differentiators to pursue:**
1. Minimal setup and dependency footprint.
2. Consistently polished, usable console.
3. Native package-manager compatibility validated by automated real-client tests.
4. Clear and helpful insight into cache behavior and bandwidth savings.
5. A straight path from laptop to team infrastructure.

## Design direction
**Mood:** Technical, precise, modern, fast, and calm; closer to a refined observability console than a legacy repository administrator.

**Frontend:** Latest supported stable Next.js at implementation time (Next.js 16.4 as of document date), App Router, TypeScript, Tailwind CSS v4, shadcn/ui with accessible Radix or Base UI primitives, Lucide icons, TanStack Table, Recharts, and a restrained motion system.

**Visual system:** High-contrast typography, neutral surfaces, one distinct accent color, subtle gradients only where useful, dark/light themes, refined data-dense tables, responsive layouts, excellent empty/loading/error states, keyboard accessibility.

**Primary navigation:** Overview · Packages · Activity · Registries · Storage · Settings.

**Signature moments:** Live cache request stream; rich ecosystem filters; elegant storage utilization visualization; one-click configuration snippet copying; precise hit/miss/upstream timing details.

## Experience goals
- The first-run wizard gets the developer to a real NuGet restore quickly.
- Users can answer "Is my cache working?" at a glance.
- Operators can locate a package, see its provenance/cache status, and evict it intentionally.
- No action that deletes cached content is surprising or irreversible without confirmation.
- Works equally well on laptop screens and a large desktop monitor.

## Long-term ambition
Become the default open-source dependency caching layer for individuals, homelabs, and small-to-medium engineering organizations. Grow adapter support and deployment sophistication without losing the single-container simplicity that made the product worth installing.

## Product guardrails
- Don't turn the product into an artifact publishing platform through incremental feature creep.
- Don't require a cloud account, telemetry service, or external identity provider for personal use.
- Don't trade correctness or security for impressive cache-hit charts.
- Don't sacrifice accessibility or performance for gratuitous animations.
- Don't lock the console to a mandatory Node server when a compiled static dashboard is sufficient.

## North-star outcomes
- More dependency requests resolved from trusted local storage.
- Less bandwidth, latency, and upstream dependency for repeat builds.
- Fewer minutes spent installing, configuring, and operating the cache.
- High confidence in protocol correctness across supported clients.

## Brand and tagline
**Product name:** Hoard.

**Preferred tagline:** **Fetch once. Build forever.**

Alternative taglines:
- **One cache. Every stack.**
- **Dependencies, delivered locally.**
- **Build faster. Fetch less.**
- **Your packages. Closer.**

## Identity status
**Hoard** is the selected product name. The short lowercase spelling `hoard` is a proposed CLI and repository identifier, subject to namespace availability. Before public launch, verify GitHub namespace, domain, and trademark clearance; existing software products also use the word Hoard.
