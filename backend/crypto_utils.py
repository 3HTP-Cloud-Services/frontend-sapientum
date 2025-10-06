import os
import base64
from cryptography.fernet import Fernet

def generate_encryption_key():
    return Fernet.generate_key().decode('utf-8')

def encrypt_triplet(catalog_id, file_id, version_id, key):
    triplet = f"{catalog_id}-{file_id}-{version_id}"
    fernet = Fernet(key.encode('utf-8'))
    encrypted = fernet.encrypt(triplet.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')

def decrypt_triplet(encrypted_triplet, key):
    try:
        fernet = Fernet(key.encode('utf-8'))
        decoded = base64.urlsafe_b64decode(encrypted_triplet.encode('utf-8'))
        decrypted = fernet.decrypt(decoded).decode('utf-8')
        parts = decrypted.split('-')
        if len(parts) != 3:
            return None, None, None
        return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception as e:
        print(f"Error decrypting triplet: {e}")
        return None, None, None
