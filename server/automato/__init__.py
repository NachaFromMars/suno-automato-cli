"""automato — guarded Suno music factory service layer (P4/P5).

Wraps the battle-tested suno-automato-cli scripts behind one gated chokepoint:
engine.submit_job(). REST (/api/v1), dashboard UI and MCP tools all go through
the same engine — no ungated generation path exists in this package (F-10).
"""
__version__ = "0.1.0"
