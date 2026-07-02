"""stdio MCP entry point: python -m automato.mcp"""
from .mcp_tools import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
