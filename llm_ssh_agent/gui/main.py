# File: llm_ssh_agent/gui/main.py
# Type: Python Module

# --- GUI STUB ---
# This file is a placeholder to show where GUI code would go.
# Implementing it requires CustomTkinter setup and similar logic
# to the TUI, connecting UI elements to core_logic callbacks.

import sys

def run():
    """Entry point for the GUI application (STUB)."""
    print("GUI Mode is not yet implemented.")
    print("Please run the TUI using 'llm-ssh-tui' or 'poetry run llm-ssh-tui'")
    # Example check before importing GUI libraries:
    # try:
    #     import customtkinter
    # except ImportError:
    #     print("Error: CustomTkinter is required for GUI mode.")
    #     print("Install it via pip install customtkinter")
    #     sys.exit(1)
    #
    # from ..core_logic import CoreLogic
    # # from .app import LLMSshGuiApp # Assuming you create this
    #
    # core_logic = CoreLogic()
    # # app = LLMSshGuiApp(core_logic)
    # # app.run() # Or app.mainloop() for tkinter
    sys.exit(0)


if __name__ == "__main__":
    run()