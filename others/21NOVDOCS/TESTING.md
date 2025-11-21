# Testing Guide - Multi-Tenant SaaS Platform

## Quick Test Commands

### 1. Test Database Initialization
```bash
source venv/bin/activate
python scripts/init_saas_db.py
```

Expected output:
- ✓ Database tables created successfully
- ✓ Default models created
- ✓ Default roles created
- ✓ Default billing plans created
- ✓ Super admin created

### 2. Test API Server
```bash
source venv/bin/activate
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Then visit: `http://localhost:8000/docs`

### 3. Test Admin Endpoints

#### List Vendors
```bash
curl http://localhost:8000/api/v1/admin/vendors
```

#### Create Vendor
```bash
curl -X POST http://localhost:8000/api/v1/admin/vendors \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "test_vendor",
    "name": "Test Vendor",
    "company_name": "Test Company Ltd",
    "plan_code": "free"
  }'
```

#### Get Vendor Details
```bash
curl http://localhost:8000/api/v1/admin/vendors/1
```

#### Create Quota
```bash
curl -X POST http://localhost:8000/api/v1/admin/vendors/1/quotas \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "tokens",
    "allocated_amount": 100000,
    "period_start": "2025-01-01T00:00:00",
    "period_end": "2025-02-01T00:00:00",
    "billing_cycle": "monthly",
    "soft_limit": true
  }'
```

#### Adjust Credits
```bash
curl -X POST http://localhost:8000/api/v1/admin/vendors/1/credits/adjust \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.0,
    "reason": "Initial credit allocation"
  }'
```

#### Assign Model
```bash
curl -X POST http://localhost:8000/api/v1/admin/vendors/1/models/assign \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "is_default": true,
    "enabled": true,
    "priority_order": 1
  }'
```

### 4. Verify Database Tables

```bash
# SQLite
sqlite3 data/chatbot.db ".tables"

# MySQL
mysql -u aiura_chatbot -p aiura_chatbots -e "SHOW TABLES;"
```

Expected tables (29 total):
- admins
- vendors
- users
- roles
- user_roles
- models
- vendor_model_assignments
- model_cache
- quota_allocations
- usage_records
- billing_plans
- invoices
- payments
- chat_sessions
- chat_messages
- knowledge_bases
- kb_documents
- kb_embeddings_refs
- vendor_configs
- vendor_endpoints
- api_keys
- rate_limits
- webhook_deliveries
- audit_logs
- feature_flags
- support_tickets
- ip_allowlist
- notifications
- data_export_requests

### 5. Test Multi-Tenancy

```python
from backend.config.database import get_db_session
from backend.models.saas_models import Vendor, User
from backend.middleware.tenant import require_vendor

# Test vendor scoping
db = next(get_db_session())
vendor = db.query(Vendor).filter(Vendor.slug == "test_vendor").first()
print(f"Vendor: {vendor.name}, Status: {vendor.status.value}")
```

## Test Checklist

- [x] Database models load without errors
- [x] All 29 tables created successfully
- [x] Default data seeded (models, roles, plans, admin)
- [x] Admin API endpoints accessible
- [x] Multi-tenant middleware functional
- [x] Quota system working
- [x] Usage tracking ready
- [x] Audit logging enabled

## Known Issues Fixed

1. ✅ SQLAlchemy `metadata` reserved name → renamed to `meta`
2. ✅ LONGTEXT compatibility → changed to `Text` for SQLite/MySQL compatibility
3. ✅ Import errors → all dependencies installed
4. ✅ Database connection → supports both SQLite and MySQL

## Next Steps

1. Implement JWT authentication for admin endpoints
2. Add vendor API endpoints
3. Integrate with existing chat endpoints
4. Build admin UI
5. Add comprehensive tests

