# Laravel Integration Guide for Neguinho Motors Chatbot

This guide explains how to integrate the Neguinho Motors chatbot widget into your Laravel website.

> **📚 For comprehensive tunnel options (Cloudflare Tunnel, localtunnel, ngrok), see [EXPOSE_TO_LARAVEL.md](./EXPOSE_TO_LARAVEL.md)**

## Quick Start Options

1. **Cloudflare Tunnel** (Recommended - Free & Unlimited) - See [EXPOSE_TO_LARAVEL.md](./EXPOSE_TO_LARAVEL.md)
2. **localtunnel** (Free & Unlimited) - See [EXPOSE_TO_LARAVEL.md](./EXPOSE_TO_LARAVEL.md)
3. **ngrok** (Free tier available) - See below or [EXPOSE_TO_LARAVEL.md](./EXPOSE_TO_LARAVEL.md)

## Prerequisites

1. **Chatbot Server Running**: The FastAPI chatbot server should be running on `http://localhost:8000`
2. **ngrok Installed**: Install ngrok from https://ngrok.com/
3. **Laravel Application**: Your Laravel website should be set up

## Step 1: Start ngrok Tunnel

1. Start your chatbot server:
```bash
cd /path/to/AiuraChatbot
source venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

2. In a new terminal, start ngrok:
```bash
ngrok http 8000
```

3. Copy the ngrok URL (e.g., `https://abc123.ngrok-free.app`)

## Step 2: Update CORS Settings (Optional)

The chatbot already allows all origins by default, but you can restrict it in `backend/config/settings.py`:

```python
cors_origins: List[str] = [
    "https://your-laravel-domain.com",
    "https://*.ngrok.io",
    "https://*.ngrok-free.app",
]
```

## Step 3: Create Laravel Blade Template

Create a new Blade template file: `resources/views/components/chatbot-widget.blade.php`

```blade
<!-- Neguinho Motors Chatbot Widget -->
<div id="chatbotWidgetContainer"></div>

<script>
    // Set your ngrok URL here
    window.CHATBOT_API_URL = '{{ env("CHATBOT_API_URL", "https://your-ngrok-url.ngrok-free.app/api/v1") }}';
    
    // Load widget script
    (function() {
        const script = document.createElement('script');
        script.src = '{{ env("CHATBOT_API_URL", "https://your-ngrok-url.ngrok-free.app") }}/static/widget.js';
        script.async = true;
        document.head.appendChild(script);
        
        // Load widget styles
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '{{ env("CHATBOT_API_URL", "https://your-ngrok-url.ngrok-free.app") }}/static/widget.css';
        document.head.appendChild(link);
    })();
</script>
```

## Step 4: Create Widget JavaScript File

Create `frontend/widget.js`:

```javascript
// Neguinho Motors Chatbot Widget
(function() {
    const CHATBOT_API_URL = window.CHATBOT_API_URL || 'http://localhost:8000/api/v1';
    
    // Create widget HTML
    const widgetHTML = `
        <div id="chatbotWidget" class="chatbot-widget">
            <div class="chatbot-header" onclick="window.toggleChatbotWidget()">
                <h3>Neguinho Motors Chatbot</h3>
                <button class="minimize-btn" onclick="event.stopPropagation(); window.toggleChatbotWidget();">−</button>
            </div>
            <div class="chatbot-messages" id="chatbotMessages">
                <div class="message assistant">
                    Hello! I'm the Neguinho Motors chatbot. How can I help you today?
                </div>
            </div>
            <div class="chatbot-input-container">
                <input type="text" class="chatbot-input" id="chatbotInput" placeholder="Type your message..." />
                <button class="chatbot-send" id="chatbotSend" onclick="window.sendChatbotMessage()">Send</button>
            </div>
        </div>
    `;
    
    // Inject widget into page
    document.body.insertAdjacentHTML('beforeend', widgetHTML);
    
    // Load styles
    const style = document.createElement('style');
    style.textContent = `
        .chatbot-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 380px;
            height: 600px;
            background: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            display: flex;
            flex-direction: column;
            z-index: 10000;
            border: 1px solid #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .chatbot-widget.minimized {
            height: 60px;
            width: 300px;
        }
        .chatbot-widget.minimized .chatbot-messages,
        .chatbot-widget.minimized .chatbot-input-container {
            display: none;
        }
        .chatbot-header {
            background: #2c3e50;
            color: white;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }
        .chatbot-header h3 {
            margin: 0;
            font-size: 1rem;
        }
        .minimize-btn {
            background: transparent;
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
        }
        .chatbot-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            background: #f9f9f9;
        }
        .message {
            max-width: 80%;
            padding: 0.75rem 1rem;
            word-wrap: break-word;
        }
        .message.user {
            align-self: flex-end;
            background: #3498db;
            color: white;
        }
        .message.assistant {
            align-self: flex-start;
            background: white;
            color: #2c3e50;
            border: 1px solid #e0e0e0;
        }
        .chatbot-input-container {
            padding: 1rem;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 0.5rem;
            background: white;
        }
        .chatbot-input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #ddd;
            font-size: 0.9rem;
        }
        .chatbot-send {
            padding: 0.75rem 1.5rem;
            background: #3498db;
            color: white;
            border: none;
            cursor: pointer;
        }
        .chatbot-send:hover {
            background: #2980b9;
        }
    `;
    document.head.appendChild(style);
    
    // Widget state
    let isMinimized = false;
    let userId = localStorage.getItem('chatbot_widget_userId');
    if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chatbot_widget_userId', userId);
    }
    let currentChatId = localStorage.getItem('chatbot_widget_currentChatId');
    
    // Functions
    window.toggleChatbotWidget = function() {
        const widget = document.getElementById('chatbotWidget');
        isMinimized = !isMinimized;
        widget.classList.toggle('minimized', isMinimized);
    };
    
    function generateChatId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    window.sendChatbotMessage = async function() {
        const input = document.getElementById('chatbotInput');
        const message = input.value.trim();
        if (!message) return;
        
        if (!currentChatId) {
            currentChatId = generateChatId();
        }
        
        addMessage('user', message);
        input.value = '';
        
        const sendButton = document.getElementById('chatbotSend');
        sendButton.disabled = true;
        sendButton.textContent = 'Sending...';
        
        try {
            const response = await fetch(`${CHATBOT_API_URL}/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    chat_id: currentChatId,
                    message: message
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.chat_id) {
                currentChatId = data.chat_id;
                localStorage.setItem('chatbot_widget_currentChatId', currentChatId);
            }
            
            addMessage('assistant', data.response);
            
            if (data.suggestions && data.suggestions.length > 0) {
                addSuggestions(data.suggestions);
            }
            
        } catch (error) {
            console.error('Error:', error);
            addMessage('assistant', `Sorry, I encountered an error: ${error.message}`);
        } finally {
            sendButton.disabled = false;
            sendButton.textContent = 'Send';
        }
    };
    
    function addMessage(role, content) {
        const container = document.getElementById('chatbotMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.innerHTML = content.replace(/\n/g, '<br>');
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
    }
    
    function addSuggestions(suggestions) {
        const container = document.getElementById('chatbotMessages');
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.style.marginTop = '1rem';
        suggestionsDiv.style.padding = '0.75rem';
        suggestionsDiv.style.background = 'rgba(52, 152, 219, 0.1)';
        suggestionsDiv.style.borderLeft = '3px solid #3498db';
        
        const title = document.createElement('div');
        title.style.fontSize = '0.85rem';
        title.style.fontWeight = 'bold';
        title.style.marginBottom = '0.5rem';
        title.style.color = '#3498db';
        title.textContent = 'You might also ask:';
        suggestionsDiv.appendChild(title);
        
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.textContent = suggestion;
            btn.style.display = 'block';
            btn.style.width = '100%';
            btn.style.marginBottom = '0.5rem';
            btn.style.padding = '0.5rem';
            btn.style.background = 'white';
            btn.style.border = '1px solid #3498db';
            btn.style.cursor = 'pointer';
            btn.style.textAlign = 'left';
            btn.onclick = () => {
                document.getElementById('chatbotInput').value = suggestion;
                window.sendChatbotMessage();
            };
            suggestionsDiv.appendChild(btn);
        });
        
        container.appendChild(suggestionsDiv);
        container.scrollTop = container.scrollHeight;
    }
    
    // Enter key support
    document.getElementById('chatbotInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            window.sendChatbotMessage();
        }
    });
})();
```

## Step 5: Add Widget to Laravel Layout

In your main layout file (e.g., `resources/views/layouts/app.blade.php`), add before `</body>`:

```blade
@include('components.chatbot-widget')
```

## Step 6: Configure Environment Variables

Add to your `.env` file:

```env
CHATBOT_API_URL=https://your-ngrok-url.ngrok-free.app
```

## Step 7: Serve Widget Files (Optional)

If you want to serve the widget files from the chatbot server, add to `backend/app/main.py`:

```python
@app.get("/static/widget.js")
async def serve_widget_js():
    """Serve widget JavaScript."""
    widget_path = Path(__file__).parent.parent.parent / "frontend" / "widget.js"
    if widget_path.exists():
        return FileResponse(str(widget_path), media_type="application/javascript")
    return {"error": "Widget not found"}

@app.get("/static/widget.css")
async def serve_widget_css():
    """Serve widget CSS."""
    widget_path = Path(__file__).parent.parent.parent / "frontend" / "widget.css"
    if widget_path.exists():
        return FileResponse(str(widget_path), media_type="text/css")
    return {"error": "Widget not found"}
```

## Alternative: Simple iframe Embed

For a simpler approach, you can embed the widget using an iframe:

```blade
<!-- In your Laravel blade template -->
<iframe 
    src="{{ env('CHATBOT_API_URL', 'https://your-ngrok-url.ngrok-free.app') }}/frontend/widget.html"
    width="380"
    height="600"
    style="position: fixed; bottom: 20px; right: 20px; border: none; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 10000;"
    allow="microphone"
></iframe>
```

## Testing

1. Start your chatbot server
2. Start ngrok: `ngrok http 8000`
3. Update `CHATBOT_API_URL` in Laravel `.env`
4. Visit your Laravel website
5. The chatbot widget should appear in the bottom-right corner

## API Endpoints

All endpoints are accessible via:
- `https://your-ngrok-url.ngrok-free.app/api/v1/chat/message` (POST)
- `https://your-ngrok-url.ngrok-free.app/api/v1/chat/chats/{user_id}` (GET)
- `https://your-ngrok-url.ngrok-free.app/api/v1/chat/history/{chat_id}` (GET)
- `https://your-ngrok-url.ngrok-free.app/api/v1/chat/clear/{chat_id}` (POST)

## Notes

- The widget uses localStorage with prefix `chatbot_widget_` to avoid conflicts
- Each user gets a unique `user_id` stored in localStorage
- Chat history persists across page refreshes
- The widget is responsive and works on mobile devices
- CORS is configured to allow requests from any origin (can be restricted in production)

## Alternative Tunnel Options

For better free and unlimited options, see **[EXPOSE_TO_LARAVEL.md](./EXPOSE_TO_LARAVEL.md)** which includes:
- **Cloudflare Tunnel** (Best option - Free, Unlimited, Stable URLs)
- **localtunnel** (Free, Unlimited, Quick Setup)
- Helper scripts in `scripts/` directory

