# Module ownership and dependency direction

Owner for each layer during Phase 0: repository maintainer; changes require PR review.

| Layer | Responsibility | Allowed internal dependencies |
| --- | --- | --- |
| domain | Entities and business validation | domain |
| ai | Pure algorithms, including unchanged RRF | ai, domain |
| application | Contracts, ports, use cases | application, domain, ai |
| infrastructure | Port implementations and external drivers | application, domain, ai |
| orchestration (future) | Workflow state, injected use cases | application, domain, ai |
| interfaces (future) | Authentication, input/output adaptation | application, domain |
| bootstrap | Explicit composition | all layers |

Core layers must not import legacy `src`, `ui`, bootstrap, infrastructure,
frameworks, database drivers, provider SDKs or network clients. No side effects at import.
An AST gate checks absolute and relative imports, including imports nested in functions.
Legacy code may forward to the new package; the reverse dependency is forbidden.
No `sys.path` mutation. No placeholder directories for unimplemented features.
