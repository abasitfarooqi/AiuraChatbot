# 🌐 Cloudflare Tunnel Setup Guide

## Quick Start - One Command

```bash
./scripts/manage.sh expose
```

This single command will:
1. ✅ Start the chatbot server (if not running)
2. ✅ Start Cloudflare tunnel
3. ✅ Give you a public HTTPS URL
4. ✅ Show API endpoints ready for Laravel/frontend

---

## Installation

### Step 1: Install Cloudflare Tunnel

**macOS (Homebrew):**
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux:**
```bash
# Download binary
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

**Windows:**
Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

### Step 2: Verify Installation

```bash
cloudflared --version
```

---

## Management Commands

### Start Everything (Server + Tunnel)
```bash
./scripts/manage.sh expose
```

### Start Server Only
```bash
./scripts/manage.sh start
```

### Start Tunnel Only (server must be running)
```bash
./scripts/manage.sh tunnel start
```

### Check Status
```bash
./scripts/manage.sh status
```

### Stop Server
```bash
./scripts/manage.sh stop
```

### Stop Tunnel
```bash
./scripts/manage.sh tunnel stop
```

### Restart Server
```bash
./scripts/manage.sh restart
```

---

## What You Get

After running `./scripts/manage.sh expose`, you'll see:

```
✅ Server started successfully (PID: 12345)
📍 Server URL: http://localhost:8000
📚 API Docs: http://localhost:8000/docs
💚 Health: http://localhost:8000/health

✅ Tunnel started successfully
🌍 Public URL: https://abc123.trycloudflare.com
📚 API Docs: https://abc123.trycloudflare.com/docs
💚 Health: https://abc123.trycloudflare.com/health
🔗 API Base: https://abc123.trycloudflare.com/api/v1
```

**Use the Public URL in your Laravel frontend!**

---

## API Endpoints

### Base URL
- **Local**: `http://localhost:8000`
- **Public (via tunnel)**: `https://your-tunnel-url.trycloudflare.com`

### Main Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### 2. Send Chat Message
```http
POST /api/v1/chat/message
Content-Type: application/json
```

**Request:**
```json
{
  "user_id": "user_001",
  "message": "What is the rental price for Honda PCX 125?",
  "chat_id": "chat_001",
  "vendor_id": "default"
}
```

**Response:**
```json
{
  "response": "Honda PCX 125 rental starts from £75 per week...",
  "chat_id": "chat_001",
  "message_id": "msg_123",
  "tokens_used": 150,
  "credits_used": 2,
  "model_used": "mistral",
  "retrieved_chunks": 3,
  "is_domain_relevant": true,
  "suggestions": [
    "Tell me about finance options",
    "What are your opening hours?"
  ]
}
```

#### 3. Get Chat History
```http
GET /api/v1/chat/history/{chat_id}
```

#### 4. Get User Chats
```http
GET /api/v1/chat/chats/{user_id}
```

#### 5. API Documentation
```http
GET /docs
```
Interactive Swagger UI for testing all endpoints.

---

## Laravel Integration

### Step 1: Get Your Public URL

Run:
```bash
./scripts/manage.sh expose
```

Copy the **Public URL** (e.g., `https://abc123.trycloudflare.com`)

### Step 2: Configure Laravel

**Option A: Environment Variable (.env)**
```env
CHATBOT_API_URL=https://abc123.trycloudflare.com
CHATBOT_API_BASE=https://abc123.trycloudflare.com/api/v1
```

**Option B: Config File (config/chatbot.php)**
```php
<?php

return [
    'api_url' => env('CHATBOT_API_URL', 'https://abc123.trycloudflare.com'),
    'api_base' => env('CHATBOT_API_BASE', 'https://abc123.trycloudflare.com/api/v1'),
];
```

### Step 3: Create Laravel Service

**app/Services/ChatbotService.php:**
```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class ChatbotService
{
    protected $apiBase;

    public function __construct()
    {
        $this->apiBase = config('chatbot.api_base', env('CHATBOT_API_BASE'));
    }

    public function sendMessage($userId, $message, $chatId = null, $vendorId = 'default')
    {
        try {
            $response = Http::timeout(30)->post("{$this->apiBase}/chat/message", [
                'user_id' => $userId,
                'message' => $message,
                'chat_id' => $chatId,
                'vendor_id' => $vendorId,
            ]);

            if ($response->successful()) {
                return $response->json();
            }

            Log::error('Chatbot API Error', [
                'status' => $response->status(),
                'body' => $response->body(),
            ]);

            return null;
        } catch (\Exception $e) {
            Log::error('Chatbot Service Exception', [
                'message' => $e->getMessage(),
            ]);
            return null;
        }
    }

    public function getChatHistory($chatId)
    {
        try {
            $response = Http::timeout(30)->get("{$this->apiBase}/chat/history/{$chatId}");
            
            if ($response->successful()) {
                return $response->json();
            }

            return null;
        } catch (\Exception $e) {
            Log::error('Chatbot History Error', ['error' => $e->getMessage()]);
            return null;
        }
    }

    public function getUserChats($userId)
    {
        try {
            $response = Http::timeout(30)->get("{$this->apiBase}/chat/chats/{$userId}");
            
            if ($response->successful()) {
                return $response->json();
            }

            return null;
        } catch (\Exception $e) {
            Log::error('Chatbot Chats Error', ['error' => $e->getMessage()]);
            return null;
        }
    }
}
```

### Step 4: Create Laravel Controller

**app/Http/Controllers/ChatbotController.php:**
```php
<?php

namespace App\Http\Controllers;

use App\Services\ChatbotService;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class ChatbotController extends Controller
{
    protected $chatbotService;

    public function __construct(ChatbotService $chatbotService)
    {
        $this->chatbotService = $chatbotService;
    }

    public function sendMessage(Request $request): JsonResponse
    {
        $request->validate([
            'message' => 'required|string',
            'user_id' => 'required|string',
            'chat_id' => 'nullable|string',
        ]);

        $result = $this->chatbotService->sendMessage(
            $request->user_id,
            $request->message,
            $request->chat_id
        );

        if ($result) {
            return response()->json($result);
        }

        return response()->json([
            'error' => 'Failed to get response from chatbot'
        ], 500);
    }

    public function getHistory($chatId): JsonResponse
    {
        $history = $this->chatbotService->getChatHistory($chatId);
        
        if ($history) {
            return response()->json($history);
        }

        return response()->json(['error' => 'Chat not found'], 404);
    }

    public function getUserChats($userId): JsonResponse
    {
        $chats = $this->chatbotService->getUserChats($userId);
        
        if ($chats) {
            return response()->json($chats);
        }

        return response()->json(['error' => 'User not found'], 404);
    }
}
```

### Step 5: Add Routes

**routes/api.php:**
```php
use App\Http\Controllers\ChatbotController;

Route::prefix('chatbot')->group(function () {
    Route::post('/message', [ChatbotController::class, 'sendMessage']);
    Route::get('/history/{chatId}', [ChatbotController::class, 'getHistory']);
    Route::get('/chats/{userId}', [ChatbotController::class, 'getUserChats']);
});
```

### Step 6: Frontend JavaScript Example

```javascript
const CHATBOT_API = 'https://abc123.trycloudflare.com/api/v1';

async function sendMessage(userId, message, chatId = null) {
    try {
        const response = await fetch(`${CHATBOT_API}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                message: message,
                chat_id: chatId,
                vendor_id: 'default'
            })
        });

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Chatbot error:', error);
        return null;
    }
}

// Usage
const result = await sendMessage('user_001', 'What is the rental price?');
console.log(result.response);
```

---

## Other Frontend Integration

### JavaScript/Fetch
```javascript
fetch('https://your-tunnel-url.trycloudflare.com/api/v1/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: 'user_001',
        message: 'Hello!'
    })
})
.then(res => res.json())
.then(data => console.log(data.response));
```

### cURL
```bash
curl -X POST https://your-tunnel-url.trycloudflare.com/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "message": "What is the rental price?"
  }'
```

### Python
```python
import requests

url = "https://your-tunnel-url.trycloudflare.com/api/v1/chat/message"
response = requests.post(url, json={
    "user_id": "user_001",
    "message": "What is the rental price?"
})
print(response.json())
```

---

## Troubleshooting

### Tunnel URL Changes Every Time?
This is normal for free Cloudflare tunnels. For a stable URL, set up a named tunnel:
```bash
cloudflared tunnel create chatbot-tunnel
cloudflared tunnel route dns chatbot-tunnel yourdomain.com
```

### Server Not Starting?
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
pkill -f "uvicorn backend.app.main:app"

# Try starting again
./scripts/manage.sh start
```

### Tunnel Not Connecting?
1. Make sure server is running: `./scripts/manage.sh status`
2. Check server logs: `tail -f logs/server.log`
3. Check tunnel logs: `tail -f logs/tunnel.log`

### CORS Issues?
The server is configured to allow all origins. If you still have issues, check:
- Server is running
- Tunnel URL is correct
- Using HTTPS (Cloudflare provides HTTPS automatically)

---

## Persistent Tunnel Setup (Optional)

For a stable URL that doesn't change:

1. **Create Named Tunnel:**
```bash
cloudflared tunnel create chatbot-tunnel
```

2. **Configure Tunnel:**
Create `~/.cloudflared/config.yml`:
```yaml
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: chatbot.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

3. **Route DNS:**
```bash
cloudflared tunnel route dns chatbot-tunnel chatbot.yourdomain.com
```

4. **Run Tunnel:**
```bash
cloudflared tunnel run chatbot-tunnel
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `./scripts/manage.sh expose` | Start server + tunnel (recommended) |
| `./scripts/manage.sh start` | Start server only |
| `./scripts/manage.sh stop` | Stop server |
| `./scripts/manage.sh restart` | Restart server |
| `./scripts/manage.sh status` | Check status |
| `./scripts/manage.sh tunnel start` | Start tunnel only |
| `./scripts/manage.sh tunnel stop` | Stop tunnel |

---

## Support

- **API Docs**: `https://your-tunnel-url/docs`
- **Health Check**: `https://your-tunnel-url/health`
- **Logs**: `tail -f logs/server.log` and `tail -f logs/tunnel.log`

