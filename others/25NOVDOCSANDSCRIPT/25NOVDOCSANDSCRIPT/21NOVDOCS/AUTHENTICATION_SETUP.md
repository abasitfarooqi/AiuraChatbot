# 🔐 Authentication System - Complete Setup Guide

## ✅ Status: Fully Operational

All authentication features have been implemented and tested successfully!

---

## 🎯 What's Been Implemented

### 1. **Authentication System**
- ✅ JWT token-based authentication
- ✅ Password hashing with bcrypt
- ✅ Super admin login
- ✅ Vendor admin login
- ✅ Token verification endpoints
- ✅ Secure logout functionality

### 2. **Role-Based Access Control**
- ✅ Super admin (full platform access)
- ✅ Vendor admin (vendor-specific access)
- ✅ Middleware for route protection
- ✅ Automatic token validation

### 3. **Vendor-Specific API Endpoints**
- ✅ `/api/v1/vendor-api/info` - Get vendor information
- ✅ `/api/v1/vendor-api/chat/message` - Send chat messages
- ✅ `/api/v1/vendor-api/chat/history/{chat_id}` - Get chat history
- ✅ `/api/v1/vendor-api/chat/sessions` - List chat sessions
- ✅ `/api/v1/vendor-api/endpoints` - Get available endpoints

### 4. **Frontend Integration**
- ✅ Login page (`/login.html`)
- ✅ Admin panel with authentication (`/admin.html`)
- ✅ Auto-redirect to login if not authenticated
- ✅ Token storage in localStorage
- ✅ Automatic token injection in API requests

---

## 🚀 Quick Start

### 1. **Start the Server**

```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
export USE_MYSQL=true
export MYSQL_USER=root
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots
export JWT_SECRET_KEY=your-secret-key-here

python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. **Access Login Page**

Open in browser:
```
http://127.0.0.1:8000/login.html
```

### 3. **Test Credentials**

#### Super Admin
- **Email:** `admin@aiurachatbot.com`
- **Password:** `admin123`

#### Vendor Admin (Neguinho Motors)
- **Email:** `admin@neguinhomotors.co.uk`
- **Password:** `neguinho123`
- **Vendor Slug:** `neguinho_motors` (optional)

---

## 📋 API Endpoints

### Authentication Endpoints

#### Super Admin Login
```http
POST /api/v1/auth/admin/login
Content-Type: application/json

{
  "email": "admin@aiurachatbot.com",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "admin_id": 1,
  "name": "Super Admin",
  "is_super": true,
  "expires_in": 86400
}
```

#### Vendor Admin Login
```http
POST /api/v1/auth/vendor-admin/login
Content-Type: application/json

{
  "email": "admin@neguinhomotors.co.uk",
  "password": "neguinho123",
  "vendor_slug": "neguinho_motors"  // Optional
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": 1,
  "vendor_id": 1,
  "vendor_slug": "neguinho_motors",
  "name": "Neguinho Admin",
  "expires_in": 86400
}
```

#### Verify Token
```http
GET /api/v1/auth/verify
Authorization: Bearer <token>
```

#### Get Current User Info
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### Vendor API Endpoints (For Separate Frontend)

All vendor API endpoints require authentication via Bearer token.

#### Get Vendor Info
```http
GET /api/v1/vendor-api/info
Authorization: Bearer <vendor_admin_token>
```

#### Send Chat Message
```http
POST /api/v1/vendor-api/chat/message
Authorization: Bearer <vendor_admin_token>
Content-Type: application/json

{
  "message": "Hello, do you offer delivery?",
  "chat_id": "optional-chat-id",
  "user_id": "optional-user-id"
}
```

#### Get Chat History
```http
GET /api/v1/vendor-api/chat/history/{chat_id}
Authorization: Bearer <vendor_admin_token>
```

#### List Chat Sessions
```http
GET /api/v1/vendor-api/chat/sessions?limit=50&offset=0
Authorization: Bearer <vendor_admin_token>
```

#### Get Available Endpoints
```http
GET /api/v1/vendor-api/endpoints
Authorization: Bearer <vendor_admin_token>
```

---

## 🔧 Setup Script

Run the setup script to create test users and vendors:

```bash
cd /Users/abdulbasit/Projects/HybridApps/AiuraChatbot
source venv/bin/activate
export USE_MYSQL=true
export MYSQL_USER=root
export MYSQL_PASSWORD=abc123
export MYSQL_DATABASE=aiura_chatbots

python3 scripts/setup_test_auth.py
```

This will create:
- ✅ Super admin: `admin@aiurachatbot.com` / `admin123`
- ✅ Neguinho Motors vendor
- ✅ Vendor admin: `admin@neguinhomotors.co.uk` / `neguinho123`

---

## 🌐 Frontend URLs

| Page | URL | Description |
|------|-----|-------------|
| **Login** | `http://127.0.0.1:8000/login.html` | Login page for admins |
| **Admin Panel** | `http://127.0.0.1:8000/admin.html` | Admin dashboard (requires login) |
| **Chatbot** | `http://127.0.0.1:8000/` | Main chatbot interface |
| **API Docs** | `http://127.0.0.1:8000/docs` | Interactive API documentation |

---

## 🔒 Security Features

1. **Password Hashing**: All passwords are hashed using bcrypt
2. **JWT Tokens**: Secure token-based authentication
3. **Token Expiration**: Tokens expire after 24 hours
4. **Role-Based Access**: Different permissions for super admin vs vendor admin
5. **Vendor Isolation**: Vendor admins can only access their own vendor's data

---

## 📝 Database Structure

### Admins Table
- Super admins and platform admins
- Email/password authentication
- `is_super` flag for super admin privileges

### Users Table
- Vendor-specific users
- Linked to vendors via `vendor_id`
- Can have roles assigned

### Roles Table
- RBAC roles (e.g., `vendor_admin`)
- Permissions stored as JSON

### UserRole Table
- Links users to roles
- Vendor-scoped role assignments

---

## 🧪 Testing

All endpoints have been tested and verified:

✅ Health check  
✅ Login page accessible  
✅ Admin page accessible  
✅ Vendor list loading  
✅ Super admin login  
✅ Vendor admin login  
✅ Token verification  
✅ Vendor API endpoints  

---

## 🎉 Ready to Use!

The authentication system is fully functional. You can now:

1. **Login** at `http://127.0.0.1:8000/login.html`
2. **Access admin panel** after login
3. **Use vendor API endpoints** for separate frontend integration
4. **Manage vendors** through the admin interface

**Neguinho Motors chatbot is already loaded and ready!**

---

## 📞 Support

If you encounter any issues:
1. Check server logs
2. Verify database connection
3. Ensure all environment variables are set
4. Run `scripts/setup_test_auth.py` to reset test data

