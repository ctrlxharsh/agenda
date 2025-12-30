import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

import streamlit as st

class EnvConfig:
    """Environment configuration manager for the application."""
    
    @staticmethod
    def _get_val(key: str, default: Optional[str] = None) -> Optional[str]:
        """Helper to get value from st.secrets or os.getenv."""
        # Check st.secrets first
        if key in st.secrets:
            return str(st.secrets[key])
        # Fallback to os.getenv
        return os.getenv(key, default)

    @staticmethod
    def get_openai_api_key() -> str:
        """
        Get OpenAI API key from secrets or environment variables.
        """
        api_key = EnvConfig._get_val("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in secrets.toml or environment variables."
            )
        return api_key.strip()
    
    @staticmethod
    def get_db_connection_string() -> Optional[str]:
        return EnvConfig._get_val("DATABASE_URL")
    
    @staticmethod
    def is_development() -> bool:
        return EnvConfig._get_val("ENVIRONMENT", "development").lower() == "development"
    
    @staticmethod
    def get_github_client_id() -> Optional[str]:
        return EnvConfig._get_val("GITHUB_CLIENT_ID")
    
    @staticmethod
    def get_github_client_secret() -> Optional[str]:
        return EnvConfig._get_val("GITHUB_CLIENT_SECRET")
        
    @staticmethod
    def get_app_url() -> str:
        """Get the base application URL (e.g. for redirects)."""
        return EnvConfig._get_val("APP_URL", "http://localhost:8501")


# Convenience functions for direct access
def get_openai_api_key() -> str:
    """Get OpenAI API key."""
    return EnvConfig.get_openai_api_key()


def get_db_connection_string() -> Optional[str]:
    """Get database connection string."""
    return EnvConfig.get_db_connection_string()
