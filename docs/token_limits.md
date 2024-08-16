# Token Limits

Every Large Language Model (LLM) has constraints on the number of tokens it can process per request:

- The model's **context window** limits the total tokens of *input and output* it can process.
- Each model has a limit on how many **output tokens** it can produce.

## Error Reporting

Papertlab will report an error if a model indicates it has exceeded a token limit. The error message will include suggested actions to avoid hitting these limits. Here's an example:

```
Model gpt-3.5-turbo has hit a token limit!

Input tokens: 768 of 16385
Output tokens: 4096 of 4096 -- exceeded output limit!
Total tokens: 4864 of 16385

To reduce output tokens:
- Ask for smaller changes in each request.
- Break your code into smaller source files.
- Try using a stronger model like gpt-4o or opus that can return diffs.

For more info: https://papertlab.com/docs/token-limits.html
```

## Input Tokens & Context Window Size

### The Problem
The most common issue is sending too much data to a model, overflowing its context window. This can happen if:
- The input is too large
- The combined input and output are too large

### Solutions
1. Reduce input tokens by removing files from the chat
2. Only add files that Papertlab needs to *edit* for your request
3. Use stronger models like GPT-4o and Opus, which have larger context windows

### Additional Tips
- Break your code into smaller source files

## Output Token Limits

### The Problem
Most models have small output limits, often around 4k tokens. Large changes affecting a lot of code may hit these limits.

### Solutions
1. Request smaller changes in each interaction
2. Break your code into smaller source files
3. Use strong models like gpt-4o, sonnet, or opus that can return diffs

## Other Causes

Token limit errors might also be caused by:
- Non-compliant API proxy servers
- Bugs in the API server hosting a local model

### Troubleshooting
- Try using Papertlab without an API proxy server
- Connect directly with recommended cloud APIs
- For local models, Ollama is known to work well with Papertlab

If you encounter persistent token limit problems, try these steps to resolve the issue.