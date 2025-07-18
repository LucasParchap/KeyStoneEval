import ipaddress
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
from urllib.parse import urlparse, unquote
import os

app = FastAPI()

INTERNAL_SERVICE_URL = os.getenv("INTERNAL_SERVICE_URL", "http://nginx-proxy:80")

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CTF Challenge - URL Fetcher</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .form-group { margin: 20px 0; }
            input[type="url"] { width: 100%; padding: 10px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            .result { background: #f8f9fa; padding: 15px; margin: 20px 0; border-left: 4px solid #007bff; }
            .error { border-left-color: #dc3545; background: #f8d7da; }
        </style>
    </head>
    <body>
        <h1>🚀 URL Fetcher Service</h1>
        <p>Enter a URL and we'll fetch its content for you!</p>
        
        <form method="post" action="/fetch">
            <div class="form-group">
                <label for="url">URL to fetch:</label>
                <input type="url" id="url" name="url" placeholder="https://example.com" required>
            </div>
            <button type="submit">Fetch Content</button>
        </form>
        
        <div class="info">
            <h3>ℹ️ Information</h3>
            <p>This service can fetch content from any publicly accessible URL.</p>
        </div>
    </body>
    </html>
    """

@app.post("/fetch")
async def fetch_url(url: str = Form(...)):
    try:
        parsed = urlparse(url)
        print(parsed)
        
        hostname = parsed.hostname
        if not hostname:
            raise HTTPException(status_code=400, detail="Invalid URL")
        
        # Check for localhost variations
        localhost_variants = ['localhost', '127.0.0.1', '::1']
        if hostname.lower() in localhost_variants:
            raise HTTPException(status_code=400, detail="Localhost access not allowed")
        print("passed filter for localhost")
        
        # Additional check for private IP ranges in string form
        private_prefixes = ['192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', 
                           '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
                           '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.']
        
        if any(hostname.startswith(prefix) for prefix in private_prefixes):
            raise HTTPException(status_code=400, detail="Private network access not allowed")
        
        print("still got there")
        print(parsed)
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(unquote(url))
            
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fetch Result</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .result {{ background: #f8f9fa; padding: 15px; margin: 20px 0; border-left: 4px solid #28a745; }}
                pre {{ background: #f1f1f1; padding: 10px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1> Fetch Successful</h1>
            <div class="result">
                <h3>URL: {url}</h3>
                <h3>Status Code: {response.status_code}</h3>
                <h3>Content:</h3>
                <pre>{response.text[:2000]}{'...' if len(response.text) > 2000 else ''}</pre>
            </div>
            <a href="/">← Back to home</a>
        </body>
        </html>
        """)
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
