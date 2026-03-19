# Understand the context hierarchy

The CLI uses a hierarchical system to source context. It loads various context
files from several locations, concatenates the contents of all found files, and
sends them to the model with every prompt. The CLI loads files in the following
order:

1.  **Global context file:**
    - **Location:** `~/.gemini/GEMINI.md` (in your user home directory).
    - **Scope:** Provides default instructions for all your projects.

2.  **Project root and ancestor context files:**
    - **Location:** The CLI searches for a `GEMINI.md` file in your current
      working directory and then in each parent directory up to the project
      root (identified by a `.git` folder).
    - **Scope:** Provides context relevant to the entire project.

3.  **Sub-directory context files:**
    - **Location:** The CLI also scans for `GEMINI.md` files in subdirectories
      below your current working directory. It respects rules in `.gitignore`
      and `.geminiignore`.
    - **Scope:** Lets you write highly specific instructions for a particular
      component or module.

The CLI footer displays the number of loaded context files, which gives you a
quick visual cue of the active instructional context.
