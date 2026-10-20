# Wayfarer Architecture Principles

## Purpose

This document defines the foundational architecture principles for Wayfarer. These principles are intended to guide all platform, workflow, API, infrastructure, and AI-agent implementation decisions.

Wayfarer is a personal Internal Developer Platform (IDP) optimized for:
- Fast environment provisioning
- Repeatable infrastructure delivery
- AI-assisted operations
- Secure-by-default deployment
- Pragmatic single-operator scalability

---

# 1. Platform Philosophy

## 1.1 AI-Native Platform

Wayfarer is designed assuming AI agents are first-class operators of the platform.

Human users and AI agents should both be able to:
- Author specifications
- Generate infrastructure
- Perform environment changes
- Execute operational workflows
- Troubleshoot deployments
- Evolve templates

The platform must expose strongly typed APIs, deterministic workflows, and explicit contracts suitable for autonomous systems.

---

## 1.2 Specification-Driven Everything

All platform behavior should originate from specifications.

Specifications are the system of record for:
- Environment definitions
- Deployment topology
- Networking rules
- Platform capabilities
- Governance constraints
- Resource relationships

Generated artifacts are disposable outputs.

Generated outputs may include:
- OpenTofu
- Bicep
- GitHub Actions
- ACA Jobs
- API contracts
- UI forms
- Documentation

---

## 1.3 Git-Centric Operations

Git is the operational backbone of the platform.

Desired characteristics:
- Declarative change history
- Full auditability
- Pull-request driven workflows
- Rollback capability
- AI-compatible execution flows

Platform changes should be reproducible from Git alone.

---

# 2. Domain-Driven Design Principles

## 2.1 Pragmatic DDD

Wayfarer uses pragmatic Domain-Driven Design.

The platform should:
- Model around business capabilities
- Use bounded contexts where valuable
- Avoid excessive ceremony
- Prefer clarity over purity
- Avoid over-engineering tactical patterns

Tactical DDD patterns are optional tools, not mandatory architecture constraints.

---

## 2.2 Capability-Oriented Boundaries

Bounded contexts should align to platform capabilities rather than technical layers.

Example bounded contexts:
- Environment Management
- Deployment Orchestration
- Template Authoring
- Identity & Access
- Networking
- AI Operations
- Catalog & Templates

Avoid generic layer-driven decomposition.

---

## 2.3 Ubiquitous Language

All platform artifacts should use a consistent ubiquitous language.

Terms must:
- Be unambiguous
- Map cleanly to domain concepts
- Avoid overloaded infrastructure jargon
- Be AI-friendly
- Remain stable over time

The authoritative vocabulary is defined in:
`002-ubiquitous-language.md`

---

# 3. Security Principles

## 3.1 Private-by-Default Networking

Internal platform components should prefer private networking.

Preferred topology:
- Azure Virtual Networks
- Private Endpoints
- Internal ingress
- Network isolation per environment
- Application Gateway or VPN ingress patterns

Public ingress must be explicit.

---

## 3.2 Identity-First Authentication

Authentication and authorization should prioritize:
- Microsoft Entra ID
- Managed identities
- Federated identity
- Workload identity
- Least privilege access

Avoid:
- Shared secrets
- Long-lived credentials
- Embedded credentials
- Easy Auth dependency coupling

---

## 3.3 Zero Trust Assumptions

All components should assume:
- Networks are hostile
- Identities must be verified
- Workflows are replayable
- Actions require authorization
- Agent actions must be auditable

---

# 4. Infrastructure Principles

## 4.1 Immutable Environment Intent

Environment definitions represent desired state.

Runtime drift should:
- Be detectable
- Be reconcilable
- Optionally be AI-remediated
- Be reviewable via Git workflows

---

## 4.2 Infrastructure as Code

All deployable infrastructure must be represented as code.

Primary tooling:
- OpenTofu
- Bicep
- GitHub Actions
- Azure-native APIs

Manual infrastructure configuration should be avoided.

---

## 4.3 Environment Isolation

Environments should be isolated by default.

Isolation may include:
- Dedicated VNets
- Dedicated subnets
- Dedicated resource groups
- Dedicated secrets
- Dedicated identities

Environment isolation strategy should be configurable based on environment classification.

---

# 5. Platform Runtime Principles

## 5.1 Cloud-Native Preference

The platform should prefer:
- Managed services
- Serverless compute
- Event-driven workflows
- Elastic scale
- Operational simplicity

Preferred Azure services include:
- Azure Container Apps
- Azure Container Apps Jobs
- Azure Service Bus
- Cosmos DB Serverless
- Azure API Management
- Azure Container Registry

---

## 5.2 Cost-Conscious Design

Platform decisions should optimize for:
- Low idle cost
- Efficient consolidation
- Minimal always-on compute
- Elastic scaling
- Small operational footprint

Avoid enterprise-scale assumptions that do not provide practical value.

---

## 5.3 Event-Driven Workflows

Long-running orchestration should favor:
- Events
- Queues
- Durable workflows
- Asynchronous execution

Synchronous orchestration should be minimized.

---

# 6. AI Agent Principles

## 6.1 AI as Operator

AI agents are expected to:
- Generate specifications
- Propose architecture
- Update infrastructure
- Diagnose failures
- Execute operational workflows

Platform APIs and workflows must support deterministic AI operation.

---

## 6.2 Human Approval Boundaries

Destructive or high-impact actions should support:
- Human approval gates
- Pull request review
- Policy validation
- Environment classification rules

---

## 6.3 Explainability

AI-generated actions should:
- Be traceable
- Produce structured reasoning
- Emit operational logs
- Support audit workflows

---

# 7. Engineering Principles

## 7.1 Strong Typing

Contracts should prefer:
- Explicit schemas
- Typed APIs
- Structured configuration
- Deterministic serialization

---

## 7.2 Observability by Default

All services should emit:
- Structured logs
- Metrics
- Distributed traces
- Correlation identifiers

---

## 7.3 Developer Experience

The platform should optimize for:
- Fast feedback loops
- Minimal ceremony
- Self-service operations
- AI-assisted workflows
- Readable specifications

---

# 8. Non-Goals

Wayfarer is not intended to:
- Become a generic enterprise platform
- Support every cloud equally
- Replace enterprise governance platforms
- Prioritize multi-tenant SaaS concerns
- Maximize abstraction over clarity

The platform prioritizes practical operator productivity over theoretical platform generalization.
