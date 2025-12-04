"""Tests for cryptographic functions."""

import pytest
import base64
from pathlib import Path
import tempfile

from libs.core.crypto import (
    generate_keypair, save_keypair, load_keypair,
    sign_data, verify_signature, generate_enrollment_token
)

class TestCrypto:
    """Test cryptographic operations."""
    
    def test_generate_keypair(self):
        """Test keypair generation."""
        private_key, public_key = generate_keypair()
        
        assert private_key is not None
        assert public_key is not None
        assert len(base64.b64decode(private_key)) > 0
        assert len(base64.b64decode(public_key)) > 0
    
    def test_save_load_keypair(self):
        """Test saving and loading keypair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            keys_dir = Path(tmpdir)
            private_key, public_key = generate_keypair()
            
            # Save keypair
            save_keypair(private_key, public_key, keys_dir, "test")
            
            # Load keypair
            loaded_private, loaded_public = load_keypair(keys_dir, "test")
            
            assert loaded_private == private_key
            assert loaded_public == public_key
    
    def test_sign_verify(self):
        """Test signing and verification."""
        private_key, public_key = generate_keypair()
        data = b"Test message to sign"
        
        # Sign data
        signature = sign_data(data, private_key)
        assert signature is not None
        
        # Verify signature
        assert verify_signature(data, signature, public_key) is True
        
        # Verify with wrong data
        assert verify_signature(b"Different message", signature, public_key) is False
        
        # Verify with wrong key
        _, wrong_public = generate_keypair()
        assert verify_signature(data, signature, wrong_public) is False
    
    def test_enrollment_token(self):
        """Test enrollment token generation."""
        token = generate_enrollment_token()
        
        assert token is not None
        assert len(token) == 19  # XXXX-XXXX-XXXX-XXXX format
        assert token.count("-") == 3
