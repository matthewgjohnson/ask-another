# Model Research Report

Generated: 1 March 2026

## Editorial Overview

The model landscape in early 2026 is the most competitive it has ever been, and the old assumption that "OpenAI leads, everyone else follows" is dead. Google's Gemini 3.1 Pro now holds the #1 spot on the Artificial Analysis Intelligence Index, while Anthropic's Claude Opus 4.6 dominates human preference in the Arena. OpenAI's GPT-5.x series remains formidable — particularly on reasoning and speed — but no single provider owns the frontier anymore. The race is genuinely three-way at the top, with Chinese labs closing fast on specific axes.

The most striking shift is the rise of Chinese open-source models as serious contenders. DeepSeek V3.2 won gold at IMO 2025 and costs less than a cent per million input tokens. GLM-5 from Zhipu AI — trained entirely on Huawei Ascend hardware — holds the #1 open-weight position with MIT licensing and the lowest hallucination rates in the field. Moonshot's Kimi K2.5 introduced a 100-agent swarm architecture that represents a genuinely different approach to reasoning. These aren't "cheap alternatives" anymore — they're architecturally distinct systems that think differently from Western models, which makes them valuable precisely for their independence.

For teams building with LLMs, the practical implication is clear: monoculture is a risk. Two models scoring 80% on the same benchmark may share 95% of their correct answers — or 60%. Benchmarks measure performance on axes, not independence between models. A diversity-optimised portfolio of thinking partners — spanning different training philosophies, data pipelines, hardware, and alignment approaches — will produce better hypotheses and catch more blind spots than picking the single highest-scoring model and running everything through it.

Pricing has collapsed at every tier. Frontier-quality reasoning is now available for under $1 per million tokens from multiple providers. The cost of querying five diverse models is often less than what a single GPT-4 call cost 18 months ago. This makes multi-model workflows not just intellectually appealing but economically trivial.

One surprise from this research: MiniMax M2.5 delivers SWE-bench scores (80.2%) that rival Claude Opus and Gemini Pro at a fraction of the cost, but its GPQA score (62%) suggests the coding performance may be narrowly optimised rather than reflecting broad intelligence. ByteDance's Seed 2.0 family is quietly building market share through aggressive pricing and production-grade throughput, even if the Mini variant's hallucination rate (62% accuracy) makes it unsuitable as a primary thinking partner.

## Recommended Favourites

| Model | Tier | Speed | Best For |
|-------|------|-------|----------|
| gemini/gemini-3.1-pro-preview | Frontier | 91 tok/s | Scientific reasoning, large-context synthesis |
| openai/gpt-5.2 | Frontier | 98 tok/s | Math, professional knowledge, fast iteration |
| openrouter/z-ai/glm-5 | Frontier (Open) | 70 tok/s | Agentic tasks, contrarian perspectives |
| openrouter/deepseek/deepseek-v3.2 | Frontier (Open) | 39 tok/s | Transparent reasoning chains, math, extreme value |
| openrouter/moonshotai/kimi-k2.5 | Frontier (Open) | 42 tok/s | Complex multi-step problems, parallel decomposition |

These five were chosen not just for capability but for **independence of thought**. Each represents a distinct training philosophy, data pipeline, and alignment approach:

**Gemini 3.1 Pro** is the benchmark leader (AA Index 57, GPQA 94.3%) and the only model trained multimodal-native from the ground up. Google's research culture and 1M token context window make it the strongest option for scientific reasoning and large-scale information synthesis. Its approach to problems reflects Google's search-and-retrieval DNA — it's excellent at connecting disparate information.

**GPT-5.2** brings OpenAI's RLHF-heavy alignment approach, which produces a more assertive and "opinionated" reasoning style. With 100% AIME 2025 and GPQA 92.4%, it's the strongest pure mathematical reasoner in the set. At 98 tok/s it's also the fastest frontier model, making it ideal for rapid iteration cycles. The Pro variant ($21/$84) pushes reasoning further but the standard version ($1.75/$14) is the sweet spot.

**GLM-5** is the most genuinely independent model in this portfolio. Trained on Huawei Ascend hardware (not NVIDIA), using a 745B MoE architecture with MIT licensing, it comes from a fundamentally different computational lineage. It holds the lowest hallucination rate of any frontier model and achieved Arena Elo 1451. When the other four models converge on an answer, GLM-5 is the one most likely to see something different.

**DeepSeek V3.2** represents the open-source reasoning revolution. Its 685B MoE architecture, trained with reinforcement learning using verifiable rewards, produces transparent chain-of-thought reasoning you can actually inspect. Gold medal at IMO 2025 (35/42 on the Speciale variant). At $0.028 per million input tokens, you can run it thousands of times for the cost of a single frontier query. MIT licensed.

**Kimi K2.5** is the structural wildcard. Its 1T MoE architecture with 100-agent swarm parallelisation is not just a different model — it's a different paradigm for how to approach problems. Where other models reason sequentially, K2.5 decomposes problems across sub-agents. GPQA 87.6% and strong vision-to-code capabilities. Open-weight under its own license.

## Model Profiles

### gemini/gemini-3.1-pro-preview

**Tier:** Frontier | **Speed:** 91 tok/s | **Context:** 1,000,000 tokens
**Strengths:** Scientific reasoning, GPQA leader, multimodal-native, 1M context, ARC-AGI-2 77.1%
**Weaknesses:** Newer model with less community feedback, Google-ecosystem affinity
**Best for:** Complex scientific reasoning, large-context document synthesis, and multimodal analysis.

Gemini 3.1 Pro holds the #1 position on the Artificial Analysis Intelligence Index (57) and leads on GPQA Diamond at 94.3% — the highest reasoning score of any available model. It achieved 80.6% on SWE-bench Verified and 77.1% on ARC-AGI-2, placing it at or near the top across every major benchmark category.

The model's 1M token context window is production-ready (not just a preview), making it uniquely suited for tasks that require synthesising large bodies of information. Its multimodal training is native rather than bolted-on, which shows in its ability to reason across text, images, and structured data simultaneously.

At $2.00/$12.00 per million tokens, it offers the best price-to-quality ratio at the frontier tier. Community reception has been strongly positive, with developers particularly praising its reasoning depth and context handling. The main concern is that as a preview model, its behaviour may shift before general availability.

Sources: artificialanalysis.ai, arena.ai, Google AI blog, developer community feedback

---

### openai/gpt-5.2

**Tier:** Frontier | **Speed:** 98 tok/s | **Context:** 200,000 tokens
**Strengths:** Mathematical reasoning, speed, RLHF-refined instruction following, Pro variant available
**Weaknesses:** Smaller context than Gemini, higher cost for Pro variant, RLHF can produce overconfidence
**Best for:** Mathematical reasoning, fast iteration, professional knowledge work.

GPT-5.2 is OpenAI's current-generation workhorse. The standard variant ($1.75/$14) delivers GPQA 92.4% and 98 tok/s — making it both one of the most capable and fastest frontier models. The Pro variant pushes to 100% on AIME 2025 and the highest reported GPQA scores, but at 12x the cost ($21/$84) it's a specialised tool for maximum reasoning depth.

OpenAI's RLHF-heavy alignment approach gives GPT-5.2 a distinctive "personality" — it's more assertive in its reasoning, more willing to commit to answers, and sometimes more confidently wrong. This makes it a useful counterpoint to more hedging models. Its instruction-following is among the best in the field.

The Codex variant (GPT-5.3) pushes coding performance further with Terminal-Bench SOTA at 77.3% and a Spark mode exceeding 1000 tok/s, but for thinking partnership the standard 5.2 is the better all-rounder. Community consensus is that GPT-5.2 represents OpenAI's most balanced model to date.

Sources: openai.com, artificialanalysis.ai, arena.ai, developer forums

---

### openrouter/z-ai/glm-5

**Tier:** Frontier (Open) | **Speed:** 70 tok/s | **Context:** 128,000 tokens
**Strengths:** Lowest hallucination rate, MIT license, 745B MoE, independent hardware lineage
**Weaknesses:** Smaller context window, less established ecosystem, Huawei Ascend availability
**Best for:** Agentic tasks where reliability matters, coding, and providing genuinely independent perspectives.

GLM-5 from Zhipu AI is the #1 open-weight model and the most architecturally independent model in this portfolio. Its 745B Mixture-of-Experts architecture was trained entirely on Huawei Ascend hardware — not NVIDIA GPUs — which means even the low-level numerical properties of its inference differ from every other model on this list. It holds the record for lowest hallucination rate among frontier models.

With Arena Elo 1451, SWE-bench 77.8%, GPQA 86.0%, and 95.7% on AIME, GLM-5 is genuinely frontier-capable across all axes. Its MIT license makes it the most permissively licensed frontier model available. At $0.80/$2.56 per million tokens via OpenRouter, it's substantially cheaper than Western frontier models.

The GLM family (previously ChatGLM) has been iterating rapidly, with GLM-4.7 offering an even cheaper option ($0.10/$0.10) at Arena 1445. Community feedback highlights GLM-5's reliability in agentic workflows and its tendency to produce more conservative, well-grounded responses — a useful property when you want a model that says "I don't know" rather than fabricating.

Sources: zhipuai.cn, arena.ai, openrouter.ai, Huawei Ascend documentation

---

### openrouter/deepseek/deepseek-v3.2

**Tier:** Frontier (Open) | **Speed:** 39 tok/s | **Context:** 128,000 tokens
**Strengths:** Gold IMO 2025, MIT license, transparent reasoning, absurdly cheap, 685B MoE
**Weaknesses:** Slower inference, Chinese-first documentation, reasoning can be verbose
**Best for:** Transparent reasoning chains, mathematical proof, code generation at extreme value.

DeepSeek V3.2 is the model that broke the cost curve. At $0.028 per million input tokens and $0.42 per million output tokens, it costs roughly 1/50th of a frontier Western model while delivering genuinely competitive performance. Its 685B MoE architecture won gold at IMO 2025, and the Speciale variant scored 35/42 on the competition.

What makes V3.2 particularly valuable as a thinking partner is its training methodology: reinforcement learning with verifiable rewards produces chain-of-thought reasoning that is explicitly inspectable. You can see why the model reached its conclusion, not just what it concluded. This transparency is rare at the frontier tier.

The model is MIT licensed and has spawned an enormous ecosystem of fine-tunes and distillations. Community consensus is overwhelmingly positive — developers praise its reasoning depth, coding capability, and the fact that it often outperforms models costing 100x more. The main complaint is speed (39 tok/s) and occasionally verbose output when reasoning through complex problems. Better than R1 for pure coding; R1-0528 remains slightly ahead for dedicated reasoning tasks.

Sources: deepseek.com, artificialanalysis.ai, arena.ai, GitHub community

---

### openrouter/moonshotai/kimi-k2.5

**Tier:** Frontier (Open) | **Speed:** 42 tok/s | **Context:** 131,072 tokens
**Strengths:** Agent swarm architecture, 1T MoE, vision-to-code, GPQA 87.6%, open-weight
**Weaknesses:** Newer with less battle-testing, swarm overhead, complex deployment
**Best for:** Complex multi-step problems, visual reasoning, and seeing how parallel decomposition changes answers.

Kimi K2.5 from Moonshot AI is the most architecturally novel model in this portfolio. Its 1 trillion parameter MoE architecture (32B active) deploys up to 100 sub-agents in a swarm configuration — a fundamentally different approach to reasoning than sequential chain-of-thought. Where other models think step-by-step, K2.5 decomposes problems into parallel threads and synthesises results.

With GPQA 87.6%, SWE-bench 76.8%, and strong vision-to-code capabilities, it's not just a novelty — it's genuinely competitive. The K2 predecessor established Moonshot's reputation for agentic capability, and K2.5 pushes that further with the swarm architecture.

The practical value for thinking partnership is unique: K2.5 will often decompose a problem differently than any sequential model would, exposing structural assumptions that other models share but never question. Its vision-to-code pipeline can take a screenshot or diagram and reason about implementation in ways that text-only models miss entirely. Open-weight under Moonshot's license, with the K2 variant also available for simpler tasks.

Sources: moonshot.cn, arena.ai, openrouter.ai, developer community

---

## The Full Landscape

### Mid-Range Workhorses

**openrouter/anthropic/claude-sonnet-4.6** — Anthropic's mid-range offering, 70% preferred over Sonnet 4.5 in human evaluation, 1M context in beta. Strong coding and creative writing at roughly half the cost of Opus. The default recommendation for teams already in the Anthropic ecosystem who don't need maximum reasoning depth.

**openai/gpt-5.2-pro** — The "turn it up to 11" variant of GPT-5.2. 100% AIME 2025, highest GPQA (93.2%), but at $21/$84 per million tokens it's a specialised tool for maximum reasoning depth rather than everyday use. Best reserved for problems where standard GPT-5.2 falls short.

**openai/gpt-5.3-codex** — OpenAI's dedicated coding model. Terminal-Bench SOTA 77.3%, Spark variant exceeding 1000 tok/s. AA Index #2. If coding speed and throughput matter more than reasoning diversity, this is the pick.

### Value Leaders

**openrouter/minimax/minimax-m2.5** — SWE-bench 80.2% at 1/20th Opus cost with Lightning mode at 100 tok/s. Open-weights (229B MoE). The gap between its stellar coding scores and mediocre GPQA (62%) suggests narrow optimisation, but for pure coding tasks the value is exceptional.

**openrouter/bytedance-seed/seed-2.0-mini** — ByteDance's cost leader at $0.10/$0.40 per million tokens. Arena ~1470 Elo (Pro variant), 256K context. Optimised for throughput over latency with four reasoning effort modes. Hallucination accuracy of 62% limits its use as a thinking partner, but for high-volume production tasks the economics are hard to beat.

**openrouter/z-ai/glm-4.7** — GLM-5's smaller sibling at $0.10/$0.10 per million tokens. Arena 1445, 95.7% AIME. Essentially free frontier-adjacent coding. The best option when you need a capable model at negligible cost.

### Chinese Lab Contenders

**openrouter/qwen/qwen3.5-397b-a17b** — Alibaba's flagship: 397B MoE (17B active), Apache 2.0, 91.3% AIME 2026, 201 languages. Strong across the board but training approach is sufficiently similar to DeepSeek that the two are somewhat correlated. Best for multilingual tasks.

**openrouter/baidu/ernie-4.5-300b-a47b** — Baidu's 2.4T parameter ultra-sparse MoE. Arena #8 globally at 1460 Elo when including Ernie 5.0. Strong multimodal native training and Chinese-language specialisation. Real-world instruction-following inconsistencies and slow inference (32 tok/s) limit practical appeal, but benchmark performance is genuinely impressive.

**openrouter/deepseek/deepseek-r1-0528** — DeepSeek's dedicated reasoning model. 87.5% AIME, MIT license, transparent chain-of-thought. Largely superseded by V3.2 for general use but remains the better choice for dedicated mathematical and logical reasoning tasks where you want to inspect the full reasoning chain.

### Open-Weight Ecosystem

**openrouter/meta-llama/llama-4-maverick** — Meta's open MoE, strong multilingual, free on OpenRouter. Battle-tested ecosystem with enormous community support.

**openrouter/meta-llama/llama-4-scout** — 10M token context window — the largest available. Smaller model but the context length is unmatched for specific use cases.

**openai/gpt-oss-120b** — OpenAI's first open-weight model. MMLU 90.0, GPQA 80.9%, free on OpenRouter. Significant as a signal of OpenAI's strategic shift toward open models.

**openrouter/google/gemma-3-27b-it** — Google's open model, free on OpenRouter. Good for basic tasks and fine-tuning experiments.

## Data Sources

- Artificial Analysis Intelligence Index and model pages (artificialanalysis.ai) — accessed 1 March 2026
- Arena (formerly LMSYS Chatbot Arena) leaderboard (arena.ai) — accessed 1 March 2026
- OpenRouter rankings and usage data (openrouter.ai/rankings) — accessed 1 March 2026
- ask-another model catalog — 52 catalog entries, 300+ models via search
- Individual model documentation and technical reports from Google, OpenAI, Zhipu AI, DeepSeek, Moonshot AI, Alibaba, ByteDance, Baidu, MiniMax, Meta
- Developer community feedback from GitHub, Reddit, Hacker News, and technical blogs

## Methodology

This report was produced using a three-stage process: (1) Survey — ranking data was pulled from three primary leaderboards (Artificial Analysis, Arena, OpenRouter) and cross-referenced against the available model catalog in ask-another, filtered for ZDR compatibility; (2) Deep Research — targeted web searches for benchmarks, community reception, and metric gaps for each of 10 shortlisted models; (3) Recommendation — favourites were selected to maximise diversity of thinking (training philosophy, data pipeline, hardware lineage, alignment approach) rather than raw benchmark scores alone.

All models were filtered for Zero Data Retention (ZDR) compatibility via OpenRouter. Models without ZDR guarantees (notably xAI/Grok) were excluded from consideration regardless of benchmark performance. Pricing reflects OpenRouter and direct API rates as of March 2026. Benchmark scores were sourced from Artificial Analysis, Arena, and official model documentation; where sources disagreed, the most conservative figure was used.
