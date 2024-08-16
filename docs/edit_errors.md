# File Editing Problems

## Understanding the Issue

Sometimes, the Large Language Model (LLM) may suggest code changes that don't get applied to your local files. You might see error messages like:

- "Failed to apply edit to *filename*"
- Other similar error notifications

This typically occurs when the LLM deviates from the system prompts and attempts to make edits in an unexpected format. While Papertlab strives to ensure LLM conformity and handles "almost" correctly formatted edits, occasional issues may arise.

## Troubleshooting Steps

If you encounter file editing problems, try the following solutions:

### 1. Use a Capable Model

- Opt for powerful models like GPT-4o, Claude 3.5 Sonnet, or Claude 3 Opus when possible.
- These models are more adept at following system prompt instructions.
- Note that weaker models, especially local ones, are more prone to editing errors.

### 2. Reduce Distractions

Even with large context windows, irrelevant code or conversations can confuse the model:

- **Limit File Selection**: Add only the files you believe need editing to the chat.
- **Remove Unnecessary Files**: Clear files from the chat session that aren't crucial for the current task.
- **Clear Conversation History**: This helps the LLM focus on the task at hand.

Remember, Papertlab sends the LLM a map of your entire Git repository, ensuring other relevant code is included automatically.

### 3. Seek Additional Assistance

If problems persist:

1. Check our GitHub issues for similar problems and solutions.
2. If your issue isn't addressed, please file a new issue on our GitHub repository.

By following these steps, you can minimize file editing problems and ensure a smoother experience with Papertlab.