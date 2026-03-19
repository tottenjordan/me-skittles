# Modularize context with imports

You can break down large `GEMINI.md` files into smaller, more manageable
components by importing content from other files using the `@file.md` syntax.
This feature supports both relative and absolute paths.

**Example `GEMINI.md` with imports:**

```markdown
# Main GEMINI.md file

This is the main content.

@./components/instructions.md

More content here.

@../shared/style-guide.md
```

For more details, see the [Memory Import Processor](/docs/core/memport)
documentation.
