#!/usr/bin/env python3
"""
PEM Key Generation Script for 7taps API Integration

This script generates RSA key pairs for 7taps webhook authentication.
Generates both public and private keys for secure webhook communication.
"""

import os
import sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import argparse


def generate_rsa_key_pair(key_size: int = 2048) -> tuple:
    """
    Generate RSA key pair for 7taps authentication.
    
    Args:
        key_size: RSA key size in bits (default: 2048)
        
    Returns:
        Tuple of (private_key, public_key) as bytes
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem


def save_key_to_file(key_data: bytes, filename: str, key_type: str):
    """
    Save key data to file.
    
    Args:
        key_data: Key data as bytes
        filename: Output filename
        key_type: Type of key (public/private)
    """
    try:
        with open(filename, 'wb') as f:
            f.write(key_data)
        
        print(f"✅ {key_type.capitalize()} key saved to: {filename}")
        
        # Set appropriate permissions
        if key_type == "private":
            os.chmod(filename, 0o600)  # Read/write for owner only
        else:
            os.chmod(filename, 0o644)  # Read for all, write for owner
            
    except Exception as e:
        print(f"❌ Error saving {key_type} key: {e}")
        sys.exit(1)


def generate_environment_vars(private_key_path: str, public_key_path: str):
    """
    Generate environment variable configuration.
    
    Args:
        private_key_path: Path to private key file
        public_key_path: Path to public key file
    """
    env_config = f"""
# 7taps API Integration Environment Variables
# Generated on: {datetime.now().isoformat()}

# PEM Key Paths
SEVENTAPS_PRIVATE_KEY_PATH={private_key_path}
SEVENTAPS_PUBLIC_KEY_PATH={public_key_path}

# 7taps API Configuration
SEVENTAPS_WEBHOOK_SECRET=your_webhook_secret_here
SEVENTAPS_API_BASE_URL=https://api.7taps.com
SEVENTAPS_WEBHOOK_ENDPOINT=/api/7taps/webhook

# Authentication Settings
SEVENTAPS_AUTH_ENABLED=true
SEVENTAPS_VERIFY_SIGNATURE=true
"""
    
    env_file = ".env.7taps"
    try:
        with open(env_file, 'w') as f:
            f.write(env_config)
        print(f"✅ Environment configuration saved to: {env_file}")
    except Exception as e:
        print(f"❌ Error saving environment config: {e}")


def main():
    """Main function for PEM key generation."""
    parser = argparse.ArgumentParser(
        description="Generate PEM keys for 7taps API integration"
    )
    parser.add_argument(
        "--key-size", 
        type=int, 
        default=2048,
        help="RSA key size in bits (default: 2048)"
    )
    parser.add_argument(
        "--output-dir", 
        default="keys",
        help="Output directory for keys (default: keys)"
    )
    parser.add_argument(
        "--private-key-name",
        default="7taps_private_key.pem",
        help="Private key filename (default: 7taps_private_key.pem)"
    )
    parser.add_argument(
        "--public-key-name",
        default="7taps_public_key.pem",
        help="Public key filename (default: 7taps_public_key.pem)"
    )
    parser.add_argument(
        "--generate-env",
        action="store_true",
        help="Generate environment configuration file"
    )
    
    args = parser.parse_args()
    
    print("🔐 7taps PEM Key Generation")
    print("=" * 40)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate key pair
    print(f"Generating RSA key pair ({args.key_size} bits)...")
    private_pem, public_pem = generate_rsa_key_pair(args.key_size)
    
    # Save keys
    private_key_path = os.path.join(args.output_dir, args.private_key_name)
    public_key_path = os.path.join(args.output_dir, args.public_key_name)
    
    save_key_to_file(private_pem, private_key_path, "private")
    save_key_to_file(public_pem, public_key_path, "public")
    
    # Generate environment config if requested
    if args.generate_env:
        generate_environment_vars(private_key_path, public_key_path)
    
    # Display key information
    print("\n📋 Key Information:")
    print(f"Private Key: {private_key_path}")
    print(f"Public Key: {public_key_path}")
    print(f"Key Size: {args.key_size} bits")
    print(f"Generated: {datetime.now().isoformat()}")
    
    print("\n🔧 Next Steps:")
    print("1. Add private key path to environment variables")
    print("2. Share public key with 7taps for webhook authentication")
    print("3. Configure webhook endpoint in 7taps dashboard")
    print("4. Test webhook authentication")
    
    print("\n✅ Key generation complete!")


if __name__ == "__main__":
    main() 