# MariaDB DBA Scripts Documentation

This documentation set follows the Diataxis architecture for [`mariadb-dba-scripts`](../README.md).

```mermaid
flowchart LR
  start["Choose Your Goal"] --> learn["Learn by Doing"]
  start --> act["Solve an Operational Task"]
  start --> check["Look Up Flags & Variables"]
  start --> understand["Understand Mechanics"]
  learn --> tut["Tutorials (01-tutorials)"]
  act --> how["How-To Guides (02-how-to-guides)"]
  check --> ref["Reference (03-reference)"]
  understand --> exp["Explanation (04-explanation)"]
```

## Documentation Quadrants

| Quadrant | Purpose | Entry Point |
| :--- | :--- | :--- |
| Tutorials | Guided sandbox lab without a live database server | [01-tutorials/index.md](01-tutorials/index.md) |
| How-To Guides | Step-by-step operational procedures in ASD-STE100 | [02-how-to-guides/index.md](02-how-to-guides/index.md) |
| Reference | CLI options, environment variables, defaults, exit codes | [03-reference/index.md](03-reference/index.md) |
| Explanation | Design rationale, LSN chaining, copytruncate trade-offs | [04-explanation/index.md](04-explanation/index.md) |
