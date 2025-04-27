# File: llm_ssh_agent/llm_interface.py
# Type: Python Module

import ollama
from typing import List, Optional, Tuple
import re
from .app_state import ChatMessage, LLMConfig

# Regex to find SSH commands formatted as [SSH_COMMAND] command_text
SSH_COMMAND_REGEX = re.compile(r"\[SSH_COMMAND\]\s*(.*)")

class LLMInterface:
    """Handles interaction with the configured LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config

        print(f"DEBUG: In LLMInterface __init__, received base_url: {self.config.base_url}") # <-- Add this print

        self.client = None
        if self.config.provider == "ollama":
            try:
                # If base_url is provided, use it for Ollama client
                self.client = ollama.Client(host=self.config.base_url) if self.config.base_url else ollama.Client()
                # Check if model exists? Ollama library might handle this.
                print(f"Ollama client initialized. Using model: {config.model_name}")
                # Try a simple list to see if client is working
                self.client.list()
                print("Ollama connection successful.")
            except Exception as e:
                print(f"Error initializing Ollama client (host={self.config.base_url}): {e}")
                print("LLM functionality may be limited.")
                self.client = None # Ensure client is None if init failed
        # Add elif blocks here for other providers (Gemini, HuggingFace API...)

    def update_config(self, new_config: LLMConfig):
        """Updates the LLM configuration and re-initializes the client if necessary."""
        # Basic implementation: just replace config and re-init client
        # More robust: check if relevant parts changed before re-initializing
        print(f"Updating LLM config to: {new_config}")
        self.config = new_config
        self.__init__(new_config) # Re-initialize

    def generate_response(self, history: List[ChatMessage]) -> Tuple[Optional[str], List[str]]:
        """
        Generates a response from the LLM based on the conversation history.
        Returns (text_response, list_of_ssh_commands).
        """
        if not self.client or self.config.provider != "ollama":
            return "Error: LLM Client not initialized or provider not supported yet.", []

        # Format history for Ollama API
        messages = [{'role': msg.sender if msg.sender != 'llm' else 'assistant', 'content': msg.text} for msg in history]

        # Add system prompt / instructions for SSH command format
        # This should probably be configurable or part of the initial history
        system_prompt = (
            "You are a helpful assistant with access to an SSH tool. "
            "When you need to execute a command on the connected remote system, "
            "format it EXACTLY as follows on its own line: "
            "[SSH_COMMAND] the_command_to_execute\n"
            "Do not add any explanation before or after the [SSH_COMMAND] tag on that line. "
            "You can use multiple [SSH_COMMAND] lines if needed. "
            "Provide your reasoning or other text on separate lines."
        )
        # This could be added as the first message or using the 'system' parameter if supported
        # For simplicity, let's prepend it to the messages list if it's not already there
        # A more robust approach would be needed for long conversations
        if not messages or messages[0].get('role') != 'system':
             messages.insert(0, {'role': 'system', 'content': system_prompt})


        try:
            print(f"Sending request to Ollama model {self.config.model_name}...")
            response = self.client.chat(
                model=self.config.model_name,
                messages=messages,
                stream=False # Keep it simple first, maybe add streaming later
            )

            full_response_text = response['message']['content']
            print(f"LLM Raw Response:\n{full_response_text}")

            text_parts = []
            ssh_commands = []
            lines = full_response_text.strip().split('\n')

            for line in lines:
                match = SSH_COMMAND_REGEX.fullmatch(line.strip())
                if match:
                    command = match.group(1).strip()
                    if command: # Avoid empty commands
                        ssh_commands.append(command)
                else:
                    text_parts.append(line)

            final_text_response = "\n".join(text_parts).strip()
            if not final_text_response and not ssh_commands:
                # Handle cases where the LLM might return only whitespace or nothing
                final_text_response = "[LLM returned empty response]"


            print(f"Parsed Text Response: {final_text_response}")
            print(f"Parsed SSH Commands: {ssh_commands}")
            return final_text_response, ssh_commands

        except Exception as e:
            error_msg = f"Error communicating with LLM ({self.config.provider} model {self.config.model_name}): {e}"
            print(error_msg)
            # Check if the error indicates the model is not available
            if "model not found" in str(e).lower():
                 error_msg += f"\nPlease ensure the model '{self.config.model_name}' is available in Ollama."
            return error_msg, []
