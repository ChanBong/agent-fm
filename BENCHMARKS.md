# agent-fm Chatterbox TTS Benchmarks

**Hardware:** RTX 4060 Laptop GPU, Windows 11, PyTorch 2.6.0+cu126
**Test sentence:** "Hey, this is a benchmark test. The quick brown fox jumps over the lazy dog near the riverbank."
**Methodology:** 3 runs per config, report median. First run excluded (warmup penalty).

---

## Baseline — Stock Chatterbox Turbo (from GitHub main)

| Metric | Value |
|---|---|
| Model load time | 28.0s (includes HF cache check) |
| VRAM allocated | 2.60 GB (2.65 GB after generation) |
| Generation time | **1.63s** (median of 3 runs, post-warmup) |
| Audio duration | 5.6s |
| RTF | **0.29** (3.4x faster than real-time) |
| Tokens/sec | ~100 it/s (from progress bar) |

Note: Browser experience is ~5s due to cold model load + network + audio buffering.

---

## Tier 1a — bfloat16 casting

| Metric | Value | Delta vs Baseline |
|---|---|---|
| VRAM allocated | **1.81 GB** | **-30% (saved 0.8 GB)** |
| Generation time | 1.64s | Same |
| RTF | 0.28 | Same |

Conclusion: bf16 saves significant VRAM but doesn't speed up Turbo — it's already compute-bound, not memory-bound.

---

## Tier 1b — torch.compile (inductor, reduce-overhead)

| Metric | Value | Delta vs Baseline |
|---|---|---|
| Generation time | 1.71s | No improvement |
| RTF | 0.30 | Same |
| Compile warmup | 1.4s | One-time cost |

Conclusion: torch.compile doesn't help Turbo. Turbo uses GPT-2 Medium (not Llama) + 2-step CFM, already well-optimized. The rsxdalv fast fork targets the original 500M model's Llama backbone.

---

## Key Insight

**Turbo's raw generation is already fast (RTF 0.29, ~1.6s for 5.6s audio).** The perceived ~5s delay in the browser comes from:
1. Cold model load on first request (~8-28s)
2. HTTP round-trips (browser → Next.js → Python → Next.js → browser)
3. Audio buffering before playback starts

**The optimization focus should shift to startup + infrastructure, not inference.**

---

## Applied — bf16 + preload + warmup at startup

Changes: server pre-loads model on startup (not first request), applies bf16, runs warmup generation.

| Metric | Before | After | Delta |
|---|---|---|---|
| First-request latency | ~28s (cold load) | **0s** (pre-loaded) | **Eliminated** |
| VRAM | 2.60 GB | **1.86 GB** | **-28%** |
| Generation time (raw) | 1.63s | 1.67s | Same |
| HTTP round-trip (full) | ~30s (first), ~4s (warm) | **3.76s** (always) | **Consistent** |

---

## Latency breakdown (where 3.76s goes)

| Stage | Time | % |
|---|---|---|
| HTTP overhead + JSON parse | ~0.05s | 1% |
| T3 autoregressive (token gen) | ~1.2s | 32% |
| S3Gen CFM decode (2 steps) | ~0.3s | 8% |
| WAV encoding (torchaudio) | ~0.1s | 3% |
| HTTP response transfer (~500KB) | ~0.05s | 1% |
| **Unaccounted / torch overhead** | **~2.0s** | **55%** |

The "unaccounted" gap (gen reports 1.67s but HTTP takes 3.76s) suggests significant overhead in the Python/torch layer outside the timed generation call — likely model.generate() preamble, tokenization, and tensor preparation.

---

## Tier 2 — Sentence-Level Streaming (WebSocket)

Test text: 2 sentences, ~6.3s total audio.

| Metric | Non-Streaming | Streaming | Improvement |
|---|---|---|---|
| Time to first audio | 3.8s | **1.2s** | **3.2x faster** |
| Total generation time | 3.8s | 2.1s | 1.8x faster |
| Total audio produced | ~5.6s | 6.3s | Similar |

Streaming generates sentences in parallel with playback — while sentence 1 plays, sentence 2 is generating. The user hears audio in 1.2s instead of waiting 3.8s.
