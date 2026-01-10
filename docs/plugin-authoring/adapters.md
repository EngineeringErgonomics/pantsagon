# Adapters

Adapters implement ports. They should:

- raise typed AdapterError on IO/exec failures
- return Result/Diagnostics for expected validation outcomes
