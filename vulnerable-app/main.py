import ipaddress
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
from urllib.parse import urlparse, unquote
import os
import logging

app = FastAPI()

# Configuration sécurisée - Approche blacklist pour les ressources internes
ALLOWED_PROTOCOLS = ['http', 'https']

# Noms d'hôtes Docker internes et localhost à bloquer
BLOCKED_INTERNAL_HOSTS = [
    'nginx-proxy',
    'internal-service', 
    'admin-service',
    'vulnerable-app',
    'localhost',
    'host.docker.internal',
    'docker.for.mac.localhost',
    'docker.for.windows.localhost'
]

# Domaines internes de l'entreprise à bloquer (exemple)
BLOCKED_INTERNAL_DOMAINS = [
    'internal.company.com',
    'admin.company.com',
    'staging.company.com'
]

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Valide si une URL est sécurisée en bloquant les accès internes.
    Approche whitelist pour les protocoles, blacklist pour les ressources internes.
    
    Args:
        url (str): URL à valider
        
    Returns:
        tuple[bool, str]: (is_safe, error_message)
    """
    try:
        
        decoded_url = unquote(url)
        parsed = urlparse(decoded_url)
        
        # Vérifier le protocole (whitelist stricte)
        if parsed.scheme not in ALLOWED_PROTOCOLS:
            return False, f"Protocol '{parsed.scheme}' not allowed. Only {ALLOWED_PROTOCOLS} are permitted."
        
        # Vérifier le hostname
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: missing hostname"
        
        # Bloquer les noms d'hôtes internes Docker/localhost
        if hostname.lower() in [host.lower() for host in BLOCKED_INTERNAL_HOSTS]:
            return False, f"Access to internal host '{hostname}' is not allowed"
        
        # Bloquer les domaines internes de l'entreprise
        if hostname.lower() in [domain.lower() for domain in BLOCKED_INTERNAL_DOMAINS]:
            return False, f"Access to internal domain '{hostname}' is not allowed"
        
        # Validation des adresses IP - bloquer les IPs privées
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False, f"Access to private/loopback IP '{hostname}' is not allowed"
        except ValueError:
            # Ce n'est pas une IP, c'est un nom d'hôte - validation OK si pas dans les blacklists
            pass
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False, f"Invalid URL format: {str(e)}"

INTERNAL_SERVICE_URL = os.getenv("INTERNAL_SERVICE_URL", "http://nginx-proxy:80")

@app.get("/", response_class=HTMLResponse)
async def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure URL Fetcher</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .form-group {{ margin: 20px 0; }}
            input[type="url"] {{ width: 100%; padding: 10px; }}
            button {{ padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }}
            .result {{ background: #f8f9fa; padding: 15px; margin: 20px 0; border-left: 4px solid #007bff; }}
            .error {{ border-left-color: #dc3545; background: #f8d7da; }}
            .security-info {{ background: #d4edda; padding: 15px; margin: 20px 0; border-left: 4px solid #28a745; }}
        </style>
    </head>
    <body>
        <h1>🔒 Secure URL Fetcher Service</h1>
        <p>Enter any public URL and we'll fetch its content for you!</p>
        
        <form method="post" action="/fetch">
            <div class="form-group">
                <label for="url">URL to fetch:</label>
                <input type="url" id="url" name="url" placeholder="https://www.youtube.com" required>
            </div>
            <button type="submit">Fetch Content</button>
        </form>
        
        <div class="security-info">
            <h3>🛡️ Security Information</h3>
            <p><strong>Allowed protocols:</strong> {', '.join(ALLOWED_PROTOCOLS)}</p>
            <p><strong>Blocked internal hosts:</strong> {', '.join(BLOCKED_INTERNAL_HOSTS[:5])}...</p>
            <p>✅ Public websites are allowed (YouTube, Google, etc.)</p>
            <p>❌ Internal services are blocked for security</p>
        </div>
    </body>
    </html>
    """

@app.post("/fetch")
async def fetch_url(url: str = Form(...)):
    try:
        # Validation sécurisée de l'URL
        is_safe, error_msg = is_safe_url(url)
        if not is_safe:
            logger.warning(f"Blocked malicious request: {url} - {error_msg}")
            raise HTTPException(status_code=403, detail=error_msg)
        
        # Décoder l'URL après validation
        decoded_url = unquote(url)
        logger.info(f"Fetching approved URL: {decoded_url}")
        
        # Requête HTTP sécurisée
        async with httpx.AsyncClient(
            timeout=10.0,  # Timeout plus long pour les sites externes
            follow_redirects=True,  # Permettre les redirects pour les sites normaux
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        ) as client:
            response = await client.get(decoded_url)
            
        logger.info(f"Successfully fetched {decoded_url} - Status: {response.status_code}")
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fetch Result</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .result {{ background: #f8f9fa; padding: 15px; margin: 20px 0; border-left: 4px solid #28a745; }}
                pre {{ background: #f1f1f1; padding: 10px; overflow-x: auto; }}
                .success {{ color: #28a745; }}
            </style>
        </head>
        <body>
            <h1>✅ Fetch Successful</h1>
            <div class="result">
                <h3>URL: {decoded_url}</h3>
                <h3>Status Code: <span class="success">{response.status_code}</span></h3>
                <h3>Content:</h3>
                <pre>{response.text[:2000]}{'...' if len(response.text) > 2000 else ''}</pre>
            </div>
            <a href="/">← Back to home</a>
        </body>
        </html>
        """)
        
    except HTTPException:
        # Re-raise HTTPException (validation errors) as-is
        raise
    except httpx.RequestError as e:
        logger.error(f"HTTP request failed for {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid URL format: {url} - {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid URL format: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected internal error processing {url}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
