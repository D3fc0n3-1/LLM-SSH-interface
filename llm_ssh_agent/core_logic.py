# File: llm_ssh_agent/core_logic.py
# Type: Python Module

import time
import threading
from typing import Optional, Callable, List, Tuple

from .app_state import AppState, ChatMessage, SSHLogEntry, SSHConnectionProfile, LLMConfig
from .llm_interface import LLMInterface
from .ssh_manager import SSHManager
from .secure_storage import save_ssh_profile, load_all_ssh_profiles, delete_ssh_profile, get_ssh_secret
from .utils import format_ssh_log

class CoreLogic:
    """
    Orchestrates the application's logic, managing state and interactions
    between UI, LLM, and SSH components.
    """
    def __init__(self):
        self.state = AppState()
        self.ssh_manager = SSHManager()
        # Initialize LLM Interface with default config from state
        self.llm_interface = LLMInterface(self.state.current_llm_config)
        self.state.saved_connections = load_all_ssh_profiles()

        # --- Callbacks for UI updates ---
        # These should be set by the UI layer (TUI/GUI)
        self.update_chat_callback: Optional[Callable[[List[ChatMessage]], None]] = None
        self.update_ssh_log_callback: Optional[Callable[[List[SSHLogEntry]], None]] = None
        self.update_connection_status_callback: Optional[Callable[[str], None]] = None
        self.update_pending_commands_callback: Optional[Callable[[List[str]], None]] = None
        self.show_message_callback: Optional[Callable[[str, str], None]] = None # (title, message)

    def _notify_ui(self, callback: Optional[Callable], *args, **kwargs):
        """Helper to safely call UI update callbacks."""
        if callback:
            try:
                # If using Textual, ensure calls are thread-safe
                # This might need refinement depending on how Textual App is structured
                # For now, assuming direct call is okay or UI handles threading
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Error in UI callback {callback.__name__}: {e}")

    def _add_system_message(self, text: str):
        """Adds a message from the 'system' to the chat."""
        message = ChatMessage(sender="system", text=text)
        self.state.conversation_history.append(message)
        self._notify_ui(self.update_chat_callback, self.state.conversation_history)

    def _add_ssh_log_entry(self, command: str, stdout: str, stderr: str):
        """Adds an entry to the SSH log and notifies the UI."""
        log_output = format_ssh_log(command, stdout, stderr)
        entry = SSHLogEntry(command=command, output=log_output, timestamp=time.time())
        self.state.ssh_log.append(entry)
        self._notify_ui(self.update_ssh_log_callback, self.state.ssh_log)

        # Optionally feed back to LLM context
        if self.state.feed_ssh_output_to_llm and (stdout or stderr):
             feedback = f"[SSH_OUTPUT for '{command}']\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
             # Add as a system message or special role? Let's use system for now.
             # Limit length?
             feedback_message = ChatMessage(sender="system", text=feedback)
             self.state.conversation_history.append(feedback_message)
             # Don't necessarily update chat UI with this internal message unless desired
             # self._notify_ui(self.update_chat_callback, self.state.conversation_history)


    # --- Connection Management ---

    def get_saved_connections(self) -> List[str]:
        """Returns a list of saved profile names."""
        return list(self.state.saved_connections.keys())

    def connect_ssh(self, profile_name: str):
        """Initiates an SSH connection using a saved profile."""
        if profile_name not in self.state.saved_connections:
            self._notify_ui(self.update_connection_status_callback, f"Error: Profile '{profile_name}' not found.")
            return

        profile = self.state.saved_connections[profile_name]
        self._notify_ui(self.update_connection_status_callback, f"Connecting to {profile.hostname}...")

        # Run connection in a separate thread to avoid blocking UI
        threading.Thread(target=self._connect_ssh_thread, args=(profile,), daemon=True).start()

    def _connect_ssh_thread(self, profile: SSHConnectionProfile):
        """Background thread function for SSH connection."""
        success, message = self.ssh_manager.connect(profile)
        self.state.active_connection = self.ssh_manager.get_connection_state() # Update state
        self._notify_ui(self.update_connection_status_callback, message)
        if success:
            self._add_system_message(f"SSH connection established to {profile.hostname}.")
        else:
             self._add_system_message(f"SSH connection failed: {message}")


    def disconnect_ssh(self):
        """Disconnects the current SSH session."""
        if self.state.active_connection and self.state.active_connection.is_connected:
            hostname = self.state.active_connection.profile.hostname
            self.ssh_manager.disconnect()
            self.state.active_connection = self.ssh_manager.get_connection_state() # Update state
            status_msg = f"Disconnected from {hostname}."
            self._notify_ui(self.update_connection_status_callback, status_msg)
            self._add_system_message("SSH connection closed.")
        else:
            self._notify_ui(self.update_connection_status_callback, "Not connected.")

    def save_new_connection(self, profile: SSHConnectionProfile, password: Optional[str] = None, key_passphrase: Optional[str] = None):
        """Saves a new connection profile."""
        save_ssh_profile(profile, password, key_passphrase)
        self.state.saved_connections = load_all_ssh_profiles() # Reload state
        self._notify_ui(self.show_message_callback, "Profile Saved", f"Profile '{profile.profile_name}' saved successfully.")
        # Maybe automatically connect after saving? For now, just save.


    def delete_connection_profile(self, profile_name: str):
         """Deletes a saved connection profile."""
         if self.state.active_connection and self.state.active_connection.profile.profile_name == profile_name:
              self.disconnect_ssh() # Disconnect if deleting the active profile

         delete_ssh_profile(profile_name)
         self.state.saved_connections = load_all_ssh_profiles() # Reload state
         self._notify_ui(self.show_message_callback, "Profile Deleted", f"Profile '{profile_name}' deleted.")


    # --- Chat and Command Execution ---

    def send_message_to_llm(self, user_message: str):
        """Sends a user message to the LLM and processes the response."""
        if not user_message.strip():
            return

        # Add user message to history
        self.state.conversation_history.append(ChatMessage(sender="user", text=user_message))
        self._notify_ui(self.update_chat_callback, self.state.conversation_history)

        # Add placeholder for LLM response
        thinking_message = ChatMessage(sender="llm", text="Thinking...")
        self.state.conversation_history.append(thinking_message)
        self._notify_ui(self.update_chat_callback, self.state.conversation_history)

        # Run LLM generation in a separate thread
        threading.Thread(target=self._generate_llm_response_thread, daemon=True).start()

    def _generate_llm_response_thread(self):
        """Background thread function for LLM response generation."""
        # Pass relevant history (maybe limit length later)
        # Exclude the "Thinking..." message
        history_to_send = self.state.conversation_history[:-1]
        text_response, ssh_commands = self.llm_interface.generate_response(history_to_send)

        # Update the placeholder message with the actual response
        self.state.conversation_history[-1].text = text_response if text_response else "[LLM provided no text response]"
        self._notify_ui(self.update_chat_callback, self.state.conversation_history)

        # Handle detected SSH commands
        if ssh_commands:
            self.state.pending_ssh_commands.extend(ssh_commands)
            self._notify_ui(self.update_pending_commands_callback, self.state.pending_ssh_commands)
            # Optionally add a system message about pending commands
            self._add_system_message(f"LLM proposed {len(ssh_commands)} command(s) for execution (awaiting approval).")


    def approve_commands(self, commands_to_execute: List[str]):
        """Executes a list of approved commands."""
        if not self.state.active_connection or not self.state.active_connection.is_connected:
            self._add_system_message("Cannot execute commands: Not connected via SSH.")
            self._notify_ui(self.show_message_callback, "Execution Error", "Not connected via SSH.")
            # Clear the commands that couldn't be run
            self.state.pending_ssh_commands = [cmd for cmd in self.state.pending_ssh_commands if cmd not in commands_to_execute]
            self._notify_ui(self.update_pending_commands_callback, self.state.pending_ssh_commands)
            return

        # Run execution in a thread to avoid blocking
        threading.Thread(target=self._execute_commands_thread, args=(commands_to_execute,), daemon=True).start()

    def _execute_commands_thread(self, commands: List[str]):
        """Background thread to execute approved SSH commands sequentially."""
        executed_count = 0
        for command in commands:
            # Check connection again before each command (it might drop)
            if not self.state.active_connection or not self.state.active_connection.is_connected:
                 self._add_system_message(f"SSH connection lost. Stopping execution at command: {command}")
                 # Remove remaining commands (including current one) from pending
                 try:
                     idx = self.state.pending_ssh_commands.index(command)
                     self.state.pending_ssh_commands = self.state.pending_ssh_commands[:idx]
                 except ValueError: # Should not happen if logic is correct
                      pass
                 self._notify_ui(self.update_pending_commands_callback, self.state.pending_ssh_commands)
                 break # Stop executing this batch

            self._add_system_message(f"Executing approved command: {command}")
            stdout, stderr = self.ssh_manager.execute_command(command)
            self._add_ssh_log_entry(command, stdout, stderr) # This also feeds back to LLM if enabled

            # Remove the executed command from the pending list
            try:
                self.state.pending_ssh_commands.remove(command)
                executed_count += 1
            except ValueError:
                print(f"Warning: Command '{command}' was executed but not found in pending list.") # Log this anomaly

            # Update UI progressively
            self._notify_ui(self.update_pending_commands_callback, self.state.pending_ssh_commands)
            time.sleep(0.1) # Small delay between commands

        self._add_system_message(f"Finished executing batch of {executed_count} command(s).")


    def reject_commands(self, commands_to_reject: List[str]):
        """Removes commands from the pending list without execution."""
        rejected_count = 0
        for command in commands_to_reject:
             try:
                  self.state.pending_ssh_commands.remove(command)
                  rejected_count += 1
             except ValueError:
                  pass # Command might have already been removed/approved
        if rejected_count > 0:
            self._add_system_message(f"Rejected {rejected_count} command(s).")
            self._notify_ui(self.update_pending_commands_callback, self.state.pending_ssh_commands)

    # --- Configuration ---
    def update_llm_settings(self, new_config: LLMConfig):
         """Updates the LLM configuration."""
         self.state.current_llm_config = new_config
         self.llm_interface.update_config(new_config) # Re-init LLM client if needed
         self._add_system_message(f"LLM settings updated. Provider: {new_config.provider}, Model: {new_config.model_name}")
         # Persist config? Need config.py module for that.
