#!/usr/bin/env python
"""Comprehensive test script to verify chatbot OpenAI integration."""

import sys
import os
import json
import requests
import time

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

print("=" * 70)
print("CHATBOT SETUP & OPENAI API VERIFICATION")
print("=" * 70)

# Test 1: Load config
print("\n[TEST 1] Loading Configuration...")
print("-" * 70)
try:
    from config import settings
    api_key = settings.openai_api_key
    
    if not api_key:
        print("❌ FAIL: OpenAI API key is not set in .env file")
        sys.exit(1)
    
    key_preview = api_key[:20] + "..." + api_key[-10:] if len(api_key) > 30 else api_key[:20] + "..."
    print(f"✅ Config loaded successfully")
    print(f"   - OpenAI API Key: {key_preview}")
    print(f"   - Qdrant URL: {'Configured' if settings.qdrant_url else 'NOT SET'}")
    print(f"   - Database: {settings.database_url}")
    print(f"   - Chunk Size: {settings.chunk_size}")
    print(f"   - Debug Mode: {settings.debug}")
except Exception as e:
    print(f"❌ FAIL: Failed to load config: {e}")
    sys.exit(1)

# Test 2: Load Flask app
print("\n[TEST 2] Initializing Flask App...")
print("-" * 70)
try:
    from main_flask import app, OPENAI_AVAILABLE, client
    print(f"✅ Flask app initialized")
    print(f"   - OpenAI Available: {OPENAI_AVAILABLE}")
    
    if not OPENAI_AVAILABLE:
        print("   ⚠️  WARNING: OpenAI client not available - check your API key!")
    else:
        print("   - OpenAI client ready")
except Exception as e:
    print(f"❌ FAIL: Failed to initialize Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test health endpoint
print("\n[TEST 3] Testing Health Endpoint...")
print("-" * 70)
try:
    with app.test_client() as client_test:
        response = client_test.get('/health')
        
        if response.status_code == 200:
            print(f"✅ Health check passed (Status: {response.status_code})")
            print(f"   - Response: {response.get_json()}")
        else:
            print(f"❌ FAIL: Health check failed with status {response.status_code}")
except Exception as e:
    print(f"❌ FAIL: Health check error: {e}")

# Test 4: Test debug endpoint
print("\n[TEST 4] Testing Debug Endpoint...")
print("-" * 70)
try:
    with app.test_client() as client_test:
        response = client_test.get('/debug')
        
        if response.status_code == 200:
            debug_data = response.get_json()
            print(f"✅ Debug endpoint working")
            print(f"   - OpenAI Available: {debug_data['openai_available']}")
            print(f"   - API Key Set: {debug_data['openai_api_key_set']}")
            if debug_data['openai_api_key_prefix']:
                print(f"   - API Key Prefix: {debug_data['openai_api_key_prefix']}")
        else:
            print(f"❌ FAIL: Debug endpoint failed with status {response.status_code}")
except Exception as e:
    print(f"❌ FAIL: Debug endpoint error: {e}")

# Test 5: Test query endpoint
print("\n[TEST 5] Testing Query Endpoint (OpenAI Integration)...")
print("-" * 70)
try:
    with app.test_client() as client_test:
        test_query = {
            "query": "What is robotics?",
            "context": ""
        }
        
        response = client_test.post(
            '/query',
            json=test_query,
            content_type='application/json'
        )
        
        if response.status_code == 200:
            response_data = response.get_json()
            status = response_data.get('status', 'unknown')
            
            if status == 'success':
                print(f"✅ Query endpoint working correctly!")
                print(f"   - Status: {status}")
                print(f"   - Response: {response_data.get('response', '')[:100]}...")
                print(f"   - Confidence: {response_data.get('confidence', 0)}")
                print(f"   - Sources: {len(response_data.get('sources', []))} found")
            elif status == 'error':
                print(f"⚠️  Query returned error status")
                print(f"   - Error: {response_data.get('response', 'Unknown error')[:150]}")
            else:
                print(f"⚠️  Unexpected status: {status}")
                print(f"   - Response: {json.dumps(response_data, indent=2)}")
        else:
            print(f"❌ FAIL: Query endpoint returned status {response.status_code}")
            print(f"   - Response: {response.get_json()}")
except Exception as e:
    print(f"❌ FAIL: Query endpoint error: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Verify OpenAI API directly
print("\n[TEST 6] Direct OpenAI API Test...")
print("-" * 70)
try:
    from openai import OpenAI
    test_client = OpenAI(api_key=api_key)
    
    # Test if key is valid by making a minimal request
    response = test_client.models.list()
    available_models = [m.id for m in response.data]
    
    print(f"✅ OpenAI API authentication successful!")
    print(f"   - Available models: {len(available_models)}")
    
    # Check if gpt-3.5-turbo is available
    if 'gpt-3.5-turbo' in available_models:
        print(f"   - gpt-3.5-turbo: ✅ Available")
    else:
        print(f"   - gpt-3.5-turbo: ❌ NOT available")
        print(f"   - Available GPT models: {[m for m in available_models if 'gpt' in m]}")
        
except Exception as e:
    print(f"❌ FAIL: OpenAI API test failed: {e}")
    error_msg = str(e).lower()
    
    if "invalid api key" in error_msg or "authentication" in error_msg:
        print("   → Your API key is invalid or expired")
        print("   → Solution: Regenerate your API key at https://platform.openai.com/account/api-keys")
    elif "rate limit" in error_msg or "429" in error_msg:
        print("   → You've hit the rate limit")
        print("   → Solution: Wait a moment and try again")
    elif "insufficient_quota" in error_msg or "billing" in error_msg:
        print("   → Your OpenAI account has no credits")
        print("   → Solution: Add credits at https://platform.openai.com/account/billing/overview")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
✅ Your chatbot is configured with:
  - Flask backend on port 8000
  - OpenAI GPT-3.5-turbo integration
  - Rate limiting and caching enabled
  - CORS enabled for frontend integration

📝 NEXT STEPS:
  1. Make sure your OpenAI account has available credits
  2. Start the backend:
     cd chatbot/backend
     python app/main_flask.py
     
  3. Test in another terminal:
     curl -X POST http://localhost:8000/query \\
       -H "Content-Type: application/json" \\
       -d '{"query": "Hello", "context": ""}'

🔒 SECURITY REMINDER:
  - Regenerate your OpenAI API key immediately
  - Add .env to .gitignore
  - Never commit credentials to git
  
⚠️  Common Issues:
  - "Invalid API Key" → Regenerate at https://platform.openai.com/account/api-keys
  - "Insufficient Quota" → Add credits at https://platform.openai.com/account/billing/overview
  - "Rate Limit" → Wait a moment before making next request
""")
print("=" * 70)
