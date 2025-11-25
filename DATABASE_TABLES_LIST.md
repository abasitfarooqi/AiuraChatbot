# Database Tables List - aiura_chatbots

## Overview
Total Tables: **40**

## Table Categories

### 1. Core Platform Tables (5)
1. **admins** - Platform super admin accounts
2. **vendors** - Vendor/tenant accounts
3. **users** - Vendor users (employees, managers, etc.)
4. **roles** - RBAC roles
5. **user_roles** - User-role assignments (RBAC)

### 2. Chat & Messaging Tables (5)
6. **chat_users** - Users who chat (separate from vendor users) ✅ NEW
7. **chat_sessions** - Chat sessions (linked to chat_users)
8. **chat_messages** - Chat messages
9. **conversation_memories** - Persistent conversation memory ✅ NEW
10. **suggestion_cache** - Cached suggestions with TTL ✅ NEW

### 3. Legacy Chat Tables (3) ⚠️ Can be removed after migration
11. **chats** - Old chat table (legacy)
12. **messages** - Old messages table (legacy)
13. **conversation_memory** - Old memory table (legacy)

### 4. Models & LLM Tables (4)
14. **models** - Central registry of available LLM models
15. **model_configs** - Model configuration per vendor
16. **model_presets** - Model configuration presets
17. **model_cache** - Model response cache per vendor

### 5. Knowledge Base & RAG Tables (3)
18. **knowledge_bases** - Knowledge bases per vendor
19. **kb_documents** - Documents in knowledge bases
20. **kb_embeddings_refs** - References to embeddings in vector DB

### 6. Caching Tables (3)
21. **main_cache** - Main persistent cache for Q&A pairs per vendor
22. **temporary_cache** - Temporary cache for Q&A pairs per chat session
23. **token_usage** - Token usage tracking (legacy) ⚠️

### 7. Billing & Quotas Tables (5)
24. **billing_plans** - Billing plan definitions
25. **quota_allocations** - Vendor-level quota allocations
26. **usage_records** - Atomic usage events for metering and billing
27. **invoices** - Invoices for vendors
28. **payments** - Payment records

### 8. Vendor Configuration Tables (2)
29. **vendor_configs** - Flexible per-vendor configuration
30. **vendor_endpoints** - Vendor webhook endpoints

### 9. API & Security Tables (4)
31. **api_keys** - API keys for vendor API access
32. **rate_limits** - Rate limits per vendor or API key
33. **ip_allowlist** - IP allowlist/blocklist
34. **webhook_deliveries** - Webhook delivery logs

### 10. Vendor Model Assignments (1)
35. **vendor_model_assignments** - Model assignments per vendor with limits

### 11. System & Admin Tables (4)
36. **audit_logs** - Immutable audit trail
37. **feature_flags** - Feature flags for gating features
38. **support_tickets** - Support tickets / helpdesk
39. **notifications** - Notifications (in-app and email logs)

### 12. Compliance Tables (1)
40. **data_export_requests** - Data export requests for compliance

---

## Table Details

### ✅ Active Tables (37)

#### Core Platform
- `admins` - Platform administrators
- `vendors` - Multi-tenant vendors
- `users` - Vendor-side users (with roles)
- `roles` - RBAC roles
- `user_roles` - User-role mappings

#### Chat System (New Multi-Vendor Architecture)
- `chat_users` - End users who chat (separate from vendor users)
- `chat_sessions` - Chat sessions (linked to chat_users via chat_user_id)
- `chat_messages` - Messages in chat sessions
- `conversation_memories` - Persistent memory per chat (linked to chat_users)
- `suggestion_cache` - Cached suggestions (linked to chat_users)

#### Models & LLM
- `models` - Available LLM models registry
- `model_configs` - Model configuration (vendor-specific)
- `model_presets` - Model presets for quick switching
- `model_cache` - Model response cache

#### Knowledge Base
- `knowledge_bases` - KB per vendor
- `kb_documents` - Documents in KB
- `kb_embeddings_refs` - Vector DB references

#### Caching
- `main_cache` - Persistent Q&A cache (vendor-wide)
- `temporary_cache` - Temporary Q&A cache (per chat)

#### Billing
- `billing_plans` - Plan definitions
- `quota_allocations` - Vendor quotas
- `usage_records` - Usage tracking
- `invoices` - Invoices
- `payments` - Payments

#### Vendor Config
- `vendor_configs` - Vendor-specific config
- `vendor_endpoints` - Webhook endpoints

#### API & Security
- `api_keys` - API keys
- `rate_limits` - Rate limiting
- `ip_allowlist` - IP filtering
- `webhook_deliveries` - Webhook logs

#### System
- `vendor_model_assignments` - Model assignments
- `audit_logs` - Audit trail
- `feature_flags` - Feature flags
- `support_tickets` - Support tickets
- `notifications` - Notifications
- `data_export_requests` - GDPR/compliance exports

### ⚠️ Legacy Tables (3) - Can be removed after migration
- `chats` - Old chat table (replaced by `chat_sessions`)
- `messages` - Old messages table (replaced by `chat_messages`)
- `conversation_memory` - Old memory table (replaced by `conversation_memories`)
- `token_usage` - Old token tracking (replaced by `usage_records`)

---

## Table Relationships

### User Hierarchy
```
admins (platform admins)
  └── vendors (multi-tenant)
      ├── users (vendor employees - RBAC)
      └── chat_users (end users who chat)
          ├── chat_sessions
          │   └── chat_messages
          ├── conversation_memories
          └── suggestion_cache
```

### Vendor Structure
```
vendors
  ├── vendor_configs
  ├── vendor_endpoints
  ├── vendor_model_assignments
  ├── knowledge_bases
  │   ├── kb_documents
  │   └── kb_embeddings_refs
  ├── chat_sessions
  │   └── chat_messages
  ├── usage_records
  ├── invoices
  │   └── payments
  └── quota_allocations
```

---

## Migration Status

### ✅ Completed Migrations
- ✅ `chat_users` table created
- ✅ `chat_sessions` migrated to use `chat_user_id`
- ✅ `conversation_memories` migrated to use `chat_user_id`
- ✅ `suggestion_cache` migrated to use `chat_user_id`

### ⚠️ Pending Cleanup
- ⚠️ Remove legacy tables: `chats`, `messages`, `conversation_memory`, `token_usage`
- ⚠️ Migrate any remaining data from legacy tables
- ⚠️ Update any code still referencing legacy tables

---

## Quick Reference

### Most Important Tables
1. **vendors** - Multi-tenant vendor accounts
2. **chat_users** - End users who chat
3. **chat_sessions** - Chat sessions
4. **chat_messages** - Messages
5. **conversation_memories** - Conversation memory
6. **models** - LLM models
7. **knowledge_bases** - RAG knowledge bases
8. **main_cache** - Persistent cache
9. **temporary_cache** - Temporary cache
10. **usage_records** - Usage tracking

### Tables by Function
- **User Management:** `users`, `chat_users`, `roles`, `user_roles`
- **Chat System:** `chat_sessions`, `chat_messages`, `conversation_memories`
- **LLM:** `models`, `model_configs`, `model_presets`
- **RAG:** `knowledge_bases`, `kb_documents`, `kb_embeddings_refs`
- **Caching:** `main_cache`, `temporary_cache`, `suggestion_cache`
- **Billing:** `billing_plans`, `quota_allocations`, `usage_records`, `invoices`, `payments`

---

## Notes

- All tables are vendor-aware (except `admins`, `models`, `billing_plans`, `roles`)
- `chat_users` is separate from `users` (vendor employees)
- Legacy tables can be removed after verifying all data is migrated
- All new tables use `chat_user_id` instead of `user_id` for chat-related data

