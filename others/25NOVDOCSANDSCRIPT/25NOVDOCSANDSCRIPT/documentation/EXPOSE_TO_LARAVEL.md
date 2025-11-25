# Exposing Local Backend to Laravel Frontend

This guide provides **free and unlimited** ways to expose your local chatbot backend to a Laravel frontend.

## 🏆 Best Option: Cloudflare Tunnel (Recommended)

**Why Cloudflare Tunnel?**
- ✅ **100% Free Forever**
- ✅ **Unlimited Bandwidth**
- ✅ **Stable URLs** (can set custom subdomain)
- ✅ **No Connection Limits**
- ✅ **HTTPS by Default**
- ✅ **Works Great for Development & Production**

### Installation

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

### Quick Start

1. **Start your chatbot server:**
```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **In a new terminal, start Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:8000
```

3. **Copy the URL** (e.g., `https://abc123-def456.trycloudflare.com`)

4. **Use this URL in your Laravel `.env`:**
```env
CHATBOT_API_URL=https://abc123-def456.trycloudflare.com
```

### Using Custom Subdomain (Optional)

For a stable URL that doesn't change:

1. **Login to Cloudflare:**
```bash
cloudflared tunnel login
```

2. **Create a tunnel:**
```bash
cloudflared tunnel create aiura-chatbot
```

3. **Configure the tunnel:**
```bash
cloudflared tunnel route dns aiura-chatbot your-subdomain.yourdomain.com
```

4. **Create config file** (`~/.cloudflared/config.yml`):
```yaml
tunnel: aiura-chatbot
credentials-file: /Users/abdulbasit/.cloudflared/aiura-chatbot.json

ingress:
  - hostname: your-subdomain.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

5. **Run the tunnel:**
```bash
cloudflared tunnel run aiura-chatbot
```

---

## 🥈 Alternative Option 1: localtunnel

**Why localtunnel?**
- ✅ **Free**
- ✅ **Unlimited**
- ✅ **No Signup Required**
- ❌ URLs change each time

### Installation

```bash
npm install -g localtunnel
```

### Usage

1. **Start your chatbot server** (as above)

2. **Start localtunnel:**
```bash
lt --port 8000
```

3. **Copy the URL** (e.g., `https://random-name.loca.lt`)

4. **Use in Laravel `.env`:**
```env
CHATBOT_API_URL=https://random-name.loca.lt
```

### Using Custom Subdomain (Optional)

```bash
lt --port 8000 --subdomain your-custom-name
```

**Note:** Custom subdomains may not always be available.

---

## 🥉 Alternative Option 2: ngrok

**Why ngrok?**
- ✅ **Free Tier Available**
- ✅ **Stable URLs** (with account)
- ❌ **Free tier has limitations** (connection limits, URL changes)

### Installation

```bash
# macOS
brew install ngrok/ngrok/ngrok

# Or download from: https://ngrok.com/download
```

### Usage

1. **Sign up at:** https://dashboard.ngrok.com/signup

2. **Get your authtoken:**
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

3. **Start your chatbot server** (as above)

4. **Start ngrok:**
```bash
ngrok http 8000
```

5. **Copy the URL** (e.g., `https://abc123.ngrok-free.app`)

6. **Use in Laravel `.env`:**
```env
CHATBOT_API_URL=https://abc123.ngrok-free.app
```

### Using Custom Domain (Paid Feature)

```bash
ngrok http 8000 --domain=your-custom-domain.ngrok.io
```

---

## 🔧 Helper Scripts

I've created helper scripts to make this easier. See the `scripts/` directory:

- `scripts/expose-cloudflare.sh` - Start Cloudflare Tunnel
- `scripts/expose-localtunnel.sh` - Start localtunnel
- `scripts/expose-ngrok.sh` - Start ngrok

---

## 📝 Laravel Integration

### Step 1: Update Laravel `.env`

Add your tunnel URL:

```env
CHATBOT_API_URL=https://your-tunnel-url.com
```

### Step 2: Create Laravel Blade Component

Create `resources/views/components/chatbot-widget.blade.php`:

```blade
<!-- Neguinho Motors Chatbot Widget -->
<div id="chatbotWidgetContainer"></div>

<script>
    // Set your tunnel URL here
    window.CHATBOT_API_URL = '{{ env("CHATBOT_API_URL", "http://localhost:8000/api/v1") }}';
    
    // Load widget script
    (function() {
        const script = document.createElement('script');
        script.src = '{{ env("CHATBOT_API_URL", "http://localhost:8000") }}/static/widget.js';
        script.async = true;
        document.head.appendChild(script);
        
        // Load widget styles
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '{{ env("CHATBOT_API_URL", "http://localhost:8000") }}/static/widget.css';
        document.head.appendChild(link);
    })();
</script>
```

### Step 3: Add to Laravel Layout

In `resources/views/layouts/app.blade.php`, add before `</body>`:

```blade
@include('components.chatbot-widget')
```

### Step 4: Simple iframe Alternative

For the simplest integration, use an iframe:

```blade
<!-- In your Laravel blade template -->
<iframe 
    src="{{ env('CHATBOT_API_URL', 'http://localhost:8000') }}/frontend/widget.html"
    width="380"
    height="600"
    style="position: fixed; bottom: 20px; right: 20px; border: none; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 10000;"
    allow="microphone"
></iframe>
```

---

## 🔒 CORS Configuration

Your backend already allows all origins by default. If you want to restrict it, update `backend/config/settings.py`:

```python
cors_origins: List[str] = [
    "https://your-laravel-domain.com",
    "https://*.trycloudflare.com",  # Cloudflare Tunnel
    "https://*.loca.lt",            # localtunnel
    "https://*.ngrok-free.app",     # ngrok
]
```

---

## 🧪 Testing

1. **Start your chatbot server:**
```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **Start your chosen tunnel** (Cloudflare, localtunnel, or ngrok)

3. **Test the tunnel URL:**
```bash
curl https://your-tunnel-url.com/health
```

Should return:
```json
{"status":"healthy","version":"1.0.0"}
```

4. **Update Laravel `.env`** with the tunnel URL

5. **Visit your Laravel website** - the chatbot widget should appear

---

## 📊 Comparison Table

| Feature | Cloudflare Tunnel | localtunnel | ngrok |
|---------|------------------|--------------|-------|
| **Cost** | Free | Free | Free (limited) |
| **Bandwidth** | Unlimited | Unlimited | Limited (free) |
| **Stable URL** | ✅ (with setup) | ❌ | ✅ (with account) |
| **Custom Domain** | ✅ | ❌ | ✅ (paid) |
| **HTTPS** | ✅ | ✅ | ✅ |
| **Setup Complexity** | Medium | Easy | Easy |
| **Best For** | Production-ready | Quick testing | Development |

---

## 🎯 Recommendation

**For Development:**
- Use **Cloudflare Tunnel** (quick start with `cloudflared tunnel --url http://localhost:8000`)
- Or **localtunnel** for quick testing

**For Production:**
- Use **Cloudflare Tunnel** with custom subdomain (most reliable and free)
- Or deploy your backend to a proper hosting service

---

## 🆘 Troubleshooting

### Tunnel URL Not Working?

1. **Check your chatbot server is running:**
```bash
curl http://localhost:8000/health
```

2. **Check tunnel is running:**
   - Cloudflare: Check terminal output
   - localtunnel: Check terminal output
   - ngrok: Visit http://localhost:4040 (ngrok web interface)

3. **Check CORS settings** in `backend/config/settings.py`

4. **Check Laravel `.env`** has correct `CHATBOT_API_URL`

### CORS Errors?

Your backend already allows all origins. If you see CORS errors:
1. Check the tunnel URL is correct
2. Verify the backend is accessible via the tunnel
3. Check browser console for specific error messages

---

## 📚 Additional Resources

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [localtunnel GitHub](https://github.com/localtunnel/localtunnel)
- [ngrok Docs](https://ngrok.com/docs)

---

**🎉 You're ready to connect your Laravel frontend to your local chatbot backend!**

