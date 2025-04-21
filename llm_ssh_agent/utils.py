# File: llm_ssh_agent/utils.py
# Type: Python Module

import time

def format_ssh_log(command: str, stdout: str, stderr: str) -> str:
    """Formats command, stdout, and stderr for display in the log."""
    log_entry = f"--- CMD: {command} ({time.strftime('%H:%M:%S')}) ---\n"
    if stdout:
        log_entry += f"{stdout.strip()}\n"
    if stderr:
        log_entry += f"--- ERR ---\n{stderr.strip()}\n"
    log_entry += "------------------------------------\n"
    return log_entry