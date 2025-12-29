import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class EnvConfig:
    """Environment configuration manager for the application."""
    
    @staticmethod
    def get_openai_api_key() -> str:
        """
        Get OpenAI API key from environment variables.
        
        Returns:
            str: OpenAI API key
            
        Raises:
            ValueError: If OPENAI_API_KEY is not set
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please add it to your .env file."
            )
        return api_key.strip()
    
    @staticmethod
    def get_db_connection_string() -> Optional[str]:
        """
        Get database connection string from environment variables.
        
        Returns:
            Optional[str]: Database connection string if set, None otherwise
        """
        return os.getenv("DATABASE_URL")
    
    @staticmethod
    def is_development() -> bool:
        """
        Check if running in development mode.
        
        Returns:
            bool: True if in development mode
        """
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @staticmethod
    def get_github_client_id() -> Optional[str]:
        """
        Get GitHub OAuth Client ID from environment variables.
        
        Returns:
            Optional[str]: GitHub Client ID if set, None otherwise
        """
        return os.getenv("GITHUB_CLIENT_ID")
    
    @staticmethod
    def get_github_client_secret() -> Optional[str]:
        """
        Get GitHub OAuth Client Secret from environment variables.
        
        Returns:
            Optional[str]: GitHub Client Secret if set, None otherwise
        """
        return os.getenv("GITHUB_CLIENT_SECRET")


# Convenience functions for direct access
def get_openai_api_key() -> str:
    """Get OpenAI API key."""
    return EnvConfig.get_openai_api_key()


def get_db_connection_string() -> Optional[str]:
    """Get database connection string."""
    return EnvConfig.get_db_connection_string()
