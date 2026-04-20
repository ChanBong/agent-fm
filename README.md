# agent-fm

Give your AI agent a voice.

An MCP server that lets AI coding agents speak to you via text-to-speech. The agent decides when and what to say — like a colleague tapping your shoulder.

**No cloud API. No API keys. Runs locally on CPU.**

## Quick Start

```bash
# Add to Claude Code
claude mcp add agent-fm -- uvx agent-fm

# Pre-download models + verify setup (~340MB, one-time)
uvx agent-fm warmup
```

That's it. Your agent can now talk to you.

### Linux only

```bash
# sounddevice needs PortAudio
sudo apt install libportaudio2
```

macOS and Windows need **zero system dependencies**.

## What It Does

agent-fm gives your AI agent a `speak()` tool. Instead of you polling the terminal to check if your agent is done, it tells you:

- "Hey, the auth refactor is done. All tests pass."
- "Quick question — should I use Redis or in-memory caching here?"
- "Heads up, there's a circular import in the payments module."

The agent decides *when* to speak based on instructions you can customize. You just work — it interrupts you only when it matters.

## How It Works

1. **MCP server** exposes `speak`, `list_voices`, and `set_voice` tools
2. **Kokoro TTS** (82M params) generates speech locally — 54 voices, 9 languages
3. **Audio queue** plays messages through your speakers, one at a time
4. **AGENTS.md** teaches your agent when to speak and when to stay quiet

## Install

### Claude Code

```bash
claude mcp add agent-fm -- uvx agent-fm
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agent-fm": {
      "command": "uvx",
      "args": ["agent-fm"]
    }
  }
}
```

### VS Code / Copilot

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "agent-fm": {
      "command": "uvx",
      "args": ["agent-fm"]
    }
  }
}
```

### Cline / Windsurf

Same `"command": "uvx", "args": ["agent-fm"]` pattern in your platform's MCP config.

### pip (alternative)

```bash
pip install agent-fm
python -m agent_fm
```

## Tools

| Tool | Description |
|---|---|
| `speak` | Speak a message aloud. Params: `message`, `urgency` (info/warning/critical), `voice`, `speed` |
| `list_voices` | List available voices, filterable by language |
| `set_voice` | Change the default voice and speed for the session |

## Teaching Your Agent When to Speak

agent-fm ships with an `AGENTS.md` you can drop into your project or `~/.claude/CLAUDE.md`:

```markdown
## Voice (agent-fm)

You have a `speak` tool. Use it to talk aloud — the user may not be watching the screen.

When to speak:
- Finished a task: speak("Done with the auth refactor. All tests pass.")
- Need input: speak("Quick question — should I use Redis or an in-memory cache here?")
- Found a problem: speak("Heads up, there's a circular import in the payments module.")
- About to do something big: speak("Starting the full test suite, this'll take a minute.")

Don't speak for trivial ops, every step, or to repeat what's already on screen.
1-2 sentences max. Talk like a colleague, not a robot.
```

This is what makes agent-fm different from a simple TTS wrapper — it teaches the agent *judgment* about when to interrupt you.

## Voices

54 voices across 9 languages:

| Language | Voices |
|---|---|
| English (US) | 20 (11 female, 9 male) |
| English (UK) | 8 (4 female, 4 male) |
| Japanese | 5 |
| Mandarin | 8 |
| Hindi | 4 |
| Spanish | 3 |
| French | 1 |
| Italian | 2 |
| Portuguese | 3 |

Default voice: `am_fenrir`. Change anytime:

```
Use the set_voice tool to switch to af_heart
```

## CLI

```bash
agent-fm              # Run MCP server (stdio transport)
agent-fm warmup       # Download models + test setup
agent-fm --version    # Show version
```

## System Requirements

| Platform | System deps | Notes |
|---|---|---|
| **macOS** | None | Just works |
| **Windows** | None | Just works |
| **Linux** | `sudo apt install libportaudio2` | PortAudio for audio playback |

Python 3.10-3.12 recommended. espeak-ng is bundled automatically via `espeakng-loader`.

Models auto-download to `~/.agent-fm/models/` on first use (~340MB).

## Uninstall

```bash
# 1. Remove from Claude Code
claude mcp remove agent-fm
claude mcp remove agent-fm -s user    # if added globally

# 2. Remove package
uv tool uninstall agent-fm            # if installed with uvx
# or: pip uninstall agent-fm          # if installed with pip

# 3. Remove cached models (~340MB)
rm -rf ~/.agent-fm/
```

## Built With

- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) — MCP server framework
- [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) — neural TTS model (ONNX, CPU)
- [sounddevice](https://python-sounddevice.readthedocs.io/) — cross-platform audio

## License

MIT
