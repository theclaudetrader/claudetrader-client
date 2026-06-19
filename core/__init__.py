"""claudetrader-client core engine.

Clean library layer — NO print/UI coupling. Every function returns structured
data so a CLI, a GUI, or a packaged app can sit on top unchanged. The engine
writes a state.json (the decoupling seam) that any front-end can read.
"""
