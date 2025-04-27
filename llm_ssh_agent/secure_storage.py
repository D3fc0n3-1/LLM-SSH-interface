# File: llm_ssh_agent/secure_storage.py
# Type: Python Module

import keyring
import json
import os
from typing import Optional, Dict
from .app_state import SSHConnectionProfile

# Use a unique service name for keyring
KEYRING_SERVICE_NAME = "LLM-SSH-Agent"
CONFIG_DIR = os.path.expanduser("~/.config/llm_ssh_agent")
PROFILES_FILE = os.path.join(CONFIG_DIR, "profiles.json")

def _ensure_config_dir():
    """Ensure the configuration directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def _get_password_alias(profile_name: str) -> str:
    """Generate the keyring alias for a profile's password."""
    return f"{profile_name}_password"

def _get_key_passphrase_alias(profile_name: str) -> str:
    """Generate the keyring alias for a profile's key passphrase."""
    return f"{profile_name}_key_passphrase"

def save_ssh_profile(profile: SSHConnectionProfile, password: Optional[str] = None, key_passphrase: Optional[str] = None):
    """Saves profile details (non-secrets) to JSON and secrets to keyring."""
    _ensure_config_dir()
    profiles = load_all_ssh_profiles()
    profiles[profile.profile_name] = profile

    # Save non-secret parts to JSON
    profiles_dict = {name: p.__dict__ for name, p in profiles.items()}
    try:
        with open(PROFILES_FILE, 'w') as f:
            json.dump(profiles_dict, f, indent=4)
    except IOError as e:
        print(f"Error saving profiles file: {e}") # Replace with logging
        return # Or raise?

    # Save secrets to keyring
    try:
        if profile.auth_method == "password" and password:
            keyring.set_password(KEYRING_SERVICE_NAME, _get_password_alias(profile.profile_name), password)
            # Ensure any old key passphrase for this profile is removed
            keyring.delete_password(KEYRING_SERVICE_NAME, _get_key_passphrase_alias(profile.profile_name))
        elif profile.auth_method == "key" and key_passphrase:
            keyring.set_password(KEYRING_SERVICE_NAME, _get_key_passphrase_alias(profile.profile_name), key_passphrase)
            # Ensure any old password for this profile is removed
            keyring.delete_password(KEYRING_SERVICE_NAME, _get_password_alias(profile.profile_name))
        else:
             # Clear potentially old secrets if method changed or no secret needed now
             keyring.delete_password(KEYRING_SERVICE_NAME, _get_password_alias(profile.profile_name))
             keyring.delete_password(KEYRING_SERVICE_NAME, _get_key_passphrase_alias(profile.profile_name))

    except keyring.errors.KeyringError as e:
        print("Error interacting with keyring. Please check the keyring configuration.") # Replace with logging/user feedback

def load_all_ssh_profiles() -> Dict[str, SSHConnectionProfile]:
    """Loads all saved SSH profiles from the JSON file."""
    _ensure_config_dir()
    if not os.path.exists(PROFILES_FILE):
        return {}
    try:
        with open(PROFILES_FILE, 'r') as f:
            profiles_dict = json.load(f)
            profiles = {}
            for name, data in profiles_dict.items():
                 # Ensure profile_name is set correctly from the dict key
                 data['profile_name'] = name
                 profiles[name] = SSHConnectionProfile(**data)
            return profiles
    except (IOError, json.JSONDecodeError) as e:
        print("Error loading profiles file. Please check the file and its permissions.") # Replace with logging
        return {}

def get_ssh_secret(profile_name: str, secret_type: str) -> Optional[str]:
    """Retrieves a password or key passphrase from keyring."""
    alias = ""
    if secret_type == "password":
        alias = _get_password_alias(profile_name)
    elif secret_type == "key_passphrase":
        alias = _get_key_passphrase_alias(profile_name)
    else:
        return None # Invalid secret type

    try:
        return keyring.get_password(KEYRING_SERVICE_NAME, alias)
    except keyring.errors.KeyringError as e:
        print("Error retrieving secret from keyring. Please check the keyring configuration.") # Replace with logging
        return None

def delete_ssh_profile(profile_name: str):
    """Deletes a profile from JSON and its secrets from keyring."""
    _ensure_config_dir()
    profiles = load_all_ssh_profiles()
    if profile_name in profiles:
        del profiles[profile_name]
        # Save updated profiles back to JSON
        profiles_dict = {name: p.__dict__ for name, p in profiles.items()}
        try:
            with open(PROFILES_FILE, 'w') as f:
                json.dump(profiles_dict, f, indent=4)
        except IOError as e:
            print("Error saving profiles file after deletion. Please check the file and its permissions.")

        # Delete secrets from keyring
        try:
            keyring.delete_password(KEYRING_SERVICE_NAME, _get_password_alias(profile_name))
            keyring.delete_password(KEYRING_SERVICE_NAME, _get_key_passphrase_alias(profile_name))
        except keyring.errors.KeyringError as e:
            # Log this, but don't stop the profile deletion
            print("Could not delete secrets from keyring. Please check the keyring configuration.")