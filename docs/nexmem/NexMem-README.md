# NexMem

A single-source-of-truth memory architecture for agent systems.

## Files
- `NexMem-Spec.md` — core principles and data model
- `NexMem-Architecture.md` — full system architecture
- `NexMem-Roadmap.md` — implementation plan
- `NexMem-OpenClaw-Integration.md` — how it plugs into OpenClaw

## Short version
- LanceDB stores canonical memory
- NexMem Core decides writes
- graph is derived
- MCP/API exposes the system
- OpenClaw is a client, not a second memory brain
