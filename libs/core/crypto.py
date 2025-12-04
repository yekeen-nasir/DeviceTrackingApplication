"""Cryptographic utilities for Tracker system."""

import base64
import secrets
from pathlib import Path
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

def generate_keypair() -> Tuple[bytes, bytes]:
    """
    Generate an ed25519 keypair.
    
    Returns:
        Tuple of (private_key_bytes, public_key_bytes) in base64
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return (
        base64.b64encode(private_bytes).decode('utf-8'),
        base64.b64encode(public_bytes).decode('utf-8')
    )

def save_keypair(
    private_key: bytes,
    public_key: bytes,
    keys_dir: Path,
    key_name: str = "device"
) -> None:
    """
    Save keypair to files with restrictive permissions.
    
    Args:
        private_key: Base64 encoded private key
        public_key: Base64 encoded public key
        keys_dir: Directory to save keys
        key_name: Base name for key files
    """
    keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    private_path = keys_dir / f"{key_name}_private.pem"
    public_path = keys_dir / f"{key_name}_public.pem"
    
    # Write with restrictive permissions
    import os
    
    with open(private_path, "wb") as f:
        os.chmod(private_path, 0o600)
        f.write(base64.b64decode(private_key))
    
    with open(public_path, "wb") as f:
        os.chmod(public_path, 0o644)
        f.write(base64.b64decode(public_key))

def load_keypair(
    keys_dir: Path,
    key_name: str = "device"
) -> Tuple[Optional[bytes], Optional[bytes]]:
    """
    Load keypair from files.
    
    Returns:
        Tuple of (private_key_bytes, public_key_bytes) in base64, or None if not found
    """
    private_path = keys_dir / f"{key_name}_private.pem"
    public_path = keys_dir / f"{key_name}_public.pem"
    
    private_key = None
    public_key = None
    
    if private_path.exists():
        with open(private_path, "rb") as f:
            private_key = base64.b64encode(f.read()).decode('utf-8')
    
    if public_path.exists():
        with open(public_path, "rb") as f:
            public_key = base64.b64encode(f.read()).decode('utf-8')
    
    return private_key, public_key

def sign_data(data: bytes, private_key_b64: str) -> str:
    """
    Sign data with ed25519 private key.
    
    Args:
        data: Data to sign
        private_key_b64: Base64 encoded private key
    
    Returns:
        Base64 encoded signature
    """
    private_key_bytes = base64.b64decode(private_key_b64)
    private_key = serialization.load_pem_private_key(
        private_key_bytes,
        password=None,
        backend=default_backend()
    )
    
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ValueError("Invalid key type, expected Ed25519")
    
    signature = private_key.sign(data)
    return base64.b64encode(signature).decode('utf-8')

def verify_signature(data: bytes, signature_b64: str, public_key_b64: str) -> bool:
    """
    Verify ed25519 signature.
    
    Args:
        data: Original data
        signature_b64: Base64 encoded signature
        public_key_b64: Base64 encoded public key
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        public_key_bytes = base64.b64decode(public_key_b64)
        public_key = serialization.load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )
        
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            return False
        
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, data)
        return True
    except (InvalidSignature, Exception):
        return False

def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)

def generate_enrollment_token() -> str:
    """Generate a one-time enrollment token."""
    # Format: XXXX-XXXX-XXXX-XXXX for readability
    token = secrets.token_hex(8).upper()
    return f"{token[:4]}-{token[4:8]}-{token[8:12]}-{token[12:16]}"
