# Neguinho Motors - First Vendor Setup Complete ✅

## Vendor Information

- **Vendor ID**: 1
- **Slug**: `neguinho_motors`
- **Name**: Neguinho Motors
- **Company**: Neguinho Motors Ltd
- **Status**: Active
- **Plan**: Pro
- **Credits**: £1,000.00

## Company Details

- **Company Number**: 11600635
- **Registered Address**: 9-13 Catford Hill, London, SE6 4NU
- **Primary Phone**: 0208 314 1498
- **Primary Email**: enquiries@neguinhomotors.co.uk
- **Trading Names**: NGN Motors, Neguinho Motors, NGN
- **Incorporated**: October 2018

## Configuration Files

- **Config Path**: `config/vendors/neguinho_motors/unified_config.json`
- **Knowledge Base Path**: `rag_knowledge_base/neguinho_motors/knowledge_base.json`
- **ChromaDB Collection**: `neguinho_motors_kb`

## Database Setup

### ✅ Model Assignments (2)
1. **Default Model**: Mistral 7B (Ollama)
   - Priority: 1
   - Enabled: Yes
   - Default: Yes

2. **Cache Model**: Phi-2 (Lightweight) (Ollama)
   - Priority: 2
   - Enabled: Yes
   - Default: No
   - Purpose: Lightweight responses for cache hits

### ✅ Quota Allocations (5)
1. **Tokens**: 1,000,000/month (soft limit)
2. **Messages**: 10,000/month (soft limit)
3. **Embeddings Storage**: 500 MB (soft limit)
4. **General Storage**: 1,000 MB / 1 GB (soft limit)
5. **Concurrent Sessions**: 50 (hard limit)

### ✅ Knowledge Base
- **Name**: Neguinho Motors Knowledge Base
- **Description**: Complete knowledge base including company info, services, branches, and policies
- **Vector DB Collection**: `neguinho_motors_kb`
- **Status**: Active

### ✅ Vendor Configurations (3)
1. **chatbot_settings**
   - Greetings, fallback messages
   - Cache and LLM enable/disable settings

2. **cache_settings**
   - Cache TTL: 24 hours
   - Lightweight model for cache: Enabled
   - Cache model: Phi-2 (Ollama)

3. **business_info**
   - Company details
   - Contact information
   - Registered address

### ✅ Vendor Admin User
- **Email**: admin@neguinhomotors.co.uk
- **Password**: neguinho2025 ⚠️ **CHANGE IMMEDIATELY**
- **Role**: vendor_admin
- **Status**: Active
- **Permissions**: Full vendor access

## Services & Branches

### Core Services
- Motorcycle rentals (short & long term)
- New and used motorcycle sales
- Servicing and repairs
- MOT testing
- Nationwide vehicle delivery
- Accident management support
- Online/offline accessories shop

### Branches
1. **Catford** (Main)
   - Address: 9-13 Unit 1179 Catford Hill, London SE6 4NU
   - Phone: 0208 314 1498
   - Hours: Mon-Sat 09:00-18:00

2. **Tooting**
   - Address: 4A Penwortham Road, London SW16 6RE
   - Phone: 0203 409 5478
   - Hours: Mon-Sat 09:00-18:00

3. **Sutton**
   - Address: 329 High St, Sutton SM1 1LW
   - Phone: 0208 412 9275
   - Hours: Mon-Sat 09:00-18:00

## Business Type
- **Category**: Motorcycle Dealership
- **Primary Brands**: Honda & Yamaha
- **Focus**: Scooters and motorcycles (125cc)

## Next Steps

1. ✅ **Change Admin Password**: Update the default password for `admin@neguinhomotors.co.uk`
2. ✅ **Load Knowledge Base**: Ensure the RAG knowledge base is loaded into ChromaDB
3. ✅ **Test Chat Endpoints**: Verify chat functionality with vendor context
4. ✅ **Monitor Usage**: Track token and message usage against quotas
5. ✅ **Configure Webhooks**: Set up webhook endpoints if needed

## API Access

The vendor can now be accessed via:
- **Vendor Slug**: `neguinho_motors`
- **Vendor ID**: `1`
- **Admin API**: `/api/v1/admin/vendors/1`
- **Chat API**: `/api/v1/chat` (with vendor context)

## Summary

✅ **Vendor Created**: Neguinho Motors (ID: 1)
✅ **Models Assigned**: 2 (Mistral 7B + Phi-2)
✅ **Quotas Set**: 5 resource types
✅ **Knowledge Base**: Linked and ready
✅ **Configurations**: 3 config entries
✅ **Admin User**: Created with vendor_admin role

**Status**: 🎉 **FULLY OPERATIONAL**

