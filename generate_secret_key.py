#!/usr/bin/env python3
"""
Secret Key Generator for Flask Applications
Generates cryptographically secure secret keys for production use.
"""

import secrets
import string

def generate_secret_key(length=64):
    """Generate a cryptographically secure secret key"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=32):
    """Generate a hex-based secret key"""
    return secrets.token_hex(length)

def main():
    print("🔐 Flask Secret Key Generator")
    print("=" * 40)
    
    print("\n1. Standard Secret Key (64 characters):")
    print(f"   {generate_secret_key(64)}")
    
    print("\n2. Hex Secret Key (64 characters):")
    print(f"   {generate_hex_key(32)}")
    
    print("\n3. Ultra-Secure Key (128 characters):")
    print(f"   {generate_secret_key(128)}")
    
    print("\n💡 Usage:")
    print("   Copy one of the above keys to your .env file:")
    print("   SECRET_KEY=<paste_key_here>")
    
    print("\n🚨 Security Notes:")
    print("   - Never share or commit secret keys")
    print("   - Use different keys for different environments")
    print("   - Regenerate keys if compromised")

if __name__ == "__main__":
    main()