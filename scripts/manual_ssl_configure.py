#!/usr/bin/env python3
"""
Manual SSL Configuration Guide for SQLPad
"""
import webbrowser
import time

def main():
    print("🔧 Manual SSL Configuration for SQLPad")
    print("=" * 50)
    print()
    print("The automatic configuration created the connection, but SSL settings")
    print("need to be configured manually in SQLPad's web interface.")
    print()
    
    # Open SQLPad in browser
    sqlpad_url = "http://localhost:3000"
    print(f"🌐 Opening SQLPad: {sqlpad_url}")
    webbrowser.open(sqlpad_url)
    
    print()
    print("📋 Follow these steps:")
    print()
    print("1. Login with: admin@7taps.com / admin123")
    print()
    print("2. Click on 'Connections' in the left sidebar")
    print()
    print("3. Click on '7taps Analytics Database' connection")
    print()
    print("4. In the connection settings, find the 'SSL' section")
    print()
    print("5. Configure these SSL settings:")
    print("   ✅ Check 'Use SSL'")
    print("   🔧 SSL Mode: Select 'require' (NOT 'verify-full' or 'verify-ca')")
    print("   ⚠️  If you see 'SSL Certificate Verification', disable it")
    print()
    print("6. Click 'Test Connection' to verify it works")
    print()
    print("7. Click 'Save' to update the connection")
    print()
    print("🔍 Alternative SSL Configuration:")
    print("If the above doesn't work, try these settings:")
    print("   - SSL Mode: 'prefer'")
    print("   - Or SSL Mode: 'allow'")
    print()
    print("💡 The key is to use SSL but NOT verify the certificate,")
    print("   which bypasses the 'unable to get local issuer certificate' error.")
    print()
    
    input("Press Enter when you've completed the SSL configuration...")
    
    print()
    print("🧪 Testing the connection...")
    print("Try running this query in SQLPad:")
    print()
    print("SELECT COUNT(*) as total_users FROM users;")
    print()
    print("If it works, you should see a number (like 1234)")
    print("If it fails, the SSL settings need adjustment.")
    print()
    print("🎉 Once working, you can access your analytics data!")

if __name__ == "__main__":
    main()
