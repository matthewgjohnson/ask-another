# Plan: Deep Research + Description Improvements

## 1. New tools: start_research, check_research, cancel_research

### Architecture
- **Lifespan task group**: FastMCP lifespan context holds an anyio task group + job store dict
- **Job store**: in-memory dict mapping job_id → {model, query, status, started, ended, result, citations, task}
- **Background tasks**: research work runs in the lifespan task group, survives tool call cancellation
- **Cancellation handling**: `start_research` catches `asyncio.CancelledError`, job continues in background

### start_research(model, query, timeout=300)
- Spawns research job in lifespan task group
- Blocks and polls job status until complete or timeout
- On completion: returns JSON with report + citations
- On timeout: returns message explaining job continues in background
- On interrupt (escape): CancelledError caught, job keeps running
- Provider routing:
  - `gemini/deep-research-*` → `litellm.interactions.create(agent=..., background=True)` + polling
  - All others (OpenRouter models) → `litellm.completion()` with extended timeout

### check_research(job_id=None)
- No args: returns markdown table of all jobs (job_id, model, status, query truncated at 50 chars, started, ended)
- With job_id: returns full results (report + citations) for completed job, or current status

### cancel_research(job_id)
- Cancels the background task for the given job_id
- Updates job status to "cancelled"

## 2. Updated tool descriptions

### feedback (rewrite)
```
Help us improve ask-another by sharing your experience. Call this
whenever you're unsure how to proceed, receive confusing output, or
a tool doesn't behave as expected. We also welcome suggestions — if
a workflow felt more complex than it should be, if you had to guess
at parameter values, or if something could simply work better.

Every piece of feedback helps us make ask-another more useful.
This tool is lightweight and safe to call at any time.
```
- Add annotations: readOnlyHint=True, idempotentHint=True

### completion (update)
```
Call a model for a quick completion. Use this for standard prompts that
return in seconds — use start_research instead for deep research tasks.
Use a favourite shorthand (e.g. 'openai') or an exact model ID verified
via search_models. Do not set temperature unless you have a specific
reason — some models reject non-default values.
```

### search_models (update)
```
Find exact model identifiers. Always call this to verify a model ID
before passing it to completion or start_research — do not guess IDs.
```

### Server instructions (update)
```
Purpose:
  - Ask another LLM for a second opinion.
  - Provide access to other models through litellm.
Howto:
  - For a quick query, use completion with a favourite model (see below).
  - To use another model: search_families → search_models → completion.
  - For deep research tasks, use start_research. If it is interrupted or
    times out, the task continues in the background — use check_research
    to retrieve results later, or cancel_research to stop a running task.
  - Never guess model IDs.
Feedback:
  - We'd love to hear how ask-another is working for you. Call
    feedback to share issues, suggestions, or anything that felt
    harder than it should be.
  - Call feedback before retrying if you receive confusing output
    or a tool call fails — it helps us improve.
```

### Error messages in other tools
- Append "If this seems like a bug, call the feedback tool to report it." to error messages

## 3. Implementation order

1. Add lifespan with task group + job store
2. Add start_research with OpenRouter path (testable now with Perplexity)
3. Add check_research
4. Add cancel_research
5. Add Gemini Interactions API path
6. Update all tool descriptions and server instructions
7. Add tests
