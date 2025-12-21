# app/utils/auth.py
import hashlib
import hmac
import os

def encrypt_user(email: str) -> str:
    """
    Create a deterministic 64-character hash using HMAC-SHA256.
    Returns exactly 64 hex characters.
    """
    try:
        # Validate that encryption key exists
        encryption_key = os.environ.get('ENCRYPTION_SECRET_KEY')
        if not encryption_key:
            raise ValueError('ENCRYPTION_SECRET_KEY environment variable is not set')
        
        # Create a deterministic 64-character hash
        # Use HMAC-SHA256 which produces 32 bytes = 64 hex characters
        text = email.strip().lower()
        hash_obj = hmac.new(
            encryption_key.encode('utf-8'),
            text.encode('utf-8'),
            hashlib.sha256
        )
        hash_value = hash_obj.hexdigest()
        
        # Return exactly 64 characters
        return hash_value
    except Exception as error:
        print(f'Encryption error: {error}')
        raise ValueError('Encryption failed')