# 🚀 Quick Start Guide

## One Command to Go Live

```bash
./scripts/manage.sh expose
```

This single command will:
1. ✅ Start the chatbot server
2. ✅ Start Cloudflare tunnel
3. ✅ Give you a public HTTPS URL
4. ✅ Show all API endpoints

**That's it! Your chatbot is now live and accessible from anywhere!**

---

## Management Commands

| Command | Description |
|---------|-------------|
| `./scripts/manage.sh expose` | **Start everything** (server + tunnel) - Recommended! |
| `./scripts/manage.sh start` | Start server only |
| `./scripts/manage.sh stop` | Stop server |
| `./scripts/manage.sh restart` | Restart server |
| `./scripts/manage.sh status` | Check server and tunnel status |
| `./scripts/manage.sh tunnel start` | Start tunnel only |
| `./scripts/manage.sh tunnel stop` | Stop tunnel only |

---

## What You Get

After running `./scripts/manage.sh expose`:

```
✅ Server started successfully
📍 Server URL: http://localhost:8000
📚 API Docs: http://localhost:8000/docs

✅ Tunnel started successfully
🌍 Public URL: https://abc123.trycloudflare.com
🔗 API Base: https://abc123.trycloudflare.com/api/v1
```

**Use the Public URL in your Laravel/frontend!**

---

## Laravel Integration

1. **Get your public URL** (from `./scripts/manage.sh expose`)

2. **Add to Laravel .env:**
```env
CHATBOT_API_URL=https://abc123.trycloudflare.com
CHATBOT_API_BASE=https://abc123.trycloudflare.com/api/v1
```

3. **Use in Laravel:**
```php
use Illuminate\Support\Facades\Http;

$response = Http::post(env('CHATBOT_API_BASE') . '/chat/message', [
    'user_id' => 'user_001',
    'message' => 'What is the rental price?'
]);

$data = $response->json();
echo $data['response'];
```

**Full Laravel guide**: See `others/documentation/CLOUDFLARE_SETUP.md`

---

## API Quick Reference

### Send Message
```bash
curl -X POST https://your-tunnel-url.trycloudflare.com/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "What is the rental price?"
  }'
```

### Health Check
```bash
curl https://your-tunnel-url.trycloudflare.com/health
```

### API Documentation
Visit: `https://your-tunnel-url.trycloudflare.com/docs`

**Full API reference**: See `others/documentation/API_REFERENCE.md`

---

## Troubleshooting

### Check Status
```bash
./scripts/manage.sh status
```

### View Logs
```bash
tail -f logs/server.log
tail -f logs/tunnel.log
```

### Server Won't Start?
```bash
# Kill existing process
pkill -f "uvicorn backend.app.main:app"

# Try again
./scripts/manage.sh start
```

---

## Documentation

- **Cloudflare Setup**: `others/documentation/CLOUDFLARE_SETUP.md`
- **API Reference**: `others/documentation/API_REFERENCE.md`
- **Full Documentation**: `README.md`

---

**🎉 Ready to go! Run `./scripts/manage.sh expose` and you're live!**

