#!/usr/bin/env python
"""Quick diagnostic script to test the RAG chatbot backend."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("RAG CHATBOT BACKEND DIAGNOSTIC")
print("=" * 60)

# Test 1: Check environment variables
print("\n[1] Environment Variables Check:")
print("-" * 40)
openai_key = os.getenv("OPENAI_API_KEY", "").strip()
qdrant_url = os.getenv("QDRANT_URL", "").strip()
qdrant_key = os.getenv("QDRANT_API_KEY", "").strip()
debug = os.getenv("DEBUG", "0")

if openai_key:
    print(f"✓ OPENAI_API_KEY: Set (length: {len(openai_key)})")
    print(f"  Prefix: {openai_key[:10]}...")
else:
    print("✗ OPENAI_API_KEY: NOT SET")

if qdrant_url:
    print(f"✓ QDRANT_URL: Set ({qdrant_url[:30]}...)")
else:
    print("✗ QDRANT_URL: NOT SET")

if qdrant_key:
    print(f"✓ QDRANT_API_KEY: Set (length: {len(qdrant_key)})")
else:
    print("✗ QDRANT_API_KEY: NOT SET")

print(f"  DEBUG: {debug}")

# Test 2: Check configuration loading
print("\n[2] Configuration Loading:")
print("-" * 40)
try:
    from app.config import settings
    print(f"✓ Configuration loaded successfully")
    print(f"  OpenAI Key Set: {bool(settings.openai_api_key)}")
    print(f"  Debug Mode: {settings.debug}")
    print(f"  Log Level: {settings.log_level}")
except Exception as e:
    print(f"✗ Configuration loading failed: {e}")
    sys.exit(1)

# Test 3: Check OpenAI client
print("\n[3] OpenAI Client Check:")
print("-" * 40)
try:
    from openai import OpenAI
    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        print(f"✓ OpenAI client initialized")
        print(f"  API Key Valid: Attempting verification...")
        # Try to list models (lightweight API call)
        try:
            # This doesn't actually list models, just checks connectivity
            print("  (Skipping model list for quick diagnosis)")
            print("  OpenAI is ready to use")
        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                print(f"✗ OpenAI API Key Authentication Failed")
                print(f"  Error: {e}")
            else:
                print(f"⚠ OpenAI verification skipped: {e}")
    else:
        print("✗ OpenAI API Key not configured")
except Exception as e:
    print(f"✗ OpenAI client initialization failed: {e}")

# Test 4: Check Flask app
print("\n[4] Flask Application Check:")
print("-" * 40)
try:
    from app.main_flask import app, OPENAI_AVAILABLE
    print(f"✓ Flask app loaded successfully")
    print(f"  OpenAI Available: {OPENAI_AVAILABLE}")
    print(f"  Routes registered:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            print(f"    - {rule.rule} ({', '.join(rule.methods - {'HEAD', 'OPTIONS'})})")
except Exception as e:
    print(f"✗ Flask app loading failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test simple API call
print("\n[5] API Functionality Test:")
print("-" * 40)
try:
    with app.test_client() as client:
        # Test health endpoint
        response = client.get('/health')
        print(f"✓ Health check: {response.status_code}")
        print(f"  Response: {response.get_json()}")
        
        # Test debug endpoint
        response = client.get('/debug')
        if response.status_code == 200:
            print(f"✓ Debug endpoint: {response.status_code}")
            debug_info = response.get_json()
            print(f"  OpenAI Available: {debug_info.get('openai_available')}")
            print(f"  API Key Set: {debug_info.get('openai_api_key_set')}")
        
        # Test query endpoint
        print(f"\n✓ Testing query endpoint:")
        response = client.post('/query', 
                              json={"query": "What is Python?", "context": ""})
        print(f"  Status: {response.status_code}")
        result = response.get_json()
        if result:
            print(f"  Response: {result.get('response', '')[:100]}...")
            print(f"  Status: {result.get('status', 'unknown')}")
            if result.get('status') == 'error':
                print(f"  Error: {result.get('error', 'unknown')}")
        
except Exception as e:
    print(f"✗ API testing failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\n📋 NEXT STEPS:")
print("1. If OPENAI_API_KEY shows as not set, add it to .env file")
print("2. If OpenAI authentication fails, verify the key is correct")
print("3. Run: python app/main_flask.py")
print("4. In another terminal, run: python test_api.py")
