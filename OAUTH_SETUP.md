# OAuth Setup Guide - Google & Facebook Login

## 🚀 What is OAuth?

**OAuth** allows users to login with their existing Google/Facebook accounts instead of creating new passwords. 

**Benefits:**
- ✅ **Faster registration** - No password needed
- ✅ **Secure** - Uses Google/Facebook security
- ✅ **Convenient** - Users don't forget passwords
- ✅ **Trust** - People trust Google/Facebook login

## 🔧 How OAuth Works

```
1. User clicks "Login with Google"
2. Redirected to Google login page
3. User enters Google credentials
4. Google sends user info back to your app
5. Your app creates/logs in the user
```

## 📋 Setup Instructions

### 1. Google OAuth Setup

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create New Project:**
   - Click "Select Project" → "New Project"
   - Name: "Planinsko Društvo OAuth"
   - Click "Create"

3. **Enable Google+ API:**
   - Go to "APIs & Services" → "Library"
   - Search: "Google+ API"
   - Click "Enable"

4. **Create OAuth Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Web application"
   - Name: "Mountaineering Club"
   - **Authorized redirect URIs:**
     ```
     http://localhost:5002/auth/google/callback
     https://your-domain.com/auth/google/callback
     ```
   - Click "Create"

5. **Copy Credentials:**
   - **Client ID:** `123456789-abc123.apps.googleusercontent.com`
   - **Client Secret:** `ABC123-secretkey`

### 2. Facebook OAuth Setup

1. **Go to Facebook Developers:**
   - Visit: https://developers.facebook.com/

2. **Create New App:**
   - Click "Create App"
   - Type: "Consumer"
   - Name: "Planinsko Društvo"
   - Click "Create"

3. **Add Facebook Login:**
   - Dashboard → "Add Product"
   - Find "Facebook Login" → "Set Up"

4. **Configure OAuth Settings:**
   - Facebook Login → Settings
   - **Valid OAuth Redirect URIs:**
     ```
     http://localhost:5002/auth/facebook/callback
     https://your-domain.com/auth/facebook/callback
     ```
   - Save Changes

5. **Copy Credentials:**
   - Settings → Basic
   - **App ID:** `1234567890123456`
   - **App Secret:** `abcdef1234567890` (click "Show")

### 3. Update .env File

```bash
# Add to your .env file:
GOOGLE_CLIENT_ID=123456789-abc123.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=ABC123-secretkey
FACEBOOK_CLIENT_ID=1234567890123456
FACEBOOK_CLIENT_SECRET=abcdef1234567890
```

### 4. Test OAuth

```bash
# Install new dependencies
pip install authlib httpx

# Run your app
python app.py

# Test:
# 1. Go to http://localhost:5002/login
# 2. Click "Prijava z Google" or "Prijava s Facebook"
# 3. Should redirect to Google/Facebook
# 4. After login, redirected back to your app
```

## 🔑 OAuth Code Explanation

### 1. OAuth Configuration (app.py)
```python
from authlib.integrations.flask_client import OAuth

# Initialize OAuth
oauth = OAuth(app)

# Configure Google
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
```

### 2. OAuth Routes
```python
# Start OAuth flow
@app.route('/auth/<provider>')
def oauth_login(provider):
    redirect_uri = url_for('oauth_callback', provider='google', _external=True)
    return google.authorize_redirect(redirect_uri)

# Handle OAuth callback
@app.route('/auth/<provider>/callback')
def oauth_callback(provider):
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    email = user_info['email']
    full_name = user_info['name']
    # Create or login user...
```

### 3. User Data Flow
```python
# What we get from Google/Facebook:
{
    'email': 'janez.novak@gmail.com',
    'name': 'Janez Novak',
    'picture': 'https://profile-photo-url.jpg'
}

# What we store in MongoDB:
{
    'email': 'janez.novak@gmail.com',
    'full_name': 'Janez Novak',
    'password': None,  # OAuth users don't have passwords
    'oauth_provider': 'google',
    'profile_picture': 'https://profile-photo-url.jpg',
    'is_approved': False,  # Still needs admin approval
    'is_admin': False
}
```

## 🛡️ Security Notes

- ✅ **No passwords stored** - OAuth users authenticate via Google/Facebook
- ✅ **Admin approval required** - OAuth users still need approval
- ✅ **Secure tokens** - Authlib handles token security
- ✅ **Profile pictures** - Automatically fetched from OAuth provider

## 🔧 HTML Templates

### Login Button (login.html)
```html
<a href="{{ url_for('oauth_login', provider='google') }}" class="btn btn-outline-danger">
    <i class="fab fa-google"></i> Prijava z Google
</a>
```

### User Flow
1. **User clicks OAuth button**
2. **Redirected to Google/Facebook**
3. **User authenticates**
4. **Returned to your app with user info**
5. **Account created (pending approval) or logged in**

## 🎯 Benefits for Your Club

- **Easier registration** - Members don't need new passwords
- **Higher signup rate** - People trust Google/Facebook
- **Better security** - No weak passwords
- **Profile pictures** - Automatic from social accounts
- **Still secure** - Admin approval still required