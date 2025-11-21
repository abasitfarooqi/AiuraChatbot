# AiuraChatbot SaaS Platform Setup Guide

Complete multi-tenant SaaS architecture with admin control, vendor management, quotas, billing, and full platform features.

## Architecture Overview

This platform implements a comprehensive multi-tenant SaaS system with:

- **Multi-tenancy**: Full vendor isolation with tenant scoping
- **Admin Control Panel**: Super admin can manage all vendors, quotas, billing, models
- **Vendor Management**: Vendors can manage their own users, knowledge bases, API keys
- **Quota System**: Resource-based quotas (tokens, messages, storage) with soft/hard limits
- **Billing & Invoicing**: Complete billing system with plans, invoices, payments
- **Model Assignment**: Control which models each vendor can use
- **Usage Tracking**: Real-time usage metering and analytics
- **Audit Logging**: Complete audit trail of all actions
- **Security**: RBAC, API keys, IP allowlists, 2FA support

## Database Setup

### Option 1: MySQL (Recommended for Production)

1. **Install MySQL** (if not already installed):
   ```bash
   # macOS
   brew install mysql
   brew services start mysql
   
   # Ubuntu/Debian
   sudo apt-get install mysql-server
   sudo systemctl start mysql
   ```

2. **Run setup script**:
   ```bash
   ./scripts/setup_mysql.sh
   ```
   
   This will:
   - Create the database `aiura_chatbots`
   - Create a database user
   - Update `.env` file with MySQL configuration

3. **Initialize database schema**:
   ```bash
   python scripts/init_saas_db.py
   ```
   
   This creates:
   - All database tables
   - Default LLM models (Mistral, Llama2, Phi-2, GPT-4)
   - Default roles (vendor_admin, vendor_user, vendor_manager, support_agent)
   - Default billing plans (Free, Hobby, Pro, Enterprise)
   - Super admin account (admin@aiurachatbot.com / admin123)

### Option 2: SQLite (Development)

For development, you can use SQLite (default):

```bash
# Just run the initialization
python scripts/init_saas_db.py
```

## Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
USE_MYSQL=true  # Set to false for SQLite
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=aiura_chatbot
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=aiura_chatbots

# Application
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM (Ollama - default)
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=mistral
```

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database**:
   ```bash
   python scripts/init_saas_db.py
   ```

3. **Start the server**:
   ```bash
   python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Database Schema

### Core Tables

- **admins**: Platform super admin accounts
- **vendors**: Vendor/tenant accounts
- **users**: Users (vendor users or platform users)
- **roles**: RBAC roles
- **user_roles**: User-role assignments
- **models**: LLM model registry
- **vendor_model_assignments**: Model assignments per vendor

### Quota & Billing

- **quota_allocations**: Vendor-level quota allocations
- **usage_records**: Atomic usage events for metering
- **billing_plans**: Billing plan definitions
- **invoices**: Invoices for vendors
- **payments**: Payment records

### Chat & Knowledge

- **chat_sessions**: Chat sessions
- **chat_messages**: Chat messages
- **knowledge_bases**: Knowledge bases per vendor
- **kb_documents**: Documents in knowledge bases
- **kb_embeddings_refs**: References to embeddings in vector DB

### Security & Management

- **vendor_configs**: Flexible per-vendor configuration
- **vendor_endpoints**: Vendor webhook endpoints
- **api_keys**: API keys for vendor API access
- **rate_limits**: Rate limits per vendor or API key
- **audit_logs**: Immutable audit trail
- **feature_flags**: Feature flags for gating features

### Additional Features

- **support_tickets**: Support tickets / helpdesk
- **ip_allowlist**: IP allowlist/blocklist
- **notifications**: Notifications (in-app and email logs)
- **data_export_requests**: Data export requests for compliance

## API Endpoints

### Super Admin Endpoints

All admin endpoints are prefixed with `/api/v1/admin`:

- `GET /admin/vendors` - List all vendors
- `GET /admin/vendors/{vendor_id}` - Get vendor details
- `POST /admin/vendors` - Create new vendor
- `PATCH /admin/vendors/{vendor_id}` - Update vendor
- `DELETE /admin/vendors/{vendor_id}` - Delete vendor
- `POST /admin/vendors/{vendor_id}/quotas` - Create quota allocation
- `POST /admin/vendors/{vendor_id}/credits/adjust` - Adjust vendor credits
- `POST /admin/vendors/{vendor_id}/models/assign` - Assign model to vendor
- `GET /admin/vendors/{vendor_id}/usage` - Get vendor usage analytics
- `GET /admin/audit-logs` - Get audit logs

### Vendor Endpoints

Vendor endpoints are scoped by vendor slug or vendor_id:

- `POST /api/v1/chat/sessions` - Create chat session
- `POST /api/v1/chat/sessions/{session_uuid}/messages` - Send message
- `GET /api/v1/vendor/{vendor_slug}/knowledge-bases` - List knowledge bases
- `POST /api/v1/vendor/{vendor_slug}/api-keys` - Create API key

## Super Admin Control Panel Features

### Vendor Overview

- **Summary**: Plan, status, billing balance, quota usage
- **Active Sessions**: Live stream of open sessions
- **Recent Messages**: Peek into recent messages
- **Users Tab**: Manage vendor users, roles, permissions
- **Models Tab**: Assign models, set limits, mark defaults
- **Quotas & Credits**: Set quotas, add credits, view usage
- **Billing & Invoices**: View invoices, mark as paid, apply credits
- **Account Controls**: Suspend/reactivate, set status
- **KB & Data**: View knowledge bases, re-index, export
- **Endpoints & API Keys**: Manage endpoints and API keys
- **Logs & Audit**: View audit logs and webhook deliveries
- **Usage Analytics**: Charts for tokens, sessions, top queries
- **Security Controls**: IP allowlists, 2FA enforcement

## Vendor Control Panel Features

### Vendor Dashboard

- Usage summary, remaining quotas, upcoming invoice
- Active sessions, recent flagged messages

### Management

- **Users**: Invite/disable users, assign roles
- **Chat Settings**: Default model, safety filters, prompts
- **Knowledge Bases**: Create KBs, upload docs, manage metadata
- **API Keys & Endpoints**: Create/revoke keys, webhooks
- **Billing & Plan**: View invoices, upgrade/downgrade
- **Logs**: Webhook delivery logs, audit trail
- **Moderation**: View flagged messages, configure thresholds
- **Export Data**: Export sessions/messages (CSV/JSON)
- **Settings**: Branding, custom domain, web widget config

## Quota System

### Resource Types

- `tokens`: LLM token usage
- `messages`: Message count
- `embeddings_storage_mb`: Embedding storage
- `storage_mb`: General storage
- `concurrent_sessions`: Concurrent chat sessions

### Quota Enforcement

- **Soft Limit**: Allow overage with billing alerts
- **Hard Limit**: Block requests when exceeded
- **Overdraft**: Temporary overdraft allowed

### Usage Tracking

Every API call creates a `usage_record` with:
- Vendor ID
- User ID (optional)
- Model ID
- Resource type
- Amount
- Cost
- Timestamp

## Billing System

### Billing Plans

- **Free**: 10k tokens/month, 100 conversations, 100MB storage
- **Hobby**: $29/month, 100k tokens, 1k conversations, 1GB storage
- **Pro**: $99/month, 1M tokens, 10k conversations, 10GB storage
- **Enterprise**: $499/month, 10M tokens, 100k conversations, 100GB storage

### Invoice Generation

- Automatic invoice generation at period end
- Manual invoice creation by admin
- Payment tracking and reconciliation
- Credit adjustments and top-ups

## Model Assignment

### Assignment Layers

1. **Global Models**: Available models in the platform
2. **Vendor Assignment**: Which models vendor can use
3. **User Override**: Optional per-user model permissions
4. **Session Selection**: Model used in each session

### Cache Models

Designate lightweight models (e.g., Phi-2) as cache models for fast, cheap responses when cache is available.

## Security Features

- **Password Hashing**: Argon2/bcrypt
- **API Key Hashing**: Hashed storage, show raw only once
- **RBAC**: Role-based access control
- **IP Allowlists**: Per-vendor IP restrictions
- **2FA Support**: Two-factor authentication ready
- **Audit Logging**: Complete audit trail
- **Rate Limiting**: Per-vendor and per-key rate limits

## Development Workflow

1. **Start MySQL** (if using):
   ```bash
   brew services start mysql  # macOS
   # or
   sudo systemctl start mysql  # Linux
   ```

2. **Run migrations**:
   ```bash
   python scripts/init_saas_db.py
   ```

3. **Start server**:
   ```bash
   python -m uvicorn backend.app.main:app --reload
   ```

4. **Access admin panel**:
   - Navigate to `http://localhost:8000/docs`
   - Use super admin credentials (change immediately!)

## Production Deployment

1. **Set strong passwords**:
   - MySQL root password
   - Database user password
   - Secret key for JWT

2. **Configure environment**:
   - Set `USE_MYSQL=true`
   - Configure all MySQL credentials
   - Set production `SECRET_KEY`

3. **Run migrations**:
   ```bash
   python scripts/init_saas_db.py
   ```

4. **Start with production server**:
   ```bash
   gunicorn backend.app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

5. **Set up reverse proxy** (Nginx/Traefik)

6. **Enable SSL/TLS**

7. **Set up backups** for MySQL database

## Next Steps

- [ ] Implement JWT authentication for admin endpoints
- [ ] Build super admin UI (React/Vue)
- [ ] Build vendor control panel UI
- [ ] Integrate Stripe for payments
- [ ] Set up email notifications
- [ ] Implement webhook delivery system
- [ ] Add data export functionality
- [ ] Set up monitoring and alerts

## Support

For issues or questions, check the logs:
- Application logs: `./logs/chatbot.log`
- Server logs: `./logs/server.log`

## License

[Your License Here]

