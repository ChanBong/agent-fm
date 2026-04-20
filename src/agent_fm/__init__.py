"""agent-fm: Give your AI agent a voice.

An MCP server that lets AI coding agents speak to you via text-to-speech.
The agent decides when and what to say — like a colleague tapping your shoulder.
"""

__version__ = "0.1.0"


def main() -> None:
    """Entry point for the agent-fm MCP server."""
    from .server import mcp

    mcp.run(transport="stdio")
