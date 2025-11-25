# MySQL Database Tables Report - aiura_chatbots

**Generated:** 2025-11-25  
**Database:** aiura_chatbots  
**Connection:** MySQL 9.4.0 (Homebrew) via root@localhost

## Summary

- **Total Tables:** 32
- **Database Size:** ~2.5 MB
- **Total Records:** ~1,040 records across all tables

## Table Categories

### ✅ Core Platform (5 tables)
- `admins` - **1 record**
- `vendors` - **2 records**  
- `users` - **80 records**
- `roles` - **4 records**
- `user_roles` - **1 record**

### ✅ Chat System (2 tables) ⚠️ MISSING 3 NEW TABLES
**Existing:**
- `chat_sessions` - **93 records**
- `chat_messages` - **543 records**

**❌ MISSING (Should be created):**
- `chat_users` - NEW table for end users who chat
- `conversation_memories` - NEW table for persistent memory
- `suggestion_cache` - NEW table for cached suggestions

### ✅ Models & LLM (3 tables) ⚠️ MISSING 1 TABLE
**Existing:**
- `models` - 6 records
- `model_configs` - 0 records
- `model_cache` - 0 records

**❌ MISSING:**
- `model_presets` - For model configuration presets

### ✅ Knowledge Base (3 tables)
- `knowledge_bases` - 2 records
- `kb_documents` - 44 records
- `kb_embeddings_refs` - 0 records

### ✅ Caching (2 tables)
- `main_cache` - **23 records**
- `temporary_cache` - **52 records**

### ✅ Billing (5 tables)
- `billing_plans` - **4 records**
- `quota_allocations` - **5 records**
- `usage_records` - **174 records**
- `invoices` - 0 records
- `payments` - 0 records

### ✅ Vendor Config (2 tables)
- `vendor_configs` - 3 records
- `vendor_endpoints` - 0 records

### ✅ API & Security (4 tables)
- `api_keys` - 0 records
- `rate_limits` - 0 records
- `ip_allowlist` - 0 records
- `webhook_deliveries` - 0 records

### ✅ System (6 tables)
- `vendor_model_assignments` - **4 records**
- `audit_logs` - 0 records
- `feature_flags` - 0 records
- `support_tickets` - 0 records
- `notifications` - 0 records
- `data_export_requests` - 0 records

## Complete Table List (32 tables)

1. admins
2. api_keys
3. audit_logs
4. billing_plans
5. chat_messages
6. chat_sessions
7. data_export_requests
8. feature_flags
9. invoices
10. ip_allowlist
11. kb_documents
12. kb_embeddings_refs
13. knowledge_bases
14. main_cache
15. model_cache
16. model_configs
17. models
18. notifications
19. payments
20. quota_allocations
21. rate_limits
22. roles
23. support_tickets
24. temporary_cache
25. usage_records
26. user_roles
27. users
28. vendor_configs
29. vendor_endpoints
30. vendor_model_assignments
31. vendors
32. webhook_deliveries

## Missing Tables (Should be created)

### Critical Missing Tables:
1. **`chat_users`** - Required for multi-vendor chat system
   - Stores end users who chat (separate from vendor users)
   - Links to `chat_sessions` via `chat_user_id`

2. **`conversation_memories`** - Required for persistent memory
   - Stores conversation memory per chat
   - Links to `chat_users` via `chat_user_id`

3. **`suggestion_cache`** - Required for cached suggestions
   - Stores cached suggestions with TTL
   - Links to `chat_users` via `chat_user_id`

### Optional Missing Tables:
4. **`model_presets`** - For model configuration presets

### Legacy Tables (Can be removed after migration):
- `chats` (replaced by `chat_sessions`)
- `messages` (replaced by `chat_messages`)
- `conversation_memory` (replaced by `conversation_memories`)
- `token_usage` (replaced by `usage_records`)

## Table Statistics

### Most Active Tables (by record count):
1. `chat_messages` - **543 records**
2. `usage_records` - **174 records**
3. `chat_sessions` - **93 records**
4. `users` - **80 records**
5. `temporary_cache` - **52 records**
6. `kb_documents` - **44 records**
7. `main_cache` - **23 records**
8. `billing_plans` - **4 records**
9. `quota_allocations` - **5 records**
10. `vendor_model_assignments` - **4 records**
11. `roles` - **4 records**
12. `models` - **6 records**
13. `vendor_configs` - **3 records**
14. `knowledge_bases` - **2 records**
15. `vendors` - **2 records**
16. `user_roles` - **1 record**
17. `admins` - **1 record**

### Empty Tables (0 records):
- `api_keys`
- `audit_logs`
- `data_export_requests`
- `feature_flags`
- `invoices`
- `ip_allowlist`
- `kb_embeddings_refs`
- `model_cache`
- `model_configs`
- `notifications`
- `payments`
- `rate_limits`
- `support_tickets`
- `user_roles`
- `vendor_endpoints`
- `webhook_deliveries`

## Recommendations

1. **Create Missing Tables:**
   - Run `scripts/create_chat_users_table.py` to create `chat_users`
   - Run `scripts/create_conversation_memory_table.py` to create `conversation_memories`
   - Create `suggestion_cache` table (if script exists)

2. **Migrate Data:**
   - Update `chat_sessions` to use `chat_user_id` instead of `user_id`
   - Migrate existing chat data to new structure

3. **Clean Up:**
   - Remove legacy tables after migration verification
   - Consider archiving old `chat_messages` if needed

4. **Verify Relationships:**
   - Ensure foreign keys are properly set up
   - Verify indexes for performance

## Connection Details

- **Host:** localhost:3306
- **User:** root (for admin access)
- **Database:** aiura_chatbots
- **Charset:** utf8mb4
- **MySQL Version:** 9.4.0 (Homebrew)

---

**Note:** This report was generated by connecting directly to the MySQL database using root credentials. For production, use the `aiura_chatbot` user with proper permissions.

