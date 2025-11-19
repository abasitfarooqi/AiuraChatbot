"""
Vendor Management API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from loguru import logger
from backend.models.database import Vendor
from backend.api.database import get_db
from sqlalchemy.orm import Session
from backend.utils.vendor_manager import get_vendor_manager
from backend.services.aiura_mind import AiuraMindService

router = APIRouter(prefix="/vendor", tags=["vendor"])


class VendorCreateRequest(BaseModel):
    vendor_id: str
    vendor_name: str
    company_name: str
    business_type: str = "motorcycle_dealership"
    copy_from_vendor: Optional[str] = None


class VendorUpdateRequest(BaseModel):
    vendor_name: Optional[str] = None
    company_name: Optional[str] = None
    business_type: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/list")
async def list_vendors():
    """List all vendors."""
    try:
        vendor_manager = get_vendor_manager()
        vendors = vendor_manager.list_vendors()
        return {"vendors": vendors, "count": len(vendors)}
    except Exception as e:
        logger.error(f"Error listing vendors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str):
    """Get vendor information."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        return vendor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vendor {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_vendor(request: VendorCreateRequest):
    """Create a new vendor."""
    try:
        vendor_manager = get_vendor_manager()
        
        # Check if vendor already exists
        existing = vendor_manager.get_vendor(request.vendor_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Vendor {request.vendor_id} already exists")
        
        vendor_info = vendor_manager.create_vendor(
            vendor_id=request.vendor_id,
            vendor_name=request.vendor_name,
            company_name=request.company_name,
            business_type=request.business_type,
            copy_from_vendor=request.copy_from_vendor
        )
        
        return {
            "status": "success",
            "message": f"Vendor {request.vendor_id} created successfully",
            "vendor": vendor_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating vendor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{vendor_id}")
async def update_vendor(vendor_id: str, request: VendorUpdateRequest):
    """Update vendor information."""
    try:
        vendor_manager = get_vendor_manager()
        
        # Check if vendor exists
        existing = vendor_manager.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        # Build update dict
        update_data = {}
        if request.vendor_name is not None:
            update_data["vendor_name"] = request.vendor_name
        if request.company_name is not None:
            update_data["company_name"] = request.company_name
        if request.business_type is not None:
            update_data["business_type"] = request.business_type
        if request.is_active is not None:
            update_data["is_active"] = request.is_active
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        success = vendor_manager.update_vendor(vendor_id, **update_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update vendor")
        
        updated_vendor = vendor_manager.get_vendor(vendor_id)
        return {
            "status": "success",
            "message": f"Vendor {vendor_id} updated successfully",
            "vendor": updated_vendor
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating vendor {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vendor_id}")
async def delete_vendor(vendor_id: str):
    """Delete (deactivate) a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        
        # Check if vendor exists
        existing = vendor_manager.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        success = vendor_manager.delete_vendor(vendor_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete vendor")
        
        return {
            "status": "success",
            "message": f"Vendor {vendor_id} deactivated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting vendor {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}/config")
async def get_vendor_config(vendor_id: str, version: Optional[str] = None):
    """Get vendor-specific unified config (optionally for a specific version)."""
    try:
        vendor_manager = get_vendor_manager()
        config_manager = vendor_manager.get_vendor_config_manager(vendor_id, version=version)
        config = config_manager.load_config()
        return config
    except Exception as e:
        logger.error(f"Error getting vendor config for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/config")
async def save_vendor_config(vendor_id: str, config: dict):
    """Save vendor-specific unified config."""
    try:
        vendor_manager = get_vendor_manager()
        
        # Check if vendor exists
        existing = vendor_manager.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        config_manager = vendor_manager.get_vendor_config_manager(vendor_id)
        success = config_manager.save_config(config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save config")
        
        return {
            "status": "success",
            "message": f"Config saved for vendor {vendor_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving vendor config for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}/knowledge-base")
async def get_vendor_knowledge_base(vendor_id: str, version: Optional[str] = None):
    """Get vendor-specific knowledge base (optionally for a specific version)."""
    try:
        vendor_manager = get_vendor_manager()
        
        # Check if vendor exists
        existing = vendor_manager.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        rag_path = vendor_manager.get_vendor_rag_path(vendor_id, version=version)
        
        if not rag_path.exists():
            # Return empty structure if file doesn't exist (allows creating new KB)
            company_name = existing.get('company_name', vendor_id) if isinstance(existing, dict) else getattr(existing, 'company_name', vendor_id)
            return {
                "metadata": {
                    "version": "2.0.0",
                    "vendor_id": vendor_id,
                    "description": f"Knowledge base for {company_name}",
                    "chunking_strategy": "semantic_chunks_with_metadata",
                    "last_updated": datetime.now().strftime("%Y-%m-%d")
                },
                "chunks": []
            }
        
        with open(rag_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)
        
        return kb_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vendor knowledge base for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}/versions/config")
async def list_config_versions(vendor_id: str):
    """List all config versions for a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        versions = vendor_manager.list_config_versions(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "versions": versions,
            "current": "current" if "current" in versions else versions[0] if versions else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing config versions for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}/versions/knowledge-base")
async def list_kb_versions(vendor_id: str):
    """List all knowledge base versions for a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        versions = vendor_manager.list_kb_versions(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "versions": versions,
            "current": "current" if "current" in versions else versions[0] if versions else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing KB versions for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VersionCreateRequest(BaseModel):
    version: str
    copy_from: Optional[str] = None


@router.post("/{vendor_id}/versions/config/create")
async def create_config_version(vendor_id: str, request: VersionCreateRequest):
    """Create a new config version for a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        success = vendor_manager.create_config_version(vendor_id, request.version, request.copy_from)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create config version")
        
        return {
            "status": "success",
            "message": f"Config version {request.version} created for vendor {vendor_id}",
            "vendor_id": vendor_id,
            "version": request.version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating config version for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/versions/knowledge-base/create")
async def create_kb_version(vendor_id: str, request: VersionCreateRequest):
    """Create a new knowledge base version for a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        success = vendor_manager.create_kb_version(vendor_id, request.version, request.copy_from)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create KB version")
        
        return {
            "status": "success",
            "message": f"Knowledge base version {request.version} created for vendor {vendor_id}",
            "vendor_id": vendor_id,
            "version": request.version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating KB version for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class VersionSwitchRequest(BaseModel):
    version: str


@router.post("/{vendor_id}/versions/config/switch")
async def switch_config_version(vendor_id: str, request: VersionSwitchRequest):
    """Switch vendor's active config to a specific version."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        success = vendor_manager.switch_config_version(vendor_id, request.version)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to switch to config version {request.version}")
        
        return {
            "status": "success",
            "message": f"Switched to config version {request.version} for vendor {vendor_id}",
            "vendor_id": vendor_id,
            "version": request.version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching config version for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/versions/knowledge-base/switch")
async def switch_kb_version(vendor_id: str, request: VersionSwitchRequest):
    """Switch vendor's active knowledge base to a specific version."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        success = vendor_manager.switch_kb_version(vendor_id, request.version)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to switch to KB version {request.version}")
        
        # Reload RAG after switching
        try:
            from backend.services.rag_service import RAGService
            rag_service = RAGService(vendor_id=vendor_id)
            rag_path = vendor_manager.get_vendor_rag_path(vendor_id)
            rag_service.load_knowledge_base(str(rag_path))
        except Exception as e:
            logger.warning(f"Error reloading RAG after version switch: {e}")
        
        return {
            "status": "success",
            "message": f"Switched to knowledge base version {request.version} for vendor {vendor_id}",
            "vendor_id": vendor_id,
            "version": request.version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching KB version for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BusinessDataRequest(BaseModel):
    business_data: str
    vendor_name: str
    company_name: str
    business_type: Optional[str] = "general"
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    generation_depth: Optional[str] = "extensive"
    max_tokens: Optional[int] = 32000
    temperature: Optional[float] = 0.2


@router.post("/{vendor_id}/aiura-mind/generate")
async def generate_from_business_data(
    vendor_id: str,
    request: BusinessDataRequest,
    db: Session = Depends(get_db)
):
    """Generate knowledge base and config from business data using AiuraMind."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        # Initialize AiuraMind service with optional custom model and settings
        aiura_mind = AiuraMindService(
            db=db, 
            vendor_id=vendor_id,
            model_provider=request.model_provider,
            model_name=request.model_name,
            generation_depth=request.generation_depth,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Generate config and KB
        result = await aiura_mind.generate_from_business_data(
            business_data=request.business_data,
            vendor_id=vendor_id,
            vendor_name=request.vendor_name,
            company_name=request.company_name,
            business_type=request.business_type
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating from business data for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/config/upload")
async def upload_config_file(
    vendor_id: str,
    file: UploadFile = File(...)
):
    """Upload and save unified config file for a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        # Read file content
        content = await file.read()
        config_data = json.loads(content.decode('utf-8'))
        
        # Validate JSON
        if not isinstance(config_data, dict):
            raise HTTPException(status_code=400, detail="Invalid config format")
        
        # Save config
        config_manager = vendor_manager.get_vendor_config_manager(vendor_id)
        success = config_manager.save_config(config_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save config")
        
        return {
            "status": "success",
            "message": f"Config uploaded and saved for vendor {vendor_id}"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading config for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/config/save-generated")
async def save_generated_config(
    vendor_id: str,
    config_data: Dict[str, Any]
):
    """Save generated config directly to vendor folder."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        # Save config
        config_manager = vendor_manager.get_vendor_config_manager(vendor_id)
        success = config_manager.save_config(config_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save config")
        
        # Also generate additional config files
        from backend.services.aiura_mind import AiuraMindService
        from backend.models.database import get_session_local
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            aiura_mind = AiuraMindService(db=db, vendor_id=vendor_id)
            company_name = config_data.get("business", {}).get("company_name", vendor.company_name)
            aiura_mind._generate_additional_config_files(config_data, vendor_id, company_name)
        finally:
            db.close()
        
        return {
            "status": "success",
            "message": f"Generated config saved to vendor {vendor_id} folder"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving generated config for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/knowledge-base/save-generated")
async def save_generated_knowledge_base(
    vendor_id: str,
    kb_data: Dict[str, Any]
):
    """Save generated knowledge base directly to vendor folder."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        # Save KB
        kb_path = vendor_manager.get_vendor_rag_path(vendor_id)
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(kb_path, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": f"Generated knowledge base saved to vendor {vendor_id} folder"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving generated KB for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/knowledge-base/upload")
async def upload_kb_file(
    vendor_id: str,
    file: UploadFile = File(...)
):
    """Upload and save knowledge base file for a vendor."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        # Read file content
        content = await file.read()
        kb_data = json.loads(content.decode('utf-8'))
        
        # Validate JSON
        if not isinstance(kb_data, dict) or "chunks" not in kb_data:
            raise HTTPException(status_code=400, detail="Invalid knowledge base format")
        
        # Ensure vendor_id in metadata
        if "metadata" not in kb_data:
            kb_data["metadata"] = {}
        kb_data["metadata"]["vendor_id"] = vendor_id
        
        # Ensure vendor_id in all chunks
        for chunk in kb_data.get("chunks", []):
            if "metadata" not in chunk:
                chunk["metadata"] = {}
            chunk["metadata"]["vendor_id"] = vendor_id
        
        # Save KB file
        rag_path = vendor_manager.get_vendor_rag_path(vendor_id)
        rag_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(rag_path, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=2, ensure_ascii=False)
        
        # Reload into RAG service
        try:
            from backend.services.rag_service import RAGService
            rag_service = RAGService(vendor_id=vendor_id)
            rag_service.load_knowledge_base(str(rag_path))
            reload_status = "success"
            reload_message = "Knowledge base uploaded and reloaded into ChromaDB"
        except Exception as e:
            logger.warning(f"Error reloading RAG for vendor {vendor_id}: {e}")
            reload_status = "warning"
            reload_message = f"Knowledge base uploaded but error reloading: {str(e)}"
        
        return {
            "status": "success",
            "message": f"Knowledge base uploaded for vendor {vendor_id}",
            "reload_status": reload_status,
            "reload_message": reload_message
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading knowledge base for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}/api-endpoints")
async def get_vendor_api_endpoints(vendor_id: str):
    """Get vendor-specific API endpoints for frontend integration."""
    try:
        vendor_manager = get_vendor_manager()
        vendor = vendor_manager.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        from backend.config import get_settings
        settings = get_settings()
        base_url = f"http://{settings.api_host}:{settings.api_port}{settings.api_prefix}"
        
        endpoints = {
            "vendor_id": vendor_id,
            "base_url": base_url,
            "endpoints": {
                "send_message": f"{base_url}/chat/message",
                "get_chats": f"{base_url}/chat/chats/{{user_id}}?vendor_id={vendor_id}",
                "get_chat_history": f"{base_url}/chat/history/{{chat_id}}?vendor_id={vendor_id}",
                "delete_chat": f"{base_url}/chat/delete/{{chat_id}}",
                "get_suggestions": f"{base_url}/chat/suggestions?vendor_id={vendor_id}"
            },
            "integration_example": {
                "send_message": {
                    "method": "POST",
                    "url": f"{base_url}/chat/message",
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "user_id": "user_123",
                        "chat_id": "chat_123",
                        "message": "Hello",
                        "vendor_id": vendor_id
                    }
                },
                "get_chats": {
                    "method": "GET",
                    "url": f"{base_url}/chat/chats/user_123?vendor_id={vendor_id}"
                }
            }
        }
        
        return endpoints
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API endpoints for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vendor_id}/knowledge-base")
async def save_vendor_knowledge_base(vendor_id: str, kb_data: dict):
    """Save vendor-specific knowledge base."""
    try:
        vendor_manager = get_vendor_manager()
        
        # Check if vendor exists
        existing = vendor_manager.get_vendor(vendor_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")
        
        rag_path = vendor_manager.get_vendor_rag_path(vendor_id)
        
        # Ensure vendor_id is set in metadata
        if "metadata" in kb_data:
            kb_data["metadata"]["vendor_id"] = vendor_id
        
        # Ensure vendor_id is set in all chunks
        if "chunks" in kb_data:
            for chunk in kb_data["chunks"]:
                if "metadata" in chunk:
                    chunk["metadata"]["vendor_id"] = vendor_id
        
        # Save to file
        with open(rag_path, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=2, ensure_ascii=False)
        
        # Reload into RAG service (vendor-specific)
        try:
            from backend.services.rag_service import RAGService
            rag_service = RAGService(vendor_id=vendor_id)
            rag_service.load_knowledge_base(str(rag_path))
            reload_status = "success"
            reload_message = "Knowledge base saved and reloaded into ChromaDB"
        except Exception as e:
            logger.warning(f"Error reloading RAG for vendor {vendor_id}: {e}")
            reload_status = "warning"
            reload_message = f"Knowledge base saved but error reloading: {str(e)}"
        
        return {
            "status": "success",
            "message": f"Knowledge base saved for vendor {vendor_id}",
            "reload_status": reload_status,
            "reload_message": reload_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving vendor knowledge base for {vendor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

