# File: llm_ssh_agent/ssh_manager.py
# Type: Python Module

import paramiko
import socket
import time
from typing import Optional, Tuple
from .app_state import SSHConnectionProfile, SSHConnectionState
from .secure_storage import get_ssh_secret

# Timeout for SSH connection attempts
CONNECTION_TIMEOUT = 10 # seconds

class SSHManager:
    """Handles SSH connection and command execution."""

    def __init__(self):
        self.active_state: Optional[SSHConnectionState] = None

    def connect(self, profile: SSHConnectionProfile) -> Tuple[bool, Optional[str]]:
        """
        Establishes an SSH connection using the provided profile.
        Retrieves secrets from secure storage.
        Returns (success: bool, message: Optional[str])
        """
        self.disconnect() # Ensure any previous connection is closed

        password = None
        key_passphrase = None
        pkey = None

        if profile.auth_method == "password":
            password = get_ssh_secret(profile.profile_name, "password")
            if password is None:
                return False, f"Password not found in secure storage for profile '{profile.profile_name}'."
        elif profile.auth_method == "key":
            key_path = profile.key_path
            if not key_path:
                return False, "Key path not specified in profile."
            try:
                # Try loading key without passphrase first
                pkey = paramiko.RSAKey.from_private_key_file(key_path) # Add Ed25519 etc. as needed
            except paramiko.PasswordRequiredException:
                key_passphrase = get_ssh_secret(profile.profile_name, "key_passphrase")
                if key_passphrase is None:
                    return False, f"Key '{key_path}' requires a passphrase, but none found in secure storage for profile '{profile.profile_name}'."
                try:
                    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=key_passphrase)
                except paramiko.SSHException as e:
                    return False, f"Failed to load private key '{key_path}': {e}"
            except FileNotFoundError:
                 return False, f"Private key file not found: {key_path}"
            except paramiko.SSHException as e:
                 return False, f"Error loading private key '{key_path}': {e}"
        else:
            return False, f"Unsupported authentication method: {profile.auth_method}"

        client = paramiko.SSHClient()
        # Load known hosts from the default known_hosts file
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())  # Reject unknown host keys

        try:
            print(f"Attempting SSH connection to {profile.username}@{profile.hostname}:{profile.port}...")
            client.connect(
                hostname=profile.hostname,
                port=profile.port,
                username=profile.username,
                password=password, # Will be None if using key
                pkey=pkey,         # Will be None if using password
                timeout=CONNECTION_TIMEOUT,
                passphrase=key_passphrase # Paramiko >3.0 uses 'passphrase', older used 'password' for key passphrases too
            )
            print("SSH Connection successful.")
            self.active_state = SSHConnectionState(
                profile=profile,
                client=client,
                is_connected=True,
                error=None
            )
            return True, f"Connected to {profile.hostname}."

        except paramiko.AuthenticationException:
            error_msg = "Authentication failed (incorrect password, key, or passphrase?)."
            print(f"Error: {error_msg}")
            self.active_state = SSHConnectionState(profile=profile, error=error_msg)
            return False, error_msg
        except (paramiko.SSHException, socket.timeout, socket.error) as e:
            error_msg = f"Connection failed: {e}"
            print(f"Error: {error_msg}")
            self.active_state = SSHConnectionState(profile=profile, error=error_msg)
            return False, error_msg
        except Exception as e: # Catch unexpected errors
            error_msg = f"An unexpected error occurred during connection: {e}"
            print(f"Error: {error_msg}")
            self.active_state = SSHConnectionState(profile=profile, error=error_msg)
            return False, error_msg


    def disconnect(self):
        """Closes the active SSH connection."""
        if self.active_state and self.active_state.client:
            try:
                self.active_state.client.close()
                print(f"SSH connection to {self.active_state.profile.hostname} closed.")
            except Exception as e:
                 print(f"Error closing SSH connection: {e}") # Log this
            self.active_state.client = None
            self.active_state.is_connected = False
            # Keep profile info but mark as disconnected
            # self.active_state = None # Or just update state? Let's update.

    def execute_command(self, command: str) -> Tuple[str, str]:
        """
        Executes a command on the remote SSH server.
        Returns (stdout, stderr).
        """
        if not self.active_state or not self.active_state.is_connected or not self.active_state.client:
            return "", "Error: Not connected to SSH server."

        client = self.active_state.client
        stdout_data = ""
        stderr_data = ""
        try:
            print(f"Executing command: {command}")
            stdin, stdout, stderr = client.exec_command(command, timeout=30) # Add timeout
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_status = stdout.channel.recv_exit_status() # Check exit status
            print(f"Command finished with exit status: {exit_status}")
            if exit_status != 0 and not stderr_data:
                 # Sometimes errors aren't printed to stderr, add generic message if exit code is non-zero
                 stderr_data += f"\nCommand exited with status {exit_status}"

        except paramiko.SSHException as e:
            stderr_data = f"Error executing command: {e}"
            print(stderr_data)
            # Consider if connection is still valid after error
            # self.disconnect() maybe? Depends on the error.
        except socket.timeout:
             stderr_data = "Error: Command timed out."
             print(stderr_data)
        except Exception as e:
             stderr_data = f"An unexpected error occurred during command execution: {e}"
             print(stderr_data)


        print(f"STDOUT:\n{stdout_data}")
        print(f"STDERR:\n{stderr_data}")
        return stdout_data, stderr_data

    def get_connection_state(self) -> Optional[SSHConnectionState]:
        return self.active_state