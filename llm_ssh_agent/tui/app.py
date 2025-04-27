# File: llm_ssh_agent/tui/app.py
# Type: Python Module

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Log, Input, Button, Static, Label, ListView, ListItem
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message
from typing import List
from ..core_logic import CoreLogic
from ..app_state import ChatMessage, SSHLogEntry, SSHConnectionProfile # Import necessary states

# --- Custom Messages for App Communication ---
class CoreUpdate(Message):
    """Generic message to trigger UI refresh based on core logic state."""
    pass

class ShowModalScreen(Message):
    """Message to request showing a modal screen (e.g., connection dialog)."""
    def __init__(self, screen_name: str, data: dict = None):
        self.screen_name = screen_name
        self.data = data or {}
        super().__init__()


# --- Placeholder Widgets (Representing the complex widgets in ./widgets/) ---
class ChatPane(Static): # Inheriting from Static
    """ Placeholder for the actual chat pane widget. """
    # Ensure Static renders markup
    DEFAULT_CLASSES = "chat-pane" # Optional: Add a CSS class for styling
    # You might need to set markup=True here or when updating content.
    # Let's ensure the Static base class instance gets markup enabled.
    # We can do this when calling update or if ChatPane had an __init__

    # A simple way to ensure markup is used when updating:
    def update_chat_history(self, history: List[ChatMessage]):
        """Formats and updates the chat pane with history."""
        formatted_text = ""
        for message in history:
            # Basic formatting (adjust as needed for desired appearance)
            if message.sender == "user":
                formatted_text += f"[bold blue]User:[/][/bold blue] {message.text}\n\n"
            elif message.sender == "llm":
                formatted_text += f"[bold green]LLM:[/][/bold green] {message.text}\n\n"
            elif message.sender == "system":
                 formatted_text += f"[bold yellow]System:[/][/bold yellow] {message.text}\n\n"
            # Remove trailing newline if it's the last message
            if message != history[-1]:
                 formatted_text += "\n"


        self.update(formatted_text) # Update the Static widget's content with markup=True implicitly by using update()



# The SSHLogPane might still be okay as Log if you want raw logs without markup


class SSHLogPane(Log):
     """ Placeholder for the actual SSH log pane widget. """
     pass

class CommandApprovalPane(Container):
     """ Placeholder for the command approval widget area. """
     # This would contain ListView, Buttons etc.
     def update_commands(self, commands: list[str]):
          # Clear existing widgets and add new ones based on commands list
          pass

class ConnectionDialog(Static): # Replace with actual Screen later
     """ Placeholder for connection management dialog/screen. """
     pass

class StatusBar(Static):
     """ Placeholder for the status bar. """
     pass

# --- Main TUI Application ---

class LLMSshApp(App[None]):
    """The main Textual application."""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit App"),
        Binding("ctrl+q", "quit", "Quit App"),
        Binding("ctrl+l", "toggle_logs", "Toggle SSH Log Pane"), # Example custom binding
        Binding("ctrl+n", "connect_dialog", "New/Manage Connections"),
    ]

    CSS_PATH = "style.tcss" # We'll need a CSS file

    # Reactive variables to hold data for UI display
    chat_history: list[ChatMessage] = reactive([])
    ssh_log_entries: list[SSHLogEntry] = reactive([])
    connection_status: str = reactive("Disconnected")
    pending_commands: list[str] = reactive([])


    def __init__(self, core_logic: CoreLogic, **kwargs):
        super().__init__(**kwargs)
        self.core_logic = core_logic
        self._set_core_logic_callbacks()

    def _set_core_logic_callbacks(self):
        """Set the callbacks in CoreLogic to update the TUI."""
        self.core_logic.update_chat_callback = self.update_chat
        self.core_logic.update_ssh_log_callback = self.update_ssh_log
        self.core_logic.update_connection_status_callback = self.update_connection_status
        self.core_logic.update_pending_commands_callback = self.update_pending_commands
        self.core_logic.show_message_callback = self.show_modal_message # Needs implementation

    # --- UI Composition ---

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                Vertical(
                    ChatPane(id="chat-pane"),
                    Input(id="chat-input", placeholder="Enter your message..."),
                    id="left-pane",
                ),
                Vertical(
                    Label("SSH Execution Log", id="ssh-log-label"),
                    SSHLogPane(id="ssh-log-pane", highlight=True,),
                    Label("Pending Commands", id="pending-cmd-label"),
                    CommandApprovalPane(id="approval-pane"), # Use the placeholder
                    id="right-pane"
                ),
                id="main-container"
            )
        )
        yield StatusBar(id="status-bar") # Use the placeholder
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.query_one("#chat-input").focus()
        # Initial status update
        status_widget = self.query_one(StatusBar)
        status_widget.update(self.connection_status) # Placeholder update

    # --- Callback Implementations (called by CoreLogic) ---

    def update_chat(self, history: list[ChatMessage]):
        """Callback to update the chat display."""
        def _update():
            chat_pane = self.query_one("#chat-pane", ChatPane)
            # Call the new method to format and display the history
            chat_pane.update_chat_history(history)

            self.call_from_thread(_update) # Ensure UI updates happen on the main thread
       	    chat_pane.clear()
            for msg in history:
                prefix = "[bold blue]You:[/]" if msg.sender == "user" \
                    else "[bold magenta]LLM:[/]" if msg.sender == "llm" \
                    else "[bold yellow]Sys:[/]"
                chat_pane.write(f"{prefix} {msg.text}")
            self.chat_history = history # Update reactive var if needed elsewhere
        # Ensure UI updates happen in the app's thread
        self.call_from_thread(_update)


    def update_ssh_log(self, log_entries: list[SSHLogEntry]):
        def _update():
            log_pane = self.query_one("#ssh-log-pane", SSHLogPane)
            # Efficient update? Or just clear and rewrite for simplicity now?
            log_pane.clear()
            for entry in log_entries:
                 log_pane.write(entry.output) # output is pre-formatted
            self.ssh_log_entries = log_entries
        self.call_from_thread(_update)

    def update_connection_status(self, status: str):
        def _update():
            status_widget = self.query_one(StatusBar)
            status_widget.update(status) # Placeholder update
            self.connection_status = status
        self.call_from_thread(_update)

    def update_pending_commands(self, commands: list[str]):
         def _update():
              approval_pane = self.query_one(CommandApprovalPane)
              approval_pane.update_commands(commands) # Delegate to the widget
              self.pending_commands = commands
         self.call_from_thread(_update)

    def show_modal_message(self, title: str, message: str):
         # Implementation depends on modal dialog approach in Textual
         # Could push a new Screen or use a built-in dialog if available
         print(f"MODAL: {title} - {message}") # Simple print for now
         pass

    # --- User Interactions ---

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Called when the user presses Enter in the chat input."""
        user_input = event.value
        if user_input:
            # Clear the input
            self.query_one("#chat-input", Input).value = ""
            # Send message to core logic (which runs LLM in thread)
            self.core_logic.send_message_to_llm(user_input)

    # Add handlers for buttons in CommandApprovalPane (e.g., on_button_pressed)
    # These handlers would call core_logic.approve_commands or core_logic.reject_commands

    # Add action handlers for bindings
    def action_toggle_logs(self) -> None:
         # Example: toggle visibility of SSH log pane
         pass

    def action_connect_dialog(self) -> None:
         # Push a new screen for managing connections
         # self.push_screen(ConnectionManagementScreen(self.core_logic)) # Example
         print("ACTION: Open Connection Dialog") # Placeholder
         pass
