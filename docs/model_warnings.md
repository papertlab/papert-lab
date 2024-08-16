# Model Warnings

## Unknown Context Window Size and Token Costs

When using Papertlab, you might encounter a warning message like this:

```
Model foobar: Unknown context window size and costs, using sane defaults.
```

### What This Means

This warning appears when you specify a model that Papertlab isn't familiar with. In such cases:

- Papertlab doesn't know the context window size for the model.
- The token costs for the model are unknown to Papertlab.

### Default Behavior

When this occurs, Papertlab will:

1. Assume an unlimited context window for the model.
2. Treat the model usage as free (no cost calculation).

### Impact

In most cases, this warning doesn't significantly affect functionality. Papertlab will continue to operate with these default assumptions.

### Resolving the Warning

To remove this warning and provide Papertlab with accurate information:

1. Refer to our documentation on configuring advanced model settings.
2. Follow the instructions to specify the correct context window size and token costs for your model.

By providing this information, you can ensure Papertlab operates with accurate parameters for your chosen model.