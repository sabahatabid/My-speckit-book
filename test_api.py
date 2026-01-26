#!/usr/bin/env python3
"""Test script for the chatbot backend API."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_query():
    """Test the query endpoint with AI."""
    try:
        payload = {
            "query": "What is machine learning?",
            "context": "Machine learning is a subset of artificial intelligence"
        }
        response = requests.post(f"{BASE_URL}/query", json=payload)
        print(f"Query test: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data.get('response', '')[:200]}...")
            print(f"Sources: {len(data.get('sources', []))}")
            print(f"Confidence: {data.get('confidence', 0)}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Query test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Chatbot Backend API with AI...")
    print("=" * 50)

    health_ok = test_health()
    print()

    if health_ok:
        query_ok = test_query()
    else:
        print("Skipping query test - backend not healthy")
        query_ok = False

    print()
    print("=" * 50)
    if health_ok and query_ok:
        print("✅ All tests passed! AI chatbot is working.")
    else:
        print("❌ Some tests failed. Check backend logs and API key.")