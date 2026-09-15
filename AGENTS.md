# FlightDeck Agent Instructions

Read [.agents/rules/flightdeck_workflow.md](.agents/rules/flightdeck_workflow.md) before making changes.

### Fast Search & Discovery Protocol (Token & Time Efficiency)
1. **Focus on the immediate prompt**: Prioritize the user's latest request directly. Do not re-analyze, re-read, or summarize historical turns unless specifically requested.
2. **Target docs first**: Before reading source files, check [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to identify the exact file and responsible module.
3. **Never read entire files**: Use targeted grep (`grep_search`), symbol searches, or small line slices (`StartLine`/`EndLine`). Do NOT inspect 500+ line files when locating a function.
4. **Commit policy**: Do NOT automatically commit changes. Commit only on explicit user request after all tests pass.
