# My Skills

This repository stores reusable agent skills as Markdown-based skill packages.

## Structure

Current contents:

```text
tutorial/
  SKILL.md
  references/
    tutorial-template.md
    multi-doc-guide.md
```

## Available Skill

### `tutorial`

The `tutorial` skill is used for writing programming tutorials. It supports:

- Single-document tutorials for smaller topics
- Multi-document tutorial planning for larger topics
- Guidance on research, structure, examples, best practices, and common pitfalls

Reference files:

- `tutorial/references/tutorial-template.md`: single-document tutorial template
- `tutorial/references/multi-doc-guide.md`: guide for splitting large tutorials into multiple documents

## Contributing

When adding a new skill:

1. Create a directory for the skill.
2. Add a `SKILL.md` file with name, description, and workflow.
3. Put supporting templates or reference docs under `references/`.
4. Keep examples practical and instructions explicit.

## Git Conventions

Use Conventional Commits when possible. Example:

```text
feat(tutorial): add tutorial writing skill templates
```
