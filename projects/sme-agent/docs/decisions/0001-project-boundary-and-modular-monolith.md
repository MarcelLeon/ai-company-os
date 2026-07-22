# ADR-0001: Project boundary and modular monolith

**Status**: Accepted
**Date**: 2026-06-18

## Decision

SME Agent is a standalone project managed by AICO. It begins as a modular monolith with ports for metadata storage, knowledge retrieval, tool execution, memory, and LLM providers.

## Why

- Business concepts must not contaminate AICO's generic orchestration core.
- One process keeps early changes reviewable and transactions understandable.
- Ports preserve provider independence without committing to premature distributed services.

## Rejected

- Adding the product to `src/aico`: violates plugin and product boundaries.
- Starting with microservices: introduces deployment and consistency cost before domain behavior is known.
- Starting with a framework-heavy agent graph: makes framework semantics the product architecture.

## Consequences

- Modules may be extracted later only when deployment or scaling evidence justifies it.
- Domain and application tests must not require a database or live LLM.
