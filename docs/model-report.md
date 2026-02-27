# Model Research Report

Generated: 2026-02-27

## Editorial Overview

The frontier model landscape in late February 2026 is defined by convergence at the top and explosive growth from below. Three models sit within 4 points of each other on the Artificial Analysis Intelligence Index — Gemini 3.1 Pro (57), GPT-5.3 Codex (54), and Claude Opus 4.6 (53) — but each wins on a completely different axis. Google leads the composite benchmarks and abstract reasoning (77.1% ARC-AGI-2). OpenAI leads terminal-native coding (77.3% Terminal-Bench 2.0). Anthropic leads human preference (Arena Elo 1503, 144-point GDPval lead) and software engineering (80.8% SWE-bench). There is no single best model anymore — there is a best model *for your task*.

The biggest shift since late 2025 is the Chinese open-weight wave. GLM-5, Kimi K2.5, Qwen 3.5, and MiniMax M2.5 have collectively demolished the assumption that open-source models trail by a generation. GLM-5 (AA Index 50, MIT license) scores higher than Gemini 3 Pro on the AA Intelligence Index. MiniMax M2.5 matches Claude Opus 4.6 on SWE-bench Verified (80.2% vs 80.8%) at 1/20th the cost. Kimi K2.5's agent swarm technology — 100 parallel sub-agents coordinating 1,500 tool calls — is a genuinely new capability that no Western model offers. These aren't budget alternatives; they're legitimate contenders that happen to be cheap.

Pricing is in freefall. MiniMax offers frontier-adjacent coding at $0.15/$1.20 per million tokens. GLM-4.7 charges $0.10 for both input and output. Gemini 2.5 Flash-Lite runs at 496 tok/s for $0.10/$0.40. Meanwhile GPT-5.2 Pro still costs $21/$168 — a 140x premium over MiniMax on output tokens for a marginal quality edge. The market is splitting into "quality at any cost" (Opus 4.6, GPT-5.2 Pro) and "good enough at almost nothing" (MiniMax, GLM, DeepSeek). The middle is getting squeezed.

Two practical takeaways. First, model routing is now the winning strategy — not model loyalty. The optimal stack in February 2026 uses Claude for complex coding, Gemini for reasoning and multimodal, Codex for terminal-native work, Grok for creative and unconstrained output, and open-weight models for cost-sensitive volume. Second, SWE-bench Verified has effectively plateaued at ~80% across the top 5 models. The next differentiator isn't benchmark scores — it's real-world factors like tool integration quality, context retrieval accuracy at scale, and latency characteristics. Claude's 98% retrieval accuracy across 1M tokens and Kimi's agent swarm coordination matter more than the 0.6% SWE-bench gap between first and fifth place.

The surprise of this cycle: Google. After years of shipping impressive benchmarks that didn't translate to developer preference, Gemini 3.1 Pro has made the jump. It tops the AA Intelligence Index by a 3-point margin, scored 77.1% on ARC-AGI-2 (2.5x improvement over its predecessor), and offers all of this at $2/$12 with a native 1M token context window. It's the best value proposition at the frontier right now, full stop.

## Recommended Favourites

| Model | Tier | Speed | Best For |
|-------|------|-------|----------|
| gemini/gemini-3.1-pro-preview | frontier | 91 tok/s | All-rounder, best price-to-quality at the frontier |
| openai/gpt-5.3-codex | frontier | 99 tok/s | Terminal-native coding, fast agentic execution |
| openrouter/x-ai/grok-4 | frontier | 42 tok/s | Creative writing, unconstrained style, hardest reasoning |
| openrouter/z-ai/glm-5 | frontier | 66 tok/s | Open-weight champion, MIT license, low hallucination |
| openrouter/deepseek/deepseek-r1-0528 | strong | variable | Math/reasoning specialist, transparent chain-of-thought |

**Gemini 3.1 Pro Preview** is the default reach-for model. AA Intelligence Index #1 (57), ARC-AGI-2 champion (77.1%), 94.3% GPQA Diamond, 1M native context, multimodal input (text/image/speech/video) — and it costs $2/$12 per million tokens, roughly 1/3 of Claude Opus 4.6 and 1/10 of GPT-5.2 Pro. The only frontier model where you don't have to think about the bill.

**GPT-5.3 Codex** is the coding specialist. AA #2 (54), Terminal-Bench 2.0 SOTA (77.3%), 99 tok/s output speed, and a token efficiency that makes it 2-4x cheaper in practice than models generating equivalent patches. The Spark variant on Cerebras hardware hits 1,000+ tok/s for real-time coding. Reach for this when you need fast, autonomous, terminal-native code execution.

**Grok 4** brings something the other favourites lack: creative freedom. Arena #3 for creative writing, #4 overall (1495 Elo), and the highest Humanity's Last Exam score of any model (50.7%). Fewer guardrails than Claude or GPT mean more range for unconventional outputs. At $3/$15 it's reasonably priced for a frontier model, though the 42 tok/s speed and 9.77s time-to-first-token require patience.

**GLM-5** is the open-weight king. AA Index ~50 (highest open-weight score), 745B MoE with MIT license, trained entirely on Huawei Ascend chips, and the industry's lowest hallucination rate among open models. At $1/$3.20 it delivers 85-90% of Opus 4.6's quality at 1/8th the cost. Self-hostable via vLLM, SGLang, or Ollama for teams that need on-premises inference.

**DeepSeek R1-0528** is the reasoning specialist. 87.5% AIME 2025 (up from 70% in the original R1), 81.0% GPQA Diamond, MIT license, and the only frontier-class model with fully transparent chain-of-thought reasoning — you can see every step of its thinking. At $0.55/$2.19 (DeepSeek API) it's the cheapest way to access genuine reasoning capability. Not a generalist — reach for it specifically when you need mathematical or logical depth.

## Model Profiles

### gemini/gemini-3.1-pro-preview

**Tier:** frontier | **Speed:** 91 tok/s | **Context:** 1,000,000 tokens
**Strengths:** reasoning, math, science, abstract-logic, multimodal, cost-effective, long-context
**Weaknesses:** verbose, slow-TTFT, terminal-agents, iterative-coding
**Best for:** Novel reasoning, scientific computation, and multimodal tasks at the best price-to-quality ratio available.

Released February 19, 2026, Gemini 3.1 Pro is the current #1 on the Artificial Analysis Intelligence Index (57), leading by 3 points over GPT-5.3 Codex. Its ARC-AGI-2 score of 77.1% represents a 2.5x improvement over Gemini 3 Pro and decisively beats Claude Opus 4.6 (68.8%) and GPT-5.3 Codex (52.9%) on abstract reasoning. It scores 94.3% on GPQA Diamond, 80.6% on SWE-bench Verified, 97% on AIME 2025, and leads WebDev Arena (#1 for React/CSS/UI generation). Google optimized it for breadth, algorithmic creativity, and scientific computation, with three configurable thinking tiers (Low/Medium/High) that let developers trade latency for reasoning depth.

The community consensus is that 3.1 Pro is "the model that 3 Pro should have been at launch." Developers praise its one-shot problem solving ability and significantly reduced hallucination rate compared to predecessors. JetBrains reported a ~15% improvement in evaluation runs with notably better token efficiency on mathematical tasks. The nickname "smartest dumb model for coding" captures the community view: brilliant at architecture and reasoning, but occasionally fumbles implementation details in longer iterative sessions. Claude and GPT-5.3 Codex both outperform it on sustained agentic coding tasks and terminal-based workflows.

At $2/$12 per million tokens with 1M native context and multimodal input (text, image, speech, video), it's the best value proposition at the frontier. The caveat is verbosity — it generated 57M tokens during AA evaluation vs a 12M median, meaning real-world costs can be 4-5x higher than headline pricing suggests. TTFT of 35 seconds when using high-thinking mode makes interactive use sluggish.

Sources: [Artificial Analysis](https://artificialanalysis.ai/models/gemini-3-1-pro-preview), [Google Blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-pro/), [NxCode Guide](https://www.nxcode.io/en/resources/news/gemini-3-1-pro-complete-guide-benchmarks-pricing-api-2026), [TechRadar](https://www.techradar.com/ai-platforms-assistants/gemini/gemini-3-1-pro-vs-gemini-3-pro-googles-new-ai-is-slower-on-purpose-and-smarter-for-it), [Medium](https://medium.com/codex/gemini-3-1-pro-is-the-smartest-dumb-model-i-know-full-breakdown-for-coding-6d89647e2dc8)

---

### openrouter/anthropic/claude-opus-4.6

**Tier:** frontier | **Speed:** 72 tok/s | **Context:** 200,000 tokens (1M beta)
**Strengths:** coding, agentic, tool-use, reasoning, creative-writing, self-correction
**Weaknesses:** cost, verbose, abstract-reasoning-gap
**Best for:** The highest-quality option for complex coding, agentic workflows, and expert reasoning when cost is secondary.

Claude Opus 4.6, released February 5, 2026, holds the #1 position on Chatbot Arena (1503 Elo), Arena Coding (1561 Elo), and GDPval-AA (1606 — a 144-point lead over GPT-5.2). It ranks #3 on the AA Intelligence Index (53). On SWE-bench Verified it scores 80.8%, and on GPQA Diamond 91.3%. Terminal-Bench 2.0 at 65.4% is the highest score ever recorded. The model introduced "adaptive thinking" with configurable effort levels (low/medium/high/max), replacing the previous extended thinking system. Its 1M token context window (beta) maintains 98% retrieval accuracy — the best in class.

The community view is unambiguous: Opus 4.6 is the most capable model available for tasks where quality is paramount. David Hendrickson noted it leads the LMSYS leaderboard "by a HUGE margin." Developers report it plans more carefully, sustains agentic tasks for longer, and catches its own mistakes through self-correction. The GDPval results show it produces expert-tier work across finance, legal, and professional domains at >11x the speed and <1% the cost of human professionals.

The primary criticism is cost: $5/$25 per million tokens is 2.5x Gemini 3.1 Pro's price. For routine tasks, Claude Sonnet 4.6 delivers comparable results at $3/$15. The model is also more verbose than median (11M tokens during AA evaluation vs 3.8M median) and trails Gemini 3.1 Pro on abstract reasoning (ARC-AGI-2: 68.8% vs 77.1%). Some users report a personality shift from Opus 4.5 — more "disagreeable and direct," with some feeling creative writing quality regressed.

Sources: [Anthropic](https://www.anthropic.com/news/claude-opus-4-6), [Artificial Analysis](https://artificialanalysis.ai/models/claude-opus-4-6), [Vellum Benchmarks](https://www.vellum.ai/blog/claude-opus-4-6-benchmarks), [NxCode Comparison](https://www.nxcode.io/resources/news/gemini-3-1-pro-vs-claude-opus-4-6-vs-gpt-5-comparison-2026), [DataCamp](https://www.datacamp.com/blog/claude-opus-4-6)

---

### openai/gpt-5.3-codex

**Tier:** frontier | **Speed:** 99 tok/s | **Context:** 200,000 tokens
**Strengths:** agentic-coding, terminal-native, token-efficient, speed, self-debugging
**Weaknesses:** file-hallucination, high-TTFT, smaller-context-window, limited-API
**Best for:** The fastest frontier model for autonomous, terminal-native coding with exceptional token efficiency.

Released February 5, 2026, GPT-5.3 Codex is OpenAI's most advanced agentic coding model and the first model instrumental in creating itself (used during its own training and evaluation). It ranks #2 on the AA Intelligence Index (54), leads Terminal-Bench 2.0 at 77.3% (SOTA), and scores 64.7% on OSWorld-Verified and 81.4% on SWE-Lancer IC Diamond. At 99.4 tok/s output speed and 2-4x fewer tokens per equivalent patch than competitors, it's both faster and more cost-effective in practice despite $1.75/$14 headline pricing.

The community frames the Codex 5.3 vs Opus 4.6 rivalry as "The Great Convergence" — two models that have converged in overall capability but diverge in where they excel. Codex wins on execution dimensions: speed, token efficiency, terminal tasks, and code review. Opus wins on understanding dimensions: context, creativity, security, and complex reasoning. Professional developers report using both models together — one developer shipped 93,000 lines of code in 5 days using the pair, another shipped 44 PRs in 5 days. The consensus "winning strategy" is not choosing between them but routing tasks to whichever model's strengths match.

The Spark variant, powered by Cerebras WSE-3 hardware, hits 1,000+ tok/s — 15x the standard model — with a 128K context window. The main model's TTFT of 61.42 seconds is a significant limitation for interactive use, and the model has a documented tendency to hallucinate file references during refactoring. API access remains limited as OpenAI "safely enables" broader access.

Sources: [OpenAI](https://openai.com/index/introducing-gpt-5-3-codex/), [Artificial Analysis](https://artificialanalysis.ai/models/gpt-5-3-codex/providers), [NxCode Comparison](https://www.nxcode.io/resources/news/gpt-5-3-codex-vs-claude-opus-4-6-ai-coding-comparison-2026), [Every.to](https://every.to/vibe-check/codex-vs-opus), [Interconnects](https://www.interconnects.ai/p/opus-46-vs-codex-53)

---

### openrouter/x-ai/grok-4

**Tier:** frontier | **Speed:** 42 tok/s | **Context:** 256,000 tokens
**Strengths:** reasoning, math, creative-writing, hardest-benchmarks, real-time-data
**Weaknesses:** slow, verbose, limited-ecosystem, expensive-heavy-tier
**Best for:** Maximum reasoning depth on the hardest problems and unconstrained creative output.

Grok 4, released July 2025 by xAI, is a 500B-parameter model that punches above its weight on the hardest benchmarks. Its Heavy variant scores 50.7% on Humanity's Last Exam — the highest of any commercial model. Base Grok 4 achieves 80.8% on SWE-bench Verified (tied for #1), 83.3% GPQA Diamond, and approximately 1495 Arena Elo (#4 overall, #3 creative writing). The AA Intelligence Index of 42 (rank #25) understates its capability — the low score reflects extreme verbosity (88M tokens during evaluation, 7x the average) rather than weak intelligence.

The community values Grok 4 for two things no other model matches: reasoning depth on the absolute hardest problems, and creative freedom with fewer guardrails than Claude or GPT. It's the go-to model for unconventional, unconstrained output. On math competition problems (100% AIME 2025 for Heavy, 96.7% HMMT) it's genuinely world-class. The real-time X/Twitter data integration gives it a unique edge for current-events reasoning.

The tradeoffs are significant: 41.7 tok/s output speed, 9.77 second TTFT, and 2-4 minute processing times for complex tasks make it unsuitable for interactive or latency-sensitive workflows. Complex TypeScript tasks scored only 6/10 vs Claude's 8.5/10, revealing gaps in nuanced multi-step coding requiring architectural judgment. The ecosystem is the thinnest of any frontier model — least third-party tooling and community infrastructure. API access at $3/$15 per million tokens is reasonable, but the Heavy variant remains subscription-only.

Sources: [Artificial Analysis](https://artificialanalysis.ai/models/grok-4), [DataCamp](https://www.datacamp.com/blog/grok-4), [Medium](https://medium.com/@leucopsis/grok-4-independent-reviews-and-benchmarks-6c22b3beb18c), [Leanware Comparison](https://www.leanware.co/insights/grok4-claude4-opus-gemini25-pro-o3-comparison), [16x Engineer Eval](https://eval.16x.engineer/blog/grok-4-evaluation-results)

---

### openrouter/z-ai/glm-5

**Tier:** frontier | **Speed:** 66 tok/s | **Context:** 200,000 tokens
**Strengths:** agentic-coding, low-hallucination, open-weight-leader, MIT-licensed, cost-effective
**Weaknesses:** text-only, resource-heavy-local, trails-top-closed-models
**Best for:** Self-hosted frontier-class agentic coding at 5-8x lower cost than Claude Opus.

GLM-5, released February 2026 by Zhipu AI (Z.AI), is a 745B MoE model (256 experts, 8 active per token, ~40-44B active parameters) trained entirely on 100,000 Huawei Ascend chips with an MIT license. It scores ~50 on the AA Intelligence Index — the highest of any open-weight model, above Gemini 3 Pro. On SWE-bench Verified it achieves 77.8% (#1 open-weight), with 86.0% GPQA Diamond, 92.7% AIME 2026, and 1451 Arena Elo. Its paper is titled "From Vibe Coding to Agentic Engineering."

The standout metric is hallucination: GLM-5 achieved an AA-Omniscience score of -1 with a 56 percentage-point reduction in hallucination rate over GLM-4.7. It knows when to abstain rather than fabricate — industry-leading among open models. The Latent Space newsletter titled their coverage "Z.ai GLM-5: New SOTA Open Weights LLM." Multiple independent sources confirm it is "on par with Claude Opus 4.5 and Gemini 3 Pro" in practical coding and agentic tasks.

At $1/$3.20 per million tokens, GLM-5 delivers approximately 85-90% of Opus 4.6's quality at 1/8th the cost. It's self-hostable via vLLM, SGLang, xLLM, or Ollama. The limitations: text-only (no multimodal), 745B total parameters make local deployment hardware-intensive despite the sparse activation, and it does trail the top closed models by 3-4 points on SWE-bench. The English-language tooling and documentation ecosystem lags behind Western models.

Sources: [Artificial Analysis](https://artificialanalysis.ai/models/glm-5), [arXiv Paper](https://arxiv.org/html/2602.15763v1), [VentureBeat](https://venturebeat.com/technology/z-ais-open-source-glm-5-achieves-record-low-hallucination-rate-and-leverages), [Latent Space](https://www.latent.space/p/ainews-zai-glm-5-new-sota-open-weights), [Hugging Face](https://huggingface.co/zai-org/GLM-5)

---

### openai/gpt-5.2-pro

**Tier:** frontier | **Speed:** 89 tok/s | **Context:** 400,000 tokens
**Strengths:** math-reasoning, deep-logic, one-shot-coding, long-context
**Weaknesses:** extremely-expensive, slow-TTFT, over-censored
**Best for:** When correctness on hard reasoning problems is worth 12x the cost and a 37-second wait.

GPT-5.2 Pro, released December 10, 2025, is OpenAI's maximum-reasoning model. It's the only frontier model to score 100% on AIME 2025. GPQA Diamond at 93.2% is the highest reported. SWE-bench Verified at 80.0% and SWE-bench Pro at 55.6% were both SOTA at release (since matched by Gemini 3.1 Pro). Arena Elo sits at approximately 1481 and GDPval at 1462, beating or tying top professionals on 70.9% of tasks.

The price is the elephant in the room: $21/$168 per million tokens — 12x the standard GPT-5.2 ($1.75/$14) and 4-7x more than Opus 4.6. The community is split. For tasks requiring maximal reasoning depth — hard math, complex multi-step proofs, safety-critical logic — the 12x premium is defensible. For everything else, standard GPT-5.2 at $1.75/$14 delivers 95-98% of the quality. As one reviewer put it: "buying a racing helmet to commute in traffic." TTFT of 37.56 seconds makes interactive use painful, and ARC-AGI-2 at 52.9% (vs Gemini 3.1 Pro's 77.1%) reveals a surprising generalization gap on novel patterns.

The model does offer 400K context (largest among OpenAI models), 30% fewer reasoning mistakes than GPT-5.1, and supports cached input at 90% discount and batch API at 50% off — making it more viable for high-volume async workloads where per-query cost can be amortized.

Sources: [OpenAI](https://openai.com/index/introducing-gpt-5-2/), [Artificial Analysis](https://artificialanalysis.ai/models/gpt-5-2/providers), [Vellum Benchmarks](https://www.vellum.ai/blog/gpt-5-2-benchmarks), [Shumer.dev Review](https://shumer.dev/gpt52review), [LLM Stats](https://llm-stats.com/models/gpt-5.2-2025-12-11)

---

### openrouter/deepseek/deepseek-r1-0528

**Tier:** strong | **Speed:** variable (20-305 tok/s by provider) | **Context:** 128,000 tokens
**Strengths:** reasoning, math, science, open-source, transparent-cot, self-hostable
**Weaknesses:** verbose, slow, coding-weaker-than-v3, overthinks-simple-tasks
**Best for:** Hard math, science, and logical reasoning with fully transparent chain-of-thought under MIT license.

DeepSeek R1-0528, released May 28, 2025, is a 685B MoE model (37B active) with MIT license and the defining feature of transparent chain-of-thought — visible `<think>` tags showing every reasoning step. AIME 2025 at 87.5% (up from 70% in the original R1), GPQA Diamond at 81.0% (up from 71.5%), and LiveCodeBench at 73.3% (up from 63.5%) represent major improvements. AA Intelligence Index is 27, reflecting the reasoning overhead rather than capability ceiling.

The community positions R1-0528 as the strongest open-source reasoning model and a credible alternative to OpenAI o3 for math and science tasks. On LMSYS Chatbot Arena it trades blows with top proprietary models, trailing by less than 2%. Daily usage on OpenRouter remains at 100-200K+ requests. The transparent CoT is highly valued by researchers and developers who need to audit and understand model reasoning.

The tradeoffs are well-understood: it averages 23K reasoning tokens per hard problem (nearly double the original R1), making it slow and expensive relative to its headline pricing of $0.55/$2.19 (DeepSeek API). For pure coding tasks, DeepSeek V3.2 is faster, cheaper, and often more accurate — DeepSeek themselves acknowledge "R1 falls short of V3 in general-purpose tasks." The model overthinks trivially simple queries, generating 200+ thinking tokens for "what's the capital of France?"

Sources: [Artificial Analysis](https://artificialanalysis.ai/models/deepseek-r1), [Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528), [VentureBeat](https://venturebeat.com/ai/deepseek-r1-0528-arrives-in-powerful-open-source-challenge-to-openai-o3-and-google-gemini-2-5-pro/), [DEV Community](https://dev.to/forgecode/my-8-hour-reality-check-coding-with-deepseek-r1-0528-2nic), [BentoML Guide](https://www.bentoml.com/blog/the-complete-guide-to-deepseek-models-from-v3-to-r1-and-beyond)

---

### openrouter/qwen/qwen3.5-397b-a17b

**Tier:** strong | **Speed:** 85 tok/s | **Context:** 262,000 tokens
**Strengths:** math-reasoning, coding, agentic, multimodal-vision, multilingual, efficient-MoE, open-weight
**Weaknesses:** high-hallucination, verbose, expensive-for-open-weight
**Best for:** Cost-efficient agentic workflows with vision and multilingual support under Apache 2.0 license.

Qwen 3.5 397B-A17B, released February 16, 2026 by Alibaba, is a 397B MoE model with only 17B active parameters per token — inference cost comparable to a 20B dense model. Apache 2.0 license. It's the first Qwen open-weight model with native vision input, covers 201 languages and dialects (69% increase over Qwen 3), and achieves 88.4% GPQA Diamond, 91.3% AIME 2026, 76.4% SWE-bench Verified, and CodeForces Elo 2056 (top 1% programmer level). AA Intelligence Index of 45 ranks it #3 among open-weight models behind GLM-5 (50) and Kimi K2.5 (47).

The architecture is efficient: 95% reduction in activation memory vs dense equivalents, and it outperforms Qwen's own trillion-parameter Qwen3-Max on most benchmarks. At 85.2 tok/s (AA benchmark) it's the fastest model in the open-weight frontier tier. The GDPval-AA Elo of 1,221 (up 361 points from Qwen3 235B) shows strong agentic capability. The community narrative positions it as "the most architecturally ambitious" open-weight model — unifying vision, agents, and massive language coverage in a single efficient sparse model.

The weaknesses are real: hallucination rate of 88% (AA-Omniscience -32, far behind GLM-5's -1) means it answers confidently when it should refuse. It generated 86M output tokens during AA evaluation (5.7x average), inflating real-world costs. At $0.60/$3.60 per million tokens it's "particularly expensive when comparing to other open weight models of similar size" per Artificial Analysis. Too new for an established Chatbot Arena Elo.

Sources: [Artificial Analysis](https://artificialanalysis.ai/models/qwen3-5-397b-a17b), [VentureBeat](https://venturebeat.com/technology/alibabas-qwen-3-5-397b-a17-beats-its-larger-trillion-parameter-model-at-a), [Hugging Face](https://huggingface.co/Qwen/Qwen3.5-397B-A17B), [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2026/02/qwen3-5-open-weight-qwen3-5-plus/), [Digital Applied](https://www.digitalapplied.com/blog/qwen-3-5-agentic-ai-benchmarks-guide)

---

### openrouter/minimax/minimax-m2.5

**Tier:** strong | **Speed:** 50-100 tok/s | **Context:** 200,000 tokens
**Strengths:** coding, tool-calling, agentic, value, speed, open-weights
**Weaknesses:** reasoning-GPQA, hallucination, no-multimodal, generalist-ceiling
**Best for:** High-volume coding and agentic workflows at 1/20th the cost of frontier models.

MiniMax M2.5, released February 2026, is a 229B MoE model (10B active, 256 experts) with modified MIT license. The headline number: 80.2% on SWE-bench Verified — within 0.6 points of Claude Opus 4.6 — at $0.15/$1.20 per million tokens. That's 33x cheaper on input and 20x cheaper on output. Completing one SWE-bench task costs ~$0.15 with M2.5 vs ~$3.00 with Opus 4.6. On Multi-SWE-bench (multi-file tasks), M2.5 actually beats Opus at 51.3% vs 50.3%. BFCL Multi-Turn tool calling at 76.8% crushes Opus's 63.3%.

MiniMax's tagline "intelligence too cheap to meter" has become the defining meme. The community is enthusiastically positive about the value proposition while remaining clear-eyed about limitations. The Lightning variant at 100 tok/s is nearly 2x most frontier models and completed SWE-bench tasks 37% faster than M2.1. Developers describe it as opening up use cases that weren't practical before at frontier pricing.

The limitations define its niche: GPQA Diamond at 62% is far below frontier models (Gemini 3.1 Pro: 94.3%), meaning graduate-level science reasoning is a clear gap. Hallucination rate at 88% (AA 36th percentile) is a regression from M2.1. No multimodal support. AA Intelligence Index of 42 puts it behind GLM-5, Kimi K2.5, and Qwen 3.5 on general intelligence. This is a specialist coding-value model, not a generalist — and that's fine.

Sources: [MiniMax Official](https://www.minimax.io/news/minimax-m25), [Artificial Analysis](https://artificialanalysis.ai/models/minimax-m2-5), [Hacker News](https://news.ycombinator.com/item?id=46991154), [The Decoder](https://the-decoder.com/minimax-m2-5-promises-intelligence-too-cheap-to-meter-as-chinese-labs-squeeze-western-ai-pricing/), [VentureBeat](https://venturebeat.com/technology/minimaxs-new-open-m2-5-and-m2-5-lightning-near-state-of-the-art-while)

---

### openrouter/moonshotai/kimi-k2.5

**Tier:** strong | **Speed:** 42 tok/s | **Context:** 262,000 tokens
**Strengths:** agentic-swarm, vision-to-code, math-reasoning, cost-efficient, open-weight, multimodal
**Weaknesses:** verbose, hallucination-prone, identity-drift, lost-in-middle
**Best for:** Agentic automation and vision-driven coding with parallel sub-agent orchestration.

Kimi K2.5, released January 27, 2026 by Moonshot AI, is a 1.04T MoE model (32B active) with modified MIT license and native multimodal input (text, image, video). Its defining capability is agent swarm technology — Parallel-Agent Reinforcement Learning (PARL) enables up to 100 sub-agents executing 1,500 coordinated tool calls in parallel, reducing execution time by up to 4.5x. When given tools, K2.5's benchmark improvement is +20.1 percentage points — nearly double the tool-use uplift of GPT-5.2 (+11.0) or Claude (+12.4). AA Intelligence Index of 47, Arena Elo 1447, SWE-bench 76.8%, GPQA Diamond 87.6%, AIME 2025 96.1%.

The community calls it "nothing short of transformative" for agentic and visual workflows. Vision-to-code capability — feeding screenshots to reconstruct websites — is a standout feature. At $0.60/$3.00 per million tokens (with $0.10 cached input), it's approximately 8x cheaper than Opus 4.6 for comparable agentic work. The 78.4% BrowseComp score (with swarm) beats GPT-5.2 Pro on autonomous web tasks.

The weaknesses are well-documented: extreme verbosity (89M tokens during AA evaluation, 6x average), hallucination (AA-Omniscience -11, behind GLM-5's -1), occasional identity confusion (identifies as "Claude" with empty system prompts), and degraded recall from the middle of long contexts. The swarm feature is beta — agents occasionally produce redundant output, and complex sequential tasks sometimes fail when coordination breaks down. At 595GB, the full model is impractical for local deployment without significant hardware.

Sources: [Artificial Analysis](https://artificialanalysis.ai/models/kimi-k2-5), [Kimi Blog](https://www.kimi.com/blog/kimi-k2-5), [Hugging Face](https://huggingface.co/moonshotai/Kimi-K2.5), [VentureBeat](https://venturebeat.com/orchestration/moonshots-kimi-k2-5-is-open-595gb-and-built-for-agent-swarms-reddit-wants-a), [DataCamp](https://www.datacamp.com/tutorial/kimi-k2-agent-swarm-guide)

## The Full Landscape

### The Frontier Supporting Cast

**openrouter/anthropic/claude-sonnet-4.6** — Anthropic's mid-range model at $3/$15. AA Index 51, SWE-bench 79.6%, GPQA 89.9%. 70% preferred over Sonnet 4.5 in blind tests. The practical default when Opus 4.6 quality isn't needed — faster, cheaper, and 1M context in beta.

**openrouter/anthropic/claude-opus-4.5** — Previous Opus generation (November 2025). SWE-bench 80.9% (still the single highest self-reported score), GPQA 87.0%. Being superseded by 4.6 but remains available and competitive.

**openai/gpt-5.2** — Standard GPT-5.2 at $1.75/$14. Arena Elo 1481. Much cheaper than Pro for 95-98% of the quality. The sensible default for OpenAI ecosystem users.

**gemini/gemini-3-pro-preview** — Predecessor to 3.1 Pro. Arena Elo 1486 (#5), GPQA 91.9%. Still strong for multimodal tasks and the base for Google's ecosystem.

**gemini/gemini-3-flash-preview** — Arena Elo 1473 (#7). Impressive ranking for a Flash model. Good speed-intelligence balance for production workloads needing both quality and throughput.

### Speed and Value Champions

**gemini/gemini-2.5-flash** — The speed champion at 249 tok/s. $0.30/$2.50, 1M context, AA Index 21. Best for high-volume fast tasks where speed matters more than frontier intelligence.

**gemini/gemini-2.5-flash-lite** — Ultra-cheap and ultra-fast at 496 tok/s, $0.10/$0.40. Best for classification, extraction, and simple routing tasks at massive scale.

**openrouter/bytedance-seed/seed-2.0-mini** — ByteDance's surprisingly capable model. Arena Elo 1470 (#10) — higher than GLM-5 and Kimi K2.5 on human preference. SWE-bench 76.5% for the Pro variant. Aggressive pricing at $0.10/$0.40. Watch this space.

**openrouter/inception/mercury** — Optimized for raw speed. Among the fastest available models for latency-sensitive applications.

### Chinese Open-Weight Ecosystem

**openrouter/z-ai/glm-4.7** — GLM-5's predecessor. Arena Elo 1445 (#3 among open-weight), $0.10/$0.10 (both input and output). 95.7% AIME 2025. An extraordinary value play — essentially free frontier-adjacent coding.

**openrouter/z-ai/glm-4.6** — Previous generation, still available. Strong for basic tasks at extremely low cost.

**openrouter/qwen/qwen3-coder** — Alibaba's dedicated coding model. Multiple size variants including free tier. Strong for code-specific workflows.

**openrouter/qwen/qwen3-max-thinking** — Qwen's frontier reasoning variant with MoE architecture. Strong on Artificial Analysis evaluations.

**openrouter/qwen/qwq-32b** — Compact 32B reasoning model. Good for local deployment on consumer GPUs — the most capable model that fits on a single high-end GPU.

**openrouter/baidu/ernie-4.5-300b-a47b** — Baidu's flagship. Strong Chinese-language performance. Arena #18 via Ernie 5.0.

**openrouter/tencent/hunyuan-a13b-instruct** — Tencent's compact MoE. Budget option for Chinese-language tasks.

### The DeepSeek Family

**openrouter/deepseek/deepseek-v3.2** — 685B MoE, MIT license. SWE-bench ~67-73%, $0.28/$0.42. Gold IMO 2025 (35/42). Extremely cheap but verbose. For pure coding, often better than R1-0528 at a fraction of the cost.

**openrouter/deepseek/deepseek-v3.2-speciale** — High-compute V3.2 variant. Gold IMO 2025. Extremely verbose. Competition math only.

**openrouter/deepseek/deepseek-chat-v3.1** — Previous generation, #6 on OpenRouter by usage with free tier. Solid general-purpose.

**openrouter/deepseek/deepseek-r1** — Original R1 (January 2025). 70% AIME vs R1-0528's 87.5%. Superseded but still widely deployed.

### Meta and Western Open-Source

**openrouter/meta-llama/llama-4-maverick** — Meta's open MoE model. Strong multilingual. Available free on OpenRouter.

**openrouter/meta-llama/llama-4-scout** — 10M token context (largest available). For resource-constrained deployments needing maximum context.

**openrouter/meta-llama/llama-3.3-70b-instruct** — Previous gen but battle-tested. Available free on OpenRouter. Good baseline model.

**openrouter/mistralai/mistral-large-2512** — Mistral's flagship (January 2026). Strong European alternative with good multilingual support.

**openrouter/mistralai/devstral-medium** — Mistral's dedicated coding model. Competitive at lower cost.

**openrouter/openai/gpt-oss-120b** — OpenAI's first open-weight model. MMLU 90.0, GPQA 80.9%. Available free on OpenRouter. A historic moment for OpenAI's open-source strategy.

### Reasoning and Research Specialty

**openai/o3** — OpenAI's dedicated reasoning model at $10/$40. Largely superseded by GPT-5.2 Pro for most use cases.

**openai/o4-mini** — Compact reasoning at $1.10/$4.40. Good speed-to-reasoning tradeoff for cost-sensitive reasoning tasks.

**openrouter/perplexity/sonar-deep-research** — Not a general LLM. Web research tool that synthesizes cited reports. ~$1/query. Best for deep research tasks requiring source synthesis.

**openrouter/perplexity/sonar-pro** — Search-augmented model for current information retrieval.

### Other Notable Models

**openrouter/x-ai/grok-4.1-fast** — Speed-optimized Grok 4 variant. Trades reasoning depth for faster inference.

**openrouter/x-ai/grok-3** — Previous xAI generation. Still capable and cheaper than Grok 4.

**openrouter/amazon/nova-premier-v1** — Amazon's flagship. Competitive pricing via Bedrock for AWS-integrated workflows.

**openrouter/cohere/command-a** — Cohere's latest. Strong RAG and enterprise search capabilities.

**openrouter/writer/palmyra-x5** — Writer's enterprise model optimized for business writing and content.

**openrouter/nvidia/llama-3.3-nemotron-super-49b-v1.5** — NVIDIA fine-tuned Llama optimized for NVIDIA hardware.

**openrouter/google/gemma-3-27b-it** — Google's open model. Free on OpenRouter. Good for basic tasks and fine-tuning.

**gemini/gemini-2.5-pro** — Previous Pro generation. Pioneered thinking budgets, 1M context. Well-documented and stable.

**gemini/gemini-2.0-flash** — Older Flash, still #5 on OpenRouter by usage. Reliable for simple tasks.

## Data Sources

- [Artificial Analysis Intelligence Index v4.0](https://artificialanalysis.ai/leaderboards/models) (fetched 2026-02-27) — composite of 10 evaluations: GDPval-AA, tau-squared-Bench, Terminal-Bench Hard, SciCode, AA-LCR, AA-Omniscience, IFBench, HLE, GPQA Diamond, CritPt
- [Arena.ai (Chatbot Arena) Elo Leaderboard](https://arena.ai/leaderboard) (fetched 2026-02-27) — human preference scores across 316+ models
- [OpenRouter Rankings](https://openrouter.ai/rankings) (fetched 2026-02-27) — real-world usage and intelligence/coding/agentic category scores
- [Onyx.app LLM Leaderboard](https://onyx.app/llm-leaderboard) (fetched 2026-02-27) — aggregated benchmarks with tier classification
- [SWE-bench Verified (Epoch AI v2.0.0)](https://epoch.ai/benchmarks/swe-bench-verified) — software engineering benchmark
- [Simon Willison's SWE-bench Summary](https://simonwillison.net/2026/Feb/19/swe-bench/) (2026-02-19) — Epoch v2.0.0 rescored results
- [FelloAI Best AI February 2026](https://felloai.com/best-ai-february-2026/) — use-case-based rankings
- ask-another `search_families` and `search_models` APIs — available model catalog (59 provider families, 400+ model variants)

## Methodology

This report was produced through a three-stage process:

**Stage 1: Survey.** Five ranking sources were consulted — three established (Artificial Analysis, Arena.ai, OpenRouter) and two discovered via search (Onyx.app, llm-stats.com). The full ask-another model catalog was pulled via API. Rankings were cross-referenced to identify the top 10 models for deep research, selecting for diversity of provider, capability tier, and use case.

**Stage 2: Deep Research.** For each of the 10 shortlisted models, 3-4 targeted web searches were conducted covering benchmarks, community reception, and metric gaps. Artificial Analysis model pages were fetched for standardized metrics where available. Research was conducted via WebSearch and WebFetch at zero API cost.

**Stage 3: Report.** Five favourites were selected (one per provider family, covering distinct use cases) and approved by the user. All metrics were cross-referenced across sources; where numbers conflicted, the most recent and most widely cited figure was used. The AA Intelligence Index v4.0 was used as the primary sorting metric for the data file, supplemented by Arena Elo, SWE-bench Verified, and GPQA Diamond.

**Caveats:** Benchmark scores are self-reported or third-party evaluated under varying conditions. The Epoch v2.0.0 rescoring of SWE-bench produced lower numbers than earlier evaluations — both versions appear in the literature. AA Intelligence Index scores changed when v4.0 launched with new evaluation components. Pricing reflects API rates as of late February 2026 and may have changed. Speed measurements vary significantly by provider and configuration.
