from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import socket
import subprocess
import os

app = FastAPI()

@app.get("/")
async def root(request: Request):
    # Get server's actual IP for debugging
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Service</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .info {{ background: #e7f3ff; padding: 15px; border: 1px solid #b8daff; border-radius: 5px; margin: 10px 0; }}
            .warning {{ background: #fff3cd; padding: 15px; border: 1px solid #ffeaa7; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>🔒 Admin Service</h1>
        
        <div class="info">
            <p><strong>Service Info:</strong></p>
            <p>This admin service is running on IP: {local_ip}</p>
            <p>Hostname: {hostname}</p>
        </div>
        
        <div class="warning">
            <p><strong>Access Control:</strong></p>
            <p>This service is protected by nginx proxy.</p>
            <p>Only requests from the admin network (192.168.100.0/24) are allowed.</p>
        </div>
        
        <p>Try accessing <a href="/admin">/admin</a> for administrative functions.</p>
        <p><strong>Note:</strong> Access control is enforced by the nginx proxy, not this service directly.</p>
    </body>
    </html>
    """)

@app.get("/admin")
async def admin(request: Request):
    # Get the original client IP from X-Forwarded-For header
    xff = request.headers.get("x-forwarded-for", "")
    client_ip = xff.split(",")[0].strip() if xff else ""
    
    # Get server's actual IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Panel</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .success {{ background: #d4edda; padding: 15px; border: 1px solid #c3e6cb; border-radius: 5px; }}
            .flag {{ background: #f8f9fa; padding: 20px; border: 2px solid #007bff; border-radius: 5px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
            .debug {{ background: #f8f9fa; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px; font-family: monospace; font-size: 12px; }}
        </style>
    </head>
    <body>
        <h1>🎯 Admin Panel Access Granted!</h1>
        
        <div class="success">
            <p><strong>✅ Authentication Successful!</strong></p>
            <p>You have successfully accessed the admin panel from the authorized network.</p>
        </div>
        
        
        <div class="debug">
            <strong>Debug Information:</strong><br>
            Admin Service IP: {local_ip}<br>
            Client IP (from X-Forwarded-For): {client_ip or 'None'}<br>
            All Request Headers: {dict(request.headers)}<br>
            Rest is in progress, please come back later for more implementation on this route<br>
        </div>
    </body>
    </html>
    """)

@app.get("/ping")
async def ping(request: Request, ip: str = "127.0.0.1"):
    """
    Usage: /ping?ip=8.8.8.8
    """
    
    try:
        # This allows command injection via semicolons, pipes, etc.
        print(ip)
        command = f"ping -c 4 {ip}"
        
        # Execute the command unsafely
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        
        output = result.stdout
        error = result.stderr
        return_code = result.returncode
        
        # Get some system info for debugging
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ping Service</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .info {{ background: #e7f3ff; padding: 15px; border: 1px solid #b8daff; border-radius: 5px; margin: 10px 0; }}
                .output {{ background: #f8f9fa; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }}
                .error {{ background: #f8d7da; padding: 15px; border: 1px solid #f5c6cb; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }}
                .form {{ background: #e7f3ff; padding: 20px; border: 1px solid #b8daff; border-radius: 5px; margin: 20px 0; }}
                input[type="text"] {{ width: 300px; padding: 8px; margin: 5px; }}
                button {{ padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
                button:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <h1>\U0001f4e1 Network Ping Service</h1>
            
            <div class="info">
                <p><strong>Service Info:</strong></p>
                <p>Server IP: {local_ip} | Hostname: {hostname}</p>
                <p>Command executed: <code>{command}</code></p>
                <p>Return code: {return_code}</p>
            </div>
            
            <div class="form">
                <h3>Ping Another IP:</h3>
                <form method="get">
                    <input type="text" name="ip" placeholder="Enter IP address" value="{ip}">
                    <button type="submit">Ping</button>
                </form>
                <p><small>Example: 8.8.8.8 or google.com</small></p>
            </div>
            
            {f'<h3>Command Output:</h3><div class="output">{output}</div>' if output else ''}
            {f'<h3>Error Output:</h3><div class="error">{error}</div>' if error else ''}
            
            <p><a href="/">← Back to Admin Service</a></p>
        </body>
        </html>
        """)
        
    except subprocess.TimeoutExpired:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Ping Service - Timeout</title></head>
        <body>
            <p>The ping command timed out after 10 seconds.</p>
            <p><a href="/ping">← Try again</a></p>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Ping Service - Error</title></head>
        <body>
            <p>An error occurred: {str(e)}</p>
            <p><a href="/ping">← Try again</a></p>
        </body>
        </html>
        """)
