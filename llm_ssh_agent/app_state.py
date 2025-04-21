# File: llm_ssh_agent/app_state.py
# Type: Python Module

import paramiko
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

# --- Configuration & Connection States ---

@dataclass
class LLMConfig:
    """Configuration for the LLM backend."""
    provider: str = "ollama"  # Default to ollama
    model_name: str = "gemma:2b" # Default model, user should change as needed
    # Add fields for API keys, base URLs etc. if supporting APIs
    base_url: Optional[str] = None # For self-hosted Ollama or APIs

@dataclass
class SSHConnectionProfile:
    """Represents saved SSH connection details (secrets stored separately)."""
    profile_name: str
    hostname: str
    port: int = 22
    username: str
    auth_method: str = "key" # "key" or "password"
    key_path: Optional[str] = None

@dataclass
class SSHConnectionState:
    """Holds the active SSH connection details and client."""
    profile: SSHConnectionProfile
    client: Optional[paramiko.SSHClient] = None
    is_connected: bool = False
    error: Optional[str] = None

# --- Chat & Logging ---

@dataclass
class ChatMessage:
    """Represents a single message in the chat history."""
    sender: str # "user" or "llm" or "system"
    text: str

@dataclass
class SSHLogEntry:
    """Represents an entry in the SSH command log."""
    command: str
    output: str
    timestamp: float # Use time.time()

# --- Application State ---

@dataclass
class AppState:
    """Holds the overall state of the application."""
    current_llm_config: LLMConfig = field(default_factory=LLMConfig)
    saved_connections: Dict[str, SSHConnectionProfile] = field(default_factory=dict)
    active_connection: Optional[SSHConnectionState] = None
    conversation_history: List[ChatMessage] = field(default_factory=list)
    pending_ssh_commands: List[str] = field(default_factory=list)
    ssh_log: List[SSHLogEntry] = field(default_factory=list)
    # Flag to control whether LLM output should be added to context
    feed_ssh_output_to_llm: bool = True