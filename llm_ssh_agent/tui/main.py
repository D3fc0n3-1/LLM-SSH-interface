# File: llm_ssh_agent/tui/main.py

from ..core_logic import CoreLogic
from .app import LLMSshApp
from ..app_state import AppState, LLMConfig # Import AppState and LLMConfig

def run():
    """Entry point for the TUI application."""

    # Create a custom LLMConfig with your Ollama server's base_url
    ollama_config = LLMConfig(
        provider="ollama",
        model_name="gemma:2b", # Make sure this matches the model you have
        base_url="http://192.168.50.221:30434" # <-- Your Ollama Server Address
    )

    # Create an AppState with this custom LLMConfig
    initial_app_state = AppState(current_llm_config=ollama_config)

    # Create CoreLogic
    core_logic = CoreLogic()

    # Assign the initial state
    core_logic.state = initial_app_state

    # --- ADD THIS LINE ---
    # Update the LLM interface within core_logic with the correct config
    core_logic.update_llm_settings(initial_app_state.current_llm_config)
    # -------------------

    # Initialize and run the Textual application
    app = LLMSshApp(core_logic)
    app.run()

if __name__ == "__main__":
    run()
