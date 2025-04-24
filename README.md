# LLM SSH Agent

**Version:** 0.1.0

## Description

LLM SSH Agent is a Python application that integrates a Large Language Model (LLM) with an SSH client. It provides a conversational interface (initially as a Terminal User Interface - TUI) allowing users to interact with an LLM (like models hosted via Ollama). Based on the conversation, the LLM can propose SSH commands to be executed on a remote system specified by the user. These commands require user approval before execution, and all SSH activity is logged separately.

The primary goal is to streamline remote system management and troubleshooting by leveraging LLM capabilities while maintaining user control and security.

## Features

*   **Chat Interface:** Converse with a configured LLM.
*   **LLM Integration:** Currently supports local Ollama models. (Extensible for API models).
*   **SSH Client:** Connect to remote systems using password or key-based authentication.
*   **Secure Profile Management:** Save SSH connection details (host, user, auth method) securely using the system's native keyring/credential store.
*   **Command Approval Workflow:** LLM suggests SSH commands (using `[SSH_COMMAND] ...` format), which must be explicitly approved by the user before execution.
*   **SSH Logging:** All executed commands and their corresponding output (stdout/stderr) are displayed in a dedicated log pane.
*   **Terminal UI:** Built using the modern Textual framework for a responsive terminal experience.

## Getting Started

### Prerequisites

*   **Python:** Version 3.9 or higher is required.
*   **Poetry:** This project uses Poetry for dependency management and packaging. Installation instructions: [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)
*   **Ollama:** You need a running Ollama instance to serve the LLM. Download and install from [https://ollama.com/](https://ollama.com/).
    *   Ensure the LLM model you intend to use (e.g., `gemma:2b`, `llama3`) is pulled: `ollama pull gemma:2b`
*   **SSH Server:** Access to an SSH server for testing the connection and command execution features.
*   **System Keyring Backend:** The `keyring` library relies on system services (like Freedesktop Secret Service on Linux, Keychain on macOS, Credential Manager on Windows). Ensure one is available and running. You might need to install packages like `gnome-keyring` or `kwallet` on Linux.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/D3fc0n3-1/LLM-SSH-interface.git
    cd llm-ssh-agent
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```
    This command creates a virtual environment and installs all necessary libraries defined in `pyproject.toml`.

### Running the Application

1.  **Activate the virtual environment (if not already active):**
    ```bash
    poetry shell
    ```

2.  **Run the Terminal User Interface (TUI):**
    ```bash
    llm-ssh-tui
    ```
    *(This uses the script defined in `pyproject.toml`)*

    Alternatively, you can run:
    ```bash
    python -m llm_ssh_agent.tui.main
    ```

## Usage

1.  **Initial Launch:** Upon first launch, the application starts with the TUI.
2.  **LLM Configuration (Implicit):** Currently, the app defaults to using Ollama with the `gemma:2b` model. If you need to change this or specify a base URL for Ollama (if not running on default `http://localhost:11434`), you'll need to modify the `LLMConfig` defaults in `llm_ssh_agent/app_state.py` for now. (Future versions should have configuration options). Ensure the selected model is available in your Ollama instance.
3.  **Connecting to SSH:**
    *   Press `Ctrl+N` (or the relevant binding shown in the footer) to open the connection management interface (Note: The connection dialog widget needs full implementation).
    *   You should be able to:
        *   Enter details for a new connection (Hostname, Port, Username, Auth Method - 'password' or 'key', Key Path if applicable).
        *   Provide a Profile Name to save the connection.
        *   Enter the password or key passphrase when prompted (it will be stored securely in your system's keyring).
        *   Select a saved profile to connect.
    *   Connection status is displayed in the status bar at the bottom.
4.  **Chatting with the LLM:**
    *   Type your messages in the input box at the bottom of the left pane and press Enter.
    *   The conversation history appears in the top-left pane. Messages are prefixed with "You:", "LLM:", or "Sys:".
5.  **SSH Command Workflow:**
    *   Instruct the LLM to perform actions on the connected SSH server. Remind it to use the `[SSH_COMMAND] your command here` format.
    *   Example prompt: `Connect to the server and tell me the contents of the home directory using [SSH_COMMAND]`
    *   If the LLM responds with a command in the correct format, it will appear in the "Pending Commands" area in the right pane.
    *   Use the buttons/keys associated with the approval pane (Note: Needs full implementation in the widget) to "Approve" or "Reject" commands.
    *   Approved commands are sent to the SSH server one by one.
    *   The command, its execution time, stdout, and stderr are displayed in the "SSH Execution Log" pane (top-right).
    *   Output from SSH commands (if enabled in `CoreLogic`) is fed back into the LLM context for subsequent turns.
6.  **Disconnecting:** Use the connection management interface (`Ctrl+N`) to disconnect.
7.  **Quitting:** Press `Ctrl+C` or `Ctrl+Q`.

## Configuration Files

*   **SSH Profiles:** Non-sensitive connection details (hostname, user, etc.) are stored in `~/.config/llm_ssh_agent/profiles.json`. **Do not edit this file manually unless you know what you are doing.**
*   **Secrets:** Passwords and key passphrases are **not** stored in the JSON file. They are managed via the `keyring` library, interacting with your operating system's credential manager (e.g., macOS Keychain, Windows Credential Manager, GNOME Keyring/KWallet).

