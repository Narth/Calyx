"""Cryptographic operations for Calyx Mail: ed25519 signing and x25519 sealed box encryption."""

from __future__ import annotations

import base64
import hashlib
from typing import TypedDict

try:
    import nacl.signing
    import nacl.public
    import nacl.utils
    from nacl.exceptions import CryptoError
except ImportError:
    raise ImportError(
        "PyNaCl is required for Calyx Mail. Install with: pip install pynacl"
    )


class KeyPair(TypedDict):
    """Key pair structure."""
    private: bytes
    public: bytes


class Identity(TypedDict):
    """Complete identity with signing and encryption keypairs."""
    signing_keypair: KeyPair
    encryption_keypair: KeyPair
    fingerprints: dict[str, str]


def compute_fingerprint(public_key: bytes) -> str:
    """
    Compute fingerprint from public key.
    
    Algorithm: SHA256(public_key)[:16], base64-encoded (no padding).
    
    Args:
        public_key: 32-byte public key (ed25519 or x25519)
        
    Returns:
        Base64-encoded fingerprint (22 chars, no padding)
    """
    hash_obj = hashlib.sha256(public_key)
    fingerprint_bytes = hash_obj.digest()[:16]
    fingerprint = base64.b64encode(fingerprint_bytes).decode('ascii').rstrip('=')
    return fingerprint


def generate_identity() -> Identity:
    """
    Generate a new identity with signing (ed25519) and encryption (x25519) keypairs.
    
    Returns:
        Identity dict with signing_keypair, encryption_keypair, and fingerprints
    """
    # Generate ed25519 signing keypair
    signing_key = nacl.signing.SigningKey.generate()
    signing_private = bytes(signing_key)
    signing_public = bytes(signing_key.verify_key)
    
    # Generate x25519 encryption keypair
    encryption_private_key = nacl.public.PrivateKey.generate()
    encryption_private = bytes(encryption_private_key)
    encryption_public = bytes(encryption_private_key.public_key)
    
    # Compute fingerprints
    signing_fp = compute_fingerprint(signing_public)
    encryption_fp = compute_fingerprint(encryption_public)
    
    return {
        "signing_keypair": {
            "private": signing_private,
            "public": signing_public,
        },
        "encryption_keypair": {
            "private": encryption_private,
            "public": encryption_public,
        },
        "fingerprints": {
            "signing": signing_fp,
            "encryption": encryption_fp,
        },
    }


def sign(payload: bytes, sender_ed25519_priv: bytes) -> bytes:
    """
    Sign payload with ed25519 private key.
    
    Args:
        payload: Bytes to sign (canonical JSON)
        sender_ed25519_priv: 32-byte ed25519 private key
        
    Returns:
        64-byte ed25519 signature
    """
    signing_key = nacl.signing.SigningKey(sender_ed25519_priv)
    signature = signing_key.sign(payload).signature
    return bytes(signature)


def verify(payload: bytes, sig: bytes, sender_ed25519_pub: bytes) -> bool:
    """
    Verify ed25519 signature.
    
    Args:
        payload: Original bytes (canonical JSON)
        sig: 64-byte ed25519 signature
        sender_ed25519_pub: 32-byte ed25519 public key
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        verify_key = nacl.signing.VerifyKey(sender_ed25519_pub)
        verify_key.verify(payload, sig)
        return True
    except (CryptoError, ValueError):
        return False


def seal_to_recipient(plaintext: bytes, recipient_x25519_pub: bytes) -> bytes:
    """
    Encrypt plaintext using x25519 sealed box (recipient's public key).
    
    Uses NaCl sealed box: ephemeral keypair + ECDH + ChaCha20Poly1305.
    
    Args:
        plaintext: Bytes to encrypt
        recipient_x25519_pub: 32-byte x25519 public key
        
    Returns:
        Sealed box ciphertext (ephemeral_pub + nonce + ciphertext + tag)
    """
    recipient_key = nacl.public.PublicKey(recipient_x25519_pub)
    box = nacl.public.SealedBox(recipient_key)
    ciphertext = box.encrypt(plaintext)
    return bytes(ciphertext)


def open_from_sender(ciphertext: bytes, recipient_x25519_priv: bytes) -> bytes:
    """
    Decrypt sealed box ciphertext using recipient's private key.
    
    Args:
        ciphertext: Sealed box ciphertext (from seal_to_recipient)
        recipient_x25519_priv: 32-byte x25519 private key
        
    Returns:
        Decrypted plaintext bytes
        
    Raises:
        DecryptionError: If decryption fails (wrong key, tampered ciphertext)
    """
    try:
        recipient_key = nacl.public.PrivateKey(recipient_x25519_priv)
        box = nacl.public.SealedBox(recipient_key)
        plaintext = box.decrypt(ciphertext)
        return bytes(plaintext)
    except CryptoError as e:
        raise DecryptionError(f"Decryption failed: {e}") from e


class DecryptionError(Exception):
    """Raised when decryption fails."""
    pass
