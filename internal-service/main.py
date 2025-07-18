#!/usr/bin/env python3
from flask import Flask, request, render_template_string, session, redirect, url_for
import pickle
import base64
from lxml import etree
import os
import ipaddress

# TODO ensure it's only accessible from the admin docker and nothing else

app = Flask(__name__)
app.secret_key = 'ctf_secret_key_pleaseleavemealone'  # Weak secret for CTF


# Network restriction
ALLOWED_SUBNET = ipaddress.IPv4Network('192.169.100.0/24')

def check_ip_access():
    """Check if the client IP is in the allowed subnet"""
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    try:
        client_ip_obj = ipaddress.IPv4Address(client_ip)
        if client_ip_obj not in ALLOWED_SUBNET:
            abort(403)  # Forbidden
    except ipaddress.AddressValueError:
        abort(403)

@app.before_request
def before_request():
    check_ip_access()




# HTML templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Secure Login Portal</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }
        .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #333; text-align: center; margin-bottom: 30px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; background-color: #4CAF50; color: white; padding: 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #45a049; }
        .error { color: red; margin-top: 10px; }
        .debug { background: #f9f9f9; padding: 10px; margin-top: 20px; border-left: 4px solid #ccc; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔐 Secure Login Portal</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #333; text-align: center; margin-bottom: 30px; }
        .upload-form { margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 4px; }
        input[type="file"] { margin: 10px 0; }
        button { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #45a049; }
        .logout { float: right; background-color: #f44336; }
        .logout:hover { background-color: #da190b; }
        .result { margin-top: 20px; padding: 15px; background: #e8f5e8; border-radius: 4px; }
        .debug { background: #f9f9f9; padding: 10px; margin-top: 20px; border-left: 4px solid #ccc; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 User Dashboard</h2>
        <a href="/logout"><button class="logout">Logout</button></a>
        
        <p>Welcome, <strong>{{ username }}</strong>!</p>
        
        <div class="upload-form">
            <h3>📁 XML Document Upload</h3>
            <form method="POST" action="/upload" enctype="multipart/form-data">
                <input type="file" name="xmlfile" accept=".xml" required>
                <button type="submit">Process XML</button>
            </form>
        </div>
        
        {% if xml_result %}
            <div class="result">
                <h3>XML Processing Result:</h3>
                <pre>{{ xml_result }}</pre>
            </div>
        {% endif %}
        
        </div>
    </div>
</body>
</html>
'''

class User:
    def __init__(self, username, is_admin=False):
        self.username = username
        self.is_admin = is_admin
        self.session_data = {}

# user database
users = {
    'admin': 'admin',
    'user': 'password',
    'guest': 'guest123'
}

def is_safe(user_input):
    blacklist = [ "subprocess", "__", "system"]
    return not any(bad in user_input for bad in blacklist)

@app.route('/')
def index():
    if 'user_data' in session:
        try:
            user_data = pickle.loads(base64.b64decode(session['user_data']))

            if user_data in blacklist:
                print("attack discovered, exiting")
                return 

            return render_template_string(DASHBOARD_TEMPLATE, 
                                        username=user_data.username,
                                        xml_result=session.get('xml_result', ''))
        except:
            session.clear()
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username in users and users[username] == password:
        user = User(username, is_admin=(username == 'admin'))
        
        pickled_user = base64.b64encode(pickle.dumps(user)).decode()
        session['user_data'] = pickled_user
        
        return redirect(url_for('index'))
    else:
        return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")

@app.route('/upload', methods=['POST'])
def upload_xml():
    if 'user_data' not in session:
        return redirect(url_for('index'))
    
    try:
        user_data = pickle.loads(base64.b64decode(session['user_data']))
    except:
        session.clear()
        return redirect(url_for('index'))
    
    if 'xmlfile' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['xmlfile']
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file and file.filename.endswith('.xml'):
        try:
            xml_content = file.read().decode('utf-8')
            
            parser = etree.XMLParser(resolve_entities=True)
            
            root = etree.fromstring(xml_content, parser=parser)
            
            result = f"XML Root: {root.tag}\n"
            result += f"Attributes: {root.attrib}\n"
            result += f"Text content: {root.text}\n"
            
            # Recursively process child elements
            for child in root:
                result += f"Child: {child.tag} = {child.text}\n"
                if child.attrib:
                    result += f"  Attributes: {child.attrib}\n"
            
            session['xml_result'] = result
            
        except etree.ParseError as e:
            session['xml_result'] = f"XML Parse Error: {str(e)}"
        except Exception as e:
            session['xml_result'] = f"Error processing XML: {str(e)}"
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Create flag file for CTF
    print("Starting server on http://localhost:5000")
    app.run(debug=True, host='192.169.100.11', port=5000)
