# Module ownership and dependency direction

Owner: repository maintainer; changes require scoped PR review.

| Layer | Allowed internal dependencies |
| --- | --- |
| domain | domain |
| ai | ai, domain |
| application | application, domain, ai |
| infrastructure | infrastructure, application, domain, ai, config |
| orchestration | orchestration, application, domain, ai |
| interfaces | interfaces, application, domain |
| bootstrap | all layers |

Pure layers permit stdlib and only these exact deterministic exceptions:
Pydantic in domain documents/assessment/knowledge_graph and AI JSON parsing;
NumPy in AI chunking; NetworkX in AI graph algorithms. Allowlisting a module does
not permit network/driver imports. AST checks include relative and nested imports.
Streamlit components cannot import infrastructure or orchestration; entrypoints
and helper scripts cannot import the removed `src`/`ui` namespaces.

No `sys.path` modification, import-time engine/model construction, private agent
reasoning in UI or placeholder framework folders. Entrypoints load environment
configuration explicitly and application requests carry authenticated scope.
