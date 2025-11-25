# Multi-Vendor System Guide

## Overview

The chatbot system now supports multiple vendors, each with their own:
- Configuration files
- Knowledge base (RAG)
- ChromaDB collections
- Database records (users, chats, messages)

## Current Vendors

- **neguinho_motors**: Neguinho Motors Ltd (Motorcycle Dealership) - Original vendor, all existing data migrated here
- **test_vendor**: Test Vendor Ltd (Retail) - Test vendor with dummy data

## Creating a New Vendor

### Via Admin Panel

1. Go to **Admin Panel** → **Vendors** tab
2. Click **"Create New Vendor"** button
3. Fill in:
   - **Vendor ID**: Unique identifier (lowercase, no spaces, e.g., `my_company`)
   - **Vendor Name**: Display name (e.g., `My Company Ltd`)
   - **Company Name**: Full company name
   - **Business Type**: Select from dropdown
   - **Copy from**: (Optional) Copy config and RAG from existing vendor
4. Click **"Create Vendor"**

### What Gets Created

When creating a new vendor (without copying), the system automatically creates:

1. **Config File**: `config/vendors/{vendor_id}/unified_config.json`
   - Includes dummy company info
   - Basic system prompts
   - Contact information template

2. **RAG Knowledge Base**: `rag_knowledge_base/{vendor_id}/knowledge_base.json`
   - 3 dummy chunks:
     - Company information
     - Services information
     - Contact information

3. **ChromaDB Collection**: `{vendor_id}_kb`
   - Empty collection ready for RAG data

4. **Database Record**: Vendor entry in `vendors` table

## Switching Vendors

### In Admin Panel

1. Use the **Vendor Selector** dropdown at the top (always visible)
2. Select a vendor from the list
3. All tabs (Unified Config, Knowledge Base, RAG, etc.) automatically update to show that vendor's data

### In Chat Frontend

1. Use the **Vendor** dropdown in the chat interface
2. Select a vendor
3. The chat interface updates:
   - Company name in title
   - Contact info in disclaimer
   - All messages use the selected vendor's config and RAG

## Vendor-Specific Features

### Configuration

Each vendor has their own `unified_config.json` with:
- Business information (company name, services, branches)
- Contact details
- System prompts
- Chatbot service settings
- All other application settings

### Knowledge Base

Each vendor has their own RAG knowledge base:
- Stored in `rag_knowledge_base/{vendor_id}/knowledge_base.json`
- Loaded into vendor-specific ChromaDB collection
- Completely isolated from other vendors

### Database

All database records are vendor-scoped:
- Users belong to a vendor
- Chats belong to a vendor
- Messages are linked to vendor-specific chats
- Token usage tracked per vendor

## API Usage

### Creating a Vendor

```bash
POST /api/v1/vendor/create
{
  "vendor_id": "my_company",
  "vendor_name": "My Company",
  "company_name": "My Company Ltd",
  "business_type": "retail",
  "copy_from_vendor": null  # or "neguinho_motors" to copy
}
```

### Sending Messages

```bash
POST /api/v1/chat/message
{
  "user_id": "user_001",
  "message": "Hello",
  "vendor_id": "neguinho_motors"  # Optional, uses default if not provided
}
```

### Getting Vendor Config

```bash
GET /api/v1/vendor/{vendor_id}/config
```

## File Structure

```
config/
  └── vendors/
      ├── neguinho_motors/
      │   └── unified_config.json
      └── test_vendor/
          └── unified_config.json

rag_knowledge_base/
  ├── neguinho_motors/
  │   └── knowledge_base.json
  └── test_vendor/
      └── knowledge_base.json

data/
  └── chroma_db/
      ├── neguinho_motors_kb/  (collection)
      └── test_vendor_kb/       (collection)
```

## Testing

1. **Create a new vendor** via admin panel
2. **Switch to the new vendor** in admin panel
3. **Edit the vendor's config** in Unified Config tab
4. **Add knowledge base data** in Knowledge Base tab
5. **Load RAG** to populate ChromaDB
6. **Switch to the vendor** in chat frontend
7. **Send a test message** to verify it uses the vendor's config and RAG

## Notes

- When creating a vendor without copying, it gets minimal dummy data to get started
- You can copy from an existing vendor to use it as a template
- Each vendor's data is completely isolated
- The default vendor is `neguinho_motors` (original data)
- Vendor switching is instant and updates all relevant UI elements

