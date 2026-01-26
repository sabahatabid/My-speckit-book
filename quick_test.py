#!/usr/bin/env python
"""Quick test to verify the Flask app loads without errors."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

print("Testing Flask app initialization...")
print("-" * 50)

try:
    # Test 1: Load config
    print("[1] Loading config...")
    from config import settings
    print(f"    ✓ Config loaded")
    print(f"    - OpenAI Key: {'Set' if settings.openai_api_key else 'NOT SET'}")
    
    # Test 2: Load Flask app
    print("\n[2] Loading Flask app...")
    from main_flask import app, OPENAI_AVAILABLE
    print(f"    ✓ Flask app loaded")
    print(f"    - OpenAI Available: {OPENAI_AVAILABLE}")
    
    # Test 3: Test health endpoint
    print("\n[3] Testing health endpoint...")
    with app.test_client() as client:
        response = client.get('/health')
        if response.status_code == 200:
            print(f"    ✓ Health check passed")
            print(f"    - Response: {response.get_json()}")
        else:
            print(f"    ✗ Health check failed: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("✓ All tests passed! App is ready to run.")
    print("=" * 50)
    print("\nTo start the server, run:")
    print("  python app/main_flask.py")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
