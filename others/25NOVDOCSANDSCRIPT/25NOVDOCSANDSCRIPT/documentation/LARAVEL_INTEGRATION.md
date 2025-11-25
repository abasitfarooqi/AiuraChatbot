# 🔗 Laravel Integration Guide

## Quick Setup (5 Minutes)

### Step 1: Start Chatbot Backend

```bash
cd /path/to/AiuraChatbot
./scripts/manage.sh expose
```

Copy the **Public URL** (e.g., `https://abc123.trycloudflare.com`)

### Step 2: Configure Laravel

**Add to `.env`:**
```env
CHATBOT_API_URL=https://abc123.trycloudflare.com
CHATBOT_API_BASE=https://abc123.trycloudflare.com/api/v1
```

**Create config file `config/chatbot.php`:**
```php
<?php

return [
    'api_url' => env('CHATBOT_API_URL'),
    'api_base' => env('CHATBOT_API_BASE'),
    'timeout' => env('CHATBOT_TIMEOUT', 30),
];
```

### Step 3: Create Service

**`app/Services/ChatbotService.php`:**
```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Cache;

class ChatbotService
{
    protected $apiBase;
    protected $timeout;

    public function __construct()
    {
        $this->apiBase = config('chatbot.api_base');
        $this->timeout = config('chatbot.timeout', 30);
    }

    /**
     * Send a message to the chatbot
     */
    public function sendMessage(string $userId, string $message, ?string $chatId = null, string $vendorId = 'default'): ?array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->post("{$this->apiBase}/chat/message", [
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
                'trace' => $e->getTraceAsString(),
            ]);
            return null;
        }
    }

    /**
     * Get chat history
     */
    public function getChatHistory(string $chatId, int $limit = 50): ?array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->get("{$this->apiBase}/chat/history/{$chatId}", [
                    'limit' => $limit,
                ]);

            if ($response->successful()) {
                return $response->json();
            }

            return null;
        } catch (\Exception $e) {
            Log::error('Chatbot History Error', ['error' => $e->getMessage()]);
            return null;
        }
    }

    /**
     * Get all chats for a user
     */
    public function getUserChats(string $userId): ?array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->get("{$this->apiBase}/chat/chats/{$userId}");

            if ($response->successful()) {
                return $response->json();
            }

            return null;
        } catch (\Exception $e) {
            Log::error('Chatbot Chats Error', ['error' => $e->getMessage()]);
            return null;
        }
    }

    /**
     * Delete a chat
     */
    public function deleteChat(string $chatId): bool
    {
        try {
            $response = Http::timeout($this->timeout)
                ->delete("{$this->apiBase}/chat/delete/{$chatId}");

            return $response->successful();
        } catch (\Exception $e) {
            Log::error('Chatbot Delete Error', ['error' => $e->getMessage()]);
            return false;
        }
    }

    /**
     * Check chatbot health
     */
    public function healthCheck(): bool
    {
        try {
            $url = config('chatbot.api_url');
            $response = Http::timeout(5)->get("{$url}/health");
            return $response->successful();
        } catch (\Exception $e) {
            return false;
        }
    }
}
```

### Step 4: Create Controller

**`app/Http/Controllers/ChatbotController.php`:**
```php
<?php

namespace App\Http\Controllers;

use App\Services\ChatbotService;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Validator;

class ChatbotController extends Controller
{
    protected $chatbotService;

    public function __construct(ChatbotService $chatbotService)
    {
        $this->chatbotService = $chatbotService;
    }

    /**
     * Send a message to the chatbot
     */
    public function sendMessage(Request $request): JsonResponse
    {
        $validator = Validator::make($request->all(), [
            'message' => 'required|string|max:1000',
            'user_id' => 'required|string|max:100',
            'chat_id' => 'nullable|string|max:100',
            'vendor_id' => 'nullable|string|max:50',
        ]);

        if ($validator->fails()) {
            return response()->json([
                'error' => 'Validation failed',
                'errors' => $validator->errors()
            ], 422);
        }

        $result = $this->chatbotService->sendMessage(
            $request->user_id,
            $request->message,
            $request->chat_id,
            $request->vendor_id ?? 'default'
        );

        if ($result) {
            return response()->json($result);
        }

        return response()->json([
            'error' => 'Failed to get response from chatbot',
            'message' => 'The chatbot service is temporarily unavailable. Please try again later.'
        ], 503);
    }

    /**
     * Get chat history
     */
    public function getHistory(Request $request, string $chatId): JsonResponse
    {
        $limit = $request->get('limit', 50);
        $history = $this->chatbotService->getChatHistory($chatId, $limit);

        if ($history) {
            return response()->json($history);
        }

        return response()->json([
            'error' => 'Chat not found'
        ], 404);
    }

    /**
     * Get all chats for a user
     */
    public function getUserChats(string $userId): JsonResponse
    {
        $chats = $this->chatbotService->getUserChats($userId);

        if ($chats) {
            return response()->json($chats);
        }

        return response()->json([
            'error' => 'User not found'
        ], 404);
    }

    /**
     * Delete a chat
     */
    public function deleteChat(string $chatId): JsonResponse
    {
        $success = $this->chatbotService->deleteChat($chatId);

        if ($success) {
            return response()->json([
                'status' => 'success',
                'message' => 'Chat deleted successfully'
            ]);
        }

        return response()->json([
            'error' => 'Failed to delete chat'
        ], 500);
    }

    /**
     * Health check
     */
    public function health(): JsonResponse
    {
        $healthy = $this->chatbotService->healthCheck();

        return response()->json([
            'status' => $healthy ? 'healthy' : 'unhealthy',
            'service' => 'chatbot'
        ], $healthy ? 200 : 503);
    }
}
```

### Step 5: Add Routes

**`routes/api.php`:**
```php
use App\Http\Controllers\ChatbotController;

Route::prefix('chatbot')->group(function () {
    Route::post('/message', [ChatbotController::class, 'sendMessage']);
    Route::get('/history/{chatId}', [ChatbotController::class, 'getHistory']);
    Route::get('/chats/{userId}', [ChatbotController::class, 'getUserChats']);
    Route::delete('/delete/{chatId}', [ChatbotController::class, 'deleteChat']);
    Route::get('/health', [ChatbotController::class, 'health']);
});
```

**Or for web routes `routes/web.php`:**
```php
Route::prefix('api/chatbot')->group(function () {
    Route::post('/message', [ChatbotController::class, 'sendMessage']);
    Route::get('/history/{chatId}', [ChatbotController::class, 'getHistory']);
    Route::get('/chats/{userId}', [ChatbotController::class, 'getUserChats']);
    Route::delete('/delete/{chatId}', [ChatbotController::class, 'deleteChat']);
    Route::get('/health', [ChatbotController::class, 'health']);
});
```

---

## Frontend Usage

### Blade Template Example

```blade
<div id="chat-container">
    <div id="messages"></div>
    <form id="chat-form">
        <input type="text" id="message-input" placeholder="Type your message...">
        <button type="submit">Send</button>
    </form>
</div>

<script>
const CHATBOT_API = '{{ config('chatbot.api_base') }}';
const USER_ID = '{{ auth()->id() }}';
let currentChatId = null;

document.getElementById('chat-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = document.getElementById('message-input').value;
    
    const response = await fetch('/api/chatbot/message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': '{{ csrf_token() }}'
        },
        body: JSON.stringify({
            user_id: USER_ID,
            message: message,
            chat_id: currentChatId
        })
    });
    
    const data = await response.json();
    
    if (data.chat_id) {
        currentChatId = data.chat_id;
    }
    
    // Display response
    document.getElementById('messages').innerHTML += 
        `<div>You: ${message}</div>` +
        `<div>Bot: ${data.response}</div>`;
    
    document.getElementById('message-input').value = '';
});
</script>
```

### Vue.js Example

```vue
<template>
  <div class="chat-container">
    <div class="messages">
      <div v-for="msg in messages" :key="msg.id" :class="msg.role">
        {{ msg.content }}
      </div>
    </div>
    <form @submit.prevent="sendMessage">
      <input v-model="inputMessage" placeholder="Type your message...">
      <button type="submit">Send</button>
    </form>
  </div>
</template>

<script>
export default {
  data() {
    return {
      messages: [],
      inputMessage: '',
      chatId: null,
      userId: 'user_001'
    }
  },
  methods: {
    async sendMessage() {
      if (!this.inputMessage.trim()) return;
      
      // Add user message
      this.messages.push({
        id: Date.now(),
        role: 'user',
        content: this.inputMessage
      });
      
      try {
        const response = await axios.post('/api/chatbot/message', {
          user_id: this.userId,
          message: this.inputMessage,
          chat_id: this.chatId
        });
        
        if (response.data.chat_id) {
          this.chatId = response.data.chat_id;
        }
        
        // Add bot response
        this.messages.push({
          id: Date.now() + 1,
          role: 'assistant',
          content: response.data.response
        });
        
        this.inputMessage = '';
      } catch (error) {
        console.error('Chatbot error:', error);
        alert('Failed to send message. Please try again.');
      }
    }
  }
}
</script>
```

### React Example

```jsx
import React, { useState } from 'react';
import axios from 'axios';

function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [chatId, setChatId] = useState(null);
  const userId = 'user_001';

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);

    try {
      const response = await axios.post('/api/chatbot/message', {
        user_id: userId,
        message: input,
        chat_id: chatId
      });

      if (response.data.chat_id) {
        setChatId(response.data.chat_id);
      }

      // Add bot response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.response
      }]);

      setInput('');
    } catch (error) {
      console.error('Chatbot error:', error);
      alert('Failed to send message');
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
      <form onSubmit={sendMessage}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}

export default Chatbot;
```

---

## Request/Response Examples

### Send Message Request
```http
POST /api/chatbot/message
Content-Type: application/json

{
  "user_id": "user_001",
  "message": "What is the rental price for Honda PCX 125?",
  "chat_id": "chat_001",
  "vendor_id": "default"
}
```

### Send Message Response
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

---

## Error Handling

The service returns `null` on errors. Always check:

```php
$result = $chatbotService->sendMessage($userId, $message);

if ($result) {
    // Success
    $response = $result['response'];
} else {
    // Error - service unavailable or API error
    // Log error or show user-friendly message
}
```

---

## Testing

### Test in Tinker
```php
php artisan tinker

$service = app(\App\Services\ChatbotService::class);
$result = $service->sendMessage('test_user', 'Hello!');
dd($result);
```

### Test with cURL
```bash
curl -X POST http://your-laravel-app.test/api/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "What is the rental price?"
  }'
```

---

## Best Practices

1. **Cache Health Checks**: Don't check health on every request
2. **Set Timeouts**: API calls can take 5-30 seconds
3. **Handle Errors Gracefully**: Show user-friendly messages
4. **Log Errors**: Monitor chatbot service availability
5. **Reuse Chat IDs**: For conversation continuity
6. **Validate Input**: Always validate user input before sending

---

## Production Considerations

1. **Add Authentication**: Protect your chatbot endpoints
2. **Rate Limiting**: Prevent abuse
3. **Queue Jobs**: For better performance, use Laravel queues
4. **Monitoring**: Track API response times and errors
5. **Fallback**: Handle chatbot unavailability gracefully

---

## Support

- **API Docs**: `https://your-tunnel-url/docs`
- **Health Check**: `https://your-tunnel-url/health`
- **Full API Reference**: See `API_REFERENCE.md`
