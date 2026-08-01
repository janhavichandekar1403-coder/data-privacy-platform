"""
anonymizer.py
-------------
Implements the four privacy-protection techniques described
in the project proposal:

1. Masking      - hides part of the value, keeps some visible
2. Hashing      - one-way SHA-256 transform (irreversible)
3. Encryption   - reversible, needs a secret key (Fernet / AES)
4. Tokenization - replaces value with a fake token, stores the
                  real value in a separate mapping table
"""

import hashlib
from cryptography.fernet import Fernet


# ---------------- MASKING ----------------
def mask_value(value: str) -> str:
    value = str(value)
    if "@" in value:  # looks like an email
        name, domain = value.split("@", 1)
        visible = name[0] if name else "*"
        return f"{visible}***@{domain}"
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


# ---------------- HASHING ----------------
def hash_value(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


# ---------------- ENCRYPTION ----------------
def generate_encryption_key() -> bytes:
    """Call this once and store the key securely (e.g. in a .env file)."""
    return Fernet.generate_key()


def encrypt_value(value: str, key: bytes) -> str:
    f = Fernet(key)
    token = f.encrypt(str(value).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(token: str, key: bytes) -> str:
    f = Fernet(key)
    return f.decrypt(token.encode("utf-8")).decode("utf-8")


# ---------------- TOKENIZATION ----------------
class Tokenizer:
    """
    Keeps an in-memory mapping of original value -> token for one
    anonymization run. In a production system this mapping table
    would be stored securely in a database, not in memory.
    """

    def __init__(self, prefix="USER"):
        self.prefix = prefix
        self.counter = 1000
        self.value_to_token = {}
        self.mapping_table = []  # for the compliance report / audit log

    def tokenize(self, value: str) -> str:
        value = str(value)
        if value in self.value_to_token:
            return self.value_to_token[value]

        self.counter += 1
        token = f"{self.prefix}_{self.counter}"
        self.value_to_token[value] = token
        self.mapping_table.append({"original": value, "token": token})
        return token


# ---------------- DISPATCH ----------------
def apply_method(value, method: str, key: bytes = None, tokenizer: Tokenizer = None):
    """
    Central function used by app.py to apply whichever method
    the user picked for a given column.
    """
    if value is None or str(value).strip() == "":
        return value

    if method == "mask":
        return mask_value(value)
    if method == "hash":
        return hash_value(value)
    if method == "encrypt":
        if key is None:
            raise ValueError("Encryption key required for 'encrypt' method")
        return encrypt_value(value, key)
    if method == "tokenize":
        if tokenizer is None:
            raise ValueError("Tokenizer instance required for 'tokenize' method")
        return tokenizer.tokenize(value)
    if method == "skip":
        return value

    raise ValueError(f"Unknown anonymization method: {method}")
