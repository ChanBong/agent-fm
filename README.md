# agent-fm

Give your AI agent a voice.

An MCP server that lets AI coding agents speak to you via text-to-speech. The agent decides when and what to say — like a colleague tapping your shoulder.

## Install

```bash
pip install agent-fm
```

## Add to Claude Code

```bash
claude mcp add agent-fm -- uvx agent-fm
```

## How it works

agent-fm exposes a `speak` tool via MCP. When your AI agent finishes a task, needs a decision, or hits an error, it calls `speak()` and you hear it through your speakers.

Powered by [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) — a high-quality, 82M-parameter TTS model that runs locally on CPU. Falls back to system TTS if Kokoro is unavailable.
