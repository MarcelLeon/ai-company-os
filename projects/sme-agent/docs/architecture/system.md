# System Architecture

```text
Interfaces (API / IM / future UI)
              |
Application use cases
              |
Metadata | Knowledge | Skills | Tools | Agent Runtime | Memory | Context
              |
Ports: repositories, retrievers, executors, LLMs, audit
              |
Adapters: Postgres, pgvector, model providers, MCP/HTTP tools
```

## Module contracts

- **domains** own vertical templates: expected merchant fields, dimensions,
  metrics, sensitive identifiers, human checks, and extension points.
- **metadata** owns governed terminology, metrics, dimensions, entities, warehouse assets, and relationships.
- **knowledge** owns source ingestion, chunks, retrieval policy, citations, and document permissions.
- **skills** owns versioned reusable instructions and input/output contracts.
- **tools** owns executable capability schemas, risk policy, credentials, and audit.
- **agent runtime** owns bounded plan/act/observe loops, budgets, interruption, and approvals.
- **memory** owns user, conversation, task, and durable business memory lifecycles.
- **context** assembles and compresses context while preserving evidence references.
- **LLM gateway** selects providers and models by policy; no business module imports a provider SDK.

The first slice implements the metadata domain and its repository port. The
commercialization slice now also includes domain templates for live/content
commerce, local services, and performance advertising so merchant data can be
validated against a business-process spine before agent diagnosis.
