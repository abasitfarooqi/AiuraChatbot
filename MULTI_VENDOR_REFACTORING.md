# Multi-Vendor Refactoring Summary

## Overview
The project has been fully refactored to be a dynamic, multi-vendor system with proper separation between:
- **Admins**: Platform administrators (you)
- **Users**: Vendor users (with roles and levels)
- **Chat Users**: Users who actually chat (separate from vendor users)

## Key Changes

### 1. New Table: `chat_users`
Created a new `chat_users` table to store users who actually chat, separate from vendor users.

**Schema:**
- `id`: Primary key
- `vendor_id`: Foreign key to vendors (which vendor this chat user belongs to)
- `identifier`: Email, phone, or anonymous ID (unique per vendor)
- `name`: Optional name
- `email`: Optional email
- `phone`: Optional phone
- `is_anonymous`: Boolean (true for anonymous chat users)
- `meta`: JSON metadata
- `created_at`, `updated_at`, `last_chat_at`: Timestamps

**Unique Constraint:** `(vendor_id, identifier)` - ensures one chat_user per identifier per vendor

### 2. Updated Tables

#### `chat_sessions`
- **Changed:** `user_id` → `chat_user_id`
- **Removed:** Foreign key to `users` table
- **Added:** Foreign key to `chat_users` table
- **Relationship:** Now links to `ChatUser` instead of `User`

#### `conversation_memories`
- **Changed:** `user_id` → `chat_user_id`
- **Removed:** Foreign key to `users` table
- **Added:** Foreign key to `chat_users` table (optional)
- **Relationship:** Now links to `ChatUser` instead of `User`

#### `suggestion_cache`
- **Changed:** `user_id` → `chat_user_id`
- **Removed:** Foreign key to `users` table
- **Added:** Foreign key to `chat_users` table (optional)
- **Relationship:** Now links to `ChatUser` instead of `User`

### 3. Updated Services

#### `MemoryService`
- `get_or_create_memory()`: Now accepts `chat_user_id` instead of `user_id`
- `update_memory()`: Now accepts `chat_user_id` instead of `user_id`
- All methods are vendor-aware and dynamic

#### `SuggestionService`
- `get_cached_suggestions()`: Now accepts `chat_user_id` instead of `user_id`
- `cache_suggestions()`: Now accepts `chat_user_id` instead of `user_id`
- `clear_all_suggestions()`: Now accepts `chat_user_id` instead of `user_id`

#### `ChatbotService`
- Updated to use `chat_user_id` from chat sessions
- All memory and suggestion operations use `chat_user_id`

### 4. Updated API Endpoints

#### `/api/v1/chat`
- `send_message()`: Creates/gets `ChatUser` instead of `User`
- `get_user_chats()`: Queries by `ChatUser` instead of `User`

#### `/api/v1/memory`
- All endpoints now use `chat_user_id` parameter instead of `user_id`
- Removed hardcoded "neguinho_motors" references
- Uses `settings.default_vendor_id` dynamically

#### `/api/v1/cache`
- `get_temporary_cache()`: Now accepts `chat_user_id` instead of `user_id`
- `get_main_cache()`: Removed `user_id` parameter (main cache is vendor-wide)

### 5. Removed Hardcoded Vendor References

All hardcoded "neguinho_motors" references have been replaced with:
- `settings.default_vendor_id` (from config)
- Dynamic vendor resolution from request parameters

**Files Updated:**
- `backend/api/memory.py`: All endpoints now use `settings.default_vendor_id`
- `backend/api/chat.py`: Uses dynamic vendor resolution
- `backend/services/memory_service.py`: Fully dynamic
- `backend/services/suggestion_service.py`: Fully dynamic
- `backend/services/chatbot_service.py`: Fully dynamic

### 6. Migration Scripts

#### `scripts/create_chat_users_table.py`
Creates the `chat_users` table in the database.

#### `scripts/migrate_to_chat_users.py`
Migrates existing data:
1. Creates `chat_users` table
2. Migrates existing `chat_sessions` to use `chat_users`
3. Migrates `conversation_memories` to use `chat_users`
4. Migrates `suggestion_cache` to use `chat_users`

## Database Schema Changes

### New Table: `chat_users`
```sql
CREATE TABLE chat_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER NOT NULL,
    identifier VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    is_anonymous BOOLEAN DEFAULT TRUE,
    meta JSON,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    last_chat_at DATETIME,
    FOREIGN KEY (vendor_id) REFERENCES vendors(id),
    UNIQUE (vendor_id, identifier)
);
```

### Modified Tables

#### `chat_sessions`
- **Removed:** `user_id` column
- **Added:** `chat_user_id` column (NOT NULL)

#### `conversation_memories`
- **Removed:** `user_id` column
- **Added:** `chat_user_id` column (nullable)

#### `suggestion_cache`
- **Removed:** `user_id` column
- **Added:** `chat_user_id` column (nullable)

## User Hierarchy

1. **Admins** (`admins` table)
   - Platform administrators
   - Full system access

2. **Users** (`users` table)
   - Vendor users (employees, managers, etc.)
   - Have roles and permissions
   - Can manage vendor settings

3. **Chat Users** (`chat_users` table)
   - End users who chat with the bot
   - Can be anonymous or identified
   - Linked to a specific vendor
   - Separate from vendor users

## Running Migrations

1. **Create chat_users table:**
   ```bash
   python3 scripts/create_chat_users_table.py
   ```

2. **Migrate existing data:**
   ```bash
   python3 scripts/migrate_to_chat_users.py
   ```

3. **Create conversation_memories and suggestion_cache tables (if not exists):**
   ```bash
   python3 scripts/create_conversation_memory_table.py
   ```

## Testing Checklist

- [ ] Run migration scripts
- [ ] Verify `chat_users` table exists
- [ ] Verify `chat_sessions` uses `chat_user_id`
- [ ] Verify `conversation_memories` uses `chat_user_id`
- [ ] Verify `suggestion_cache` uses `chat_user_id`
- [ ] Test creating a new chat session
- [ ] Test memory operations
- [ ] Test cache operations
- [ ] Test with multiple vendors
- [ ] Verify no hardcoded vendor references remain

## Notes

- All vendor references are now dynamic
- Default vendor is loaded from `settings.default_vendor_id`
- Chat users are automatically created when a new chat session starts
- Chat users are vendor-specific (same identifier can exist for different vendors)
- All services are fully multi-vendor compatible

