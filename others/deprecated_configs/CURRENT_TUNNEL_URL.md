# 🌍 Current Tunnel URL

## Your Public Chatbot URL

**Public URL:** `https://incident-military-later-certainly.trycloudflare.com`

---

## API Endpoints

### Base URLs
- **Public URL**: `https://incident-military-later-certainly.trycloudflare.com`
- **API Base**: `https://incident-military-later-certainly.trycloudflare.com/api/v1`
- **API Docs**: `https://incident-military-later-certainly.trycloudflare.com/docs`
- **Health Check**: `https://incident-military-later-certainly.trycloudflare.com/health`

---

## Laravel Configuration

Add to your Laravel `.env` file:

```env
CHATBOT_API_URL=https://incident-military-later-certainly.trycloudflare.com
CHATBOT_API_BASE=https://incident-military-later-certainly.trycloudflare.com/api/v1
```

---

## Quick Test

### Health Check
```bash
curl https://incident-military-later-certainly.trycloudflare.com/health
```

### Send Message
```bash
curl -X POST https://incident-military-later-certainly.trycloudflare.com/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "What is the rental price?"
  }'
```

---

## Get Current URL

Run:
```bash
./scripts/get-tunnel-url.sh
```

Or check status:
```bash
./scripts/manage.sh status
```

---

**Note:** This URL may change if you restart the tunnel. Run `./scripts/manage.sh expose` to get a new URL.

