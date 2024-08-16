# Using Papertlab in Large (Mono) Repositories

Papertlab is compatible with repositories of any size. However, it's not optimized for quick performance and response time in very large repositories. Here are some strategies to improve performance:

## Working with Subdirectories

To focus on specific parts of your codebase:

1. Change into a subdirectory of your repo containing the code you want to work on.
2. Use the `--subtree-only` switch when starting Papertlab.

This approach tells Papertlab to ignore the parts of the repository outside your current directory.

## Using .papertlabignore

You can create a `.papertlabignore` file to exclude irrelevant parts of your repository:

- This file follows `.gitignore` syntax and conventions.
- Place it in your repository's root directory.

This allows you to switch between different ignore configurations based on your current task.

By implementing these strategies, you can optimize Papertlab's performance in large repositories and focus on the most relevant parts of your codebase for each task.