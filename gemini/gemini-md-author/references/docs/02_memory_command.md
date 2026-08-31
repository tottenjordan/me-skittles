# Manage context with the `/memory` command

You can interact with the loaded context files by using the `/memory` command.

- **`/memory show`**: Displays the full, concatenated content of the current
  hierarchical memory. This lets you inspect the exact instructional context
  being provided to the model.
- **`/memory refresh`**: Forces a re-scan and reload of all `GEMINI.md` files
  from all configured locations.
- **`/memory add <text>`**: Appends your text to your global
  `~/.gemini/GEMINI.md` file. This lets you add persistent memories on the
  fly.
