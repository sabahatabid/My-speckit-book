"""Flask application for the RAG Chatbot backend."""

import os
import sys
import time
import hashlib
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from typing import List, Dict, Any, Optional

from config import settings
from billing import billing_tracker
# from ingestion.pipeline import IngestionPipeline, IngestionResult, TextChunk  # Temporarily disabled

# Configure logging first
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add OpenAI import
try:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    OPENAI_AVAILABLE = True
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.warning(f"OpenAI initialization failed: {e} - using mock responses")
    OPENAI_AVAILABLE = False
    client = None



# Global variables for background tasks
ingestion_results: Dict[str, Any] = {}

# Cache for API responses to reduce rate limit issues
response_cache: Dict[str, Dict[str, Any]] = {}
CACHE_EXPIRY = 3600  # Cache expires after 1 hour (in seconds)
RATE_LIMIT_DELAY = 1.0  # Minimum delay between API requests (in seconds)
last_api_call_time = 0

def get_cache_key(query: str, context: str) -> str:
    """Generate a cache key from query and context."""
    combined = f"{query}|{context}".lower().strip()
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_response(query: str, context: str) -> Optional[str]:
    """Get response from cache if available and not expired."""
    cache_key = get_cache_key(query, context)
    if cache_key in response_cache:
        cached = response_cache[cache_key]
        if time.time() - cached['timestamp'] < CACHE_EXPIRY:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached['response']
        else:
            # Remove expired cache
            del response_cache[cache_key]
    return None

def cache_response(query: str, context: str, response: str):
    """Cache the API response."""
    cache_key = get_cache_key(query, context)
    response_cache[cache_key] = {
        'response': response,
        'timestamp': time.time()
    }
    logger.info(f"Cached response for query: {query[:50]}...")

def enforce_rate_limit():
    """Enforce minimum delay between API calls."""
    global last_api_call_time
    elapsed = time.time() - last_api_call_time
    if elapsed < RATE_LIMIT_DELAY:
        sleep_time = RATE_LIMIT_DELAY - elapsed
        logger.info(f"Rate limiting: waiting {sleep_time:.2f}s before next API call")
        time.sleep(sleep_time)
    last_api_call_time = time.time()

def generate_ai_response(query: str, context: str = "") -> str:
    """Generate AI response using OpenAI with caching and rate limiting."""
    try:
        # Check cache first
        cached_response = get_cached_response(query, context)
        if cached_response:
            return cached_response
        
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available, returning mock response")
            return f"Mock response: Unable to process query '{query}' - OpenAI client not initialized. Please check your API key."
        
        if not settings.openai_api_key:
            logger.error("OpenAI API key is empty")
            return "Error: OpenAI API key is not configured. Please add OPENAI_API_KEY to your .env file."

        # Enforce rate limiting
        enforce_rate_limit()

        # Create prompt based on context
        if context:
            prompt = f"""You are a helpful AI assistant for a technical documentation book. The user has selected this text: "{context}"

Based on this context, please answer their question: "{query}"

Provide a clear, helpful response that relates to the selected content. If the question isn't directly related to the context, use your general knowledge but reference that you don't see direct connection to the selected text."""
        else:
            prompt = f"""You are a helpful AI assistant for a technical documentation book. Please answer this question: "{query}"

Provide a clear, helpful response. Since no specific text was selected, draw from your general knowledge while keeping the response relevant to technical documentation."""

        # Call OpenAI API
        logger.info(f"Making OpenAI API call for query: {query[:50]}...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant specializing in technical documentation and programming."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content.strip()
        logger.info(f"OpenAI response generated successfully: {len(ai_response)} characters")
        
        # Track billing and usage
        try:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            billing_tracker.log_request(
                query=query,
                context=context,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model="gpt-3.5-turbo",
                response=ai_response
            )
        except Exception as e:
            logger.warning(f"Failed to log billing: {e}")
        
        # Cache the response
        cache_response(query, context, ai_response)
        
        return ai_response

    except Exception as e:
        logger.error(f"Unexpected error in AI response generation: {type(e).__name__}: {e}")
        error_msg = str(e).lower()
        
        # Specific error handling
        if "authentication" in error_msg or "api key" in error_msg or "401" in error_msg:
            logger.warning("Authentication error - checking API key configuration")
            return f"Error: Authentication failed with OpenAI. Please verify your OPENAI_API_KEY in the .env file is correct. Error details: {str(e)[:100]}"
        elif "rate limit" in error_msg or "429" in error_msg:
            logger.warning("Rate limit exceeded - wait before retrying")
            return f"Error: OpenAI API rate limit exceeded. This happens with free tier accounts. Please wait a moment and try again, or upgrade your OpenAI plan at https://platform.openai.com/account/billing/overview"
        elif "insufficient_quota" in error_msg or "billing" in error_msg or "403" in error_msg:
            logger.warning("Insufficient quota or billing issue")
            return f"Error: OpenAI account has insufficient credits. Please add credits to your account at https://platform.openai.com/account/billing/overview"
        elif "model" in error_msg and "not found" in error_msg:
            logger.warning("Model not found")
            return f"Error: The specified model (gpt-3.5-turbo) is not available. Please check your OpenAI account permissions."
        else:
            logger.warning(f"General API error: {str(e)}")
            return f"Error: Failed to generate response. Details: {str(e)[:150]}"

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/', methods=['GET'])
def index():
    """Root endpoint - shows available API endpoints."""
    return jsonify({
        "status": "RAG Chatbot Backend Running",
        "version": "0.1.0",
        "endpoints": {
            "GET /": "This endpoint - shows available endpoints",
            "GET /health": "Health check endpoint",
            "GET /debug": "Debug information (OpenAI status, API key check)",
            "POST /query": "Submit a query to the chatbot - requires JSON: {'query': 'your question', 'context': 'optional selected text'}",
            "POST /ingest": "Start document ingestion",
            "GET /ingest/status": "Check ingestion status",
            "GET /billing/stats": "Get cumulative API usage and billing statistics",
            "GET /billing/recent": "Get recent API usage records (add ?limit=N parameter)"
        },
        "docs": "RAG Chatbot for Docusaurus documentation",
        "openai_available": OPENAI_AVAILABLE,
        "billing_tracking": "Enabled - all API calls are tracked for cost monitoring"
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "version": "0.1.0"})


@app.route('/ingest', methods=['POST'])
def ingest_documents():
    """Mock document ingestion endpoint."""
    try:
        data = request.get_json() or {}
        docs_path = data.get('docs_path', '../docs')

        logger.info(f"Mock ingestion started for path: {docs_path}")

        # Mock ingestion result
        response_data = {
            "success": True,
            "documents_processed": 5,
            "chunks_created": 25,
            "total_tokens": 1250,
            "errors": [],
            "validation": {"status": "mock_validation_passed"},
            "database_status": "mock_database_ready"
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Mock ingestion failed: {e}")
        return jsonify({"error": f"Ingestion failed: {str(e)}"}), 500


@app.route('/ingest/status', methods=['GET'])
def get_ingestion_status():
    """Get the status of the latest ingestion."""
    if "latest" not in ingestion_results:
        return jsonify({"status": "No ingestion completed yet"})

    result = ingestion_results["latest"]
    return jsonify({
        "status": "completed" if result.success else "failed",
        "documents_processed": result.documents_processed,
        "chunks_created": result.chunks_created,
        "total_tokens": result.total_tokens,
        "errors": result.errors
    })


@app.route('/billing/stats', methods=['GET'])
def billing_stats():
    """Get API usage and billing statistics."""
    stats = billing_tracker.get_stats()
    return jsonify({
        "total_requests": stats.get("total_requests", 0),
        "total_tokens": stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0),
        "total_input_tokens": stats.get("total_input_tokens", 0),
        "total_output_tokens": stats.get("total_output_tokens", 0),
        "total_cost_usd": round(stats.get("total_cost", 0), 4),
        "model": stats.get("model", "gpt-3.5-turbo"),
        "first_request": stats.get("first_request"),
        "last_request": stats.get("last_request")
    })


@app.route('/billing/recent', methods=['GET'])
def billing_recent():
    """Get recent API usage records."""
    limit = request.args.get('limit', 10, type=int)
    recent = billing_tracker.get_recent_usage(limit)
    return jsonify({
        "records": recent,
        "count": len(recent)
    })


@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check system status."""
    return jsonify({
        "openai_available": OPENAI_AVAILABLE,
        "openai_api_key_set": bool(settings.openai_api_key),
        "openai_api_key_prefix": settings.openai_api_key[:10] + "..." if settings.openai_api_key else None,
    })


@app.route('/query', methods=['POST'])
def query_chatbot():
    """Handle chatbot queries with AI-powered responses."""
    try:
        data = request.get_json()
        if not data:
            error_msg = "No JSON data provided in request"
            logger.error(error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 400

        # Simple validation without pydantic
        query = data.get('query', '').strip()
        context = data.get('context', '').strip()

        if not query:
            error_msg = "Query is required and cannot be empty"
            logger.error(error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 400

        logger.info(f"Received query: {query[:100]}...")

        # Check if OpenAI is available
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI client not initialized")
            return jsonify({
                "error": "OpenAI service not available. Please check your API configuration.",
                "status": "error"
            }), 503

        # Generate AI response
        response_text = generate_ai_response(query, context)

        # Check if response is an error message
        if response_text.startswith("Error:"):
            logger.warning(f"AI generation returned error: {response_text}")
            return jsonify({
                "response": response_text,
                "sources": [],
                "confidence": 0.0,
                "status": "error"
            }), 200

        # Mock sources
        sources = [
            {
                "chunk_id": "mock-source-1",
                "content": "Sample source content from documentation",
                "document_path": "docs/intro.md",
                "similarity_score": 0.85
            }
        ]

        response_data = {
            "response": response_text,
            "sources": sources,
            "confidence": 0.8,
            "status": "success"
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Query failed: {type(e).__name__}: {e}", exc_info=True)
        return jsonify({
            "error": f"Query processing failed: {str(e)}",
            "status": "error"
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,  # Disable debug mode to avoid watchdog issues
        use_reloader=False  # Disable reloader on Windows
    )