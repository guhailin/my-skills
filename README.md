# My Skills

This repository stores reusable agent skills as Markdown-based skill packages.

## How to Install

Install a skill from this repository with `npx skills add`:

```bash
npx skills add guhailin/my-skills/tutorial
```

After installation, the agent can load the `tutorial` skill when the task matches its description.

## Available Skills

### `tutorial`

Used for writing programming tutorials and technical learning guides.

Main capabilities:

- Plan tutorial research around official docs, use cases, and common pitfalls
- Decide whether the topic should be written as a single document or split into multiple documents
- Provide a complete tutorial structure covering overview, syntax, scenarios, best practices, and pitfalls
- Reuse built-in reference templates for small and large tutorial topics

Reference files:

- `tutorial/SKILL.md`: skill definition and workflow
- `tutorial/references/tutorial-template.md`: single-document tutorial template
- `tutorial/references/multi-doc-guide.md`: multi-document splitting guide
