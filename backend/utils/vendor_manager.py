"""
Vendor Management Utilities.
Handles vendor-specific configurations, RAG knowledge bases, and ChromaDB collections.
"""
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from backend.models.database import Vendor, get_session_local
from backend.utils.unified_config_manager import UnifiedConfigManager


class VendorManager:
    """Manages vendors and their configurations."""
    
    def __init__(self):
        """Initialize vendor manager."""
        self.vendors_dir = Path("./config/vendors")
        self.rag_dir = Path("./rag_knowledge_base")
        self.vendors_dir.mkdir(parents=True, exist_ok=True)
        self.rag_dir.mkdir(parents=True, exist_ok=True)
    
    def create_vendor(
        self,
        vendor_id: str,
        vendor_name: str,
        company_name: str,
        business_type: str = "motorcycle_dealership",
        copy_from_vendor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new vendor with its own config and RAG knowledge base.
        
        Args:
            vendor_id: Unique vendor identifier (e.g., "neguinho_motors")
            vendor_name: Display name for the vendor
            company_name: Company name
            business_type: Type of business
            copy_from_vendor: Optional vendor ID to copy config from (for templates)
        
        Returns:
            Dict with vendor info and paths
        """
        try:
            # Create vendor directories
            vendor_config_dir = self.vendors_dir / vendor_id
            vendor_config_dir.mkdir(parents=True, exist_ok=True)
            
            vendor_rag_dir = self.rag_dir / vendor_id
            vendor_rag_dir.mkdir(parents=True, exist_ok=True)
            
            # Create vendor-specific config
            config_path = vendor_config_dir / "unified_config.json"
            rag_path = vendor_rag_dir / "knowledge_base.json"
            
            # If copying from another vendor, use that as template
            if copy_from_vendor:
                source_config = self.vendors_dir / copy_from_vendor / "unified_config.json"
                source_rag = self.rag_dir / copy_from_vendor / "knowledge_base.json"
                
                if source_config.exists():
                    shutil.copy(source_config, config_path)
                    # Update vendor_id in copied config
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    config["metadata"]["vendor_id"] = vendor_id
                    config["business"]["company_name"] = company_name
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                
                if source_rag.exists():
                    shutil.copy(source_rag, rag_path)
                    # Update vendor_id in copied RAG
                    with open(rag_path, "r", encoding="utf-8") as f:
                        rag_data = json.load(f)
                    # Update vendor_id in all chunks
                    for chunk in rag_data.get("chunks", []):
                        if "metadata" in chunk:
                            chunk["metadata"]["vendor_id"] = vendor_id
                    with open(rag_path, "w", encoding="utf-8") as f:
                        json.dump(rag_data, f, indent=2, ensure_ascii=False)
            else:
                # Create default config with comprehensive dummy data
                config_manager = UnifiedConfigManager(str(config_path))
                default_config = config_manager._get_default_config()
                
                # Update metadata
                default_config["metadata"]["vendor_id"] = vendor_id
                default_config["metadata"]["business_type"] = business_type
                default_config["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
                
                # Update business info
                default_config["business"]["company_name"] = company_name
                default_config["business"]["services_list"] = ["service 1", "service 2", "service 3"]
                default_config["business"]["core_activities"] = [f"{company_name} provides quality services"]
                
                # Update contact info
                default_config["contact"]["primary_phone"] = "0000 000 0000"
                default_config["contact"]["primary_email"] = f"info@{vendor_id.replace('_', '')}.com"
                default_config["contact"]["contact_format"] = "Contact: {phone} or {email}"
                
                # Update prompts
                default_config["prompts"]["main_system_prompt"] = f"""You are the {company_name} chatbot assistant. You help customers with their inquiries.
        
CRITICAL RULES:
1. ONLY use information provided in the INFORMATION section
2. NEVER make up or guess information
3. Be helpful, friendly, and professional
4. If you don't know something, direct customers to contact us

RESPONSE FORMAT:
- Use clear, concise language
- Format responses with proper structure
- Always be polite and professional"""
                default_config["prompts"]["fallback_message"] = f"I don't have that information. Please contact us for more details."
                default_config["prompts"]["out_of_domain_message"] = f"I can help you with {company_name} services. How can I assist you?"
                
                config_manager.save_config(default_config)
                
                # Create vendor-specific config files
                self._create_vendor_config_files(vendor_id, default_config, company_name)
                
                # Create default RAG with dummy chunks
                default_rag = {
                    "metadata": {
                        "version": "2.0.0",
                        "vendor_id": vendor_id,
                        "description": f"Knowledge base for {company_name}",
                        "chunking_strategy": "semantic_chunks_with_metadata",
                        "last_updated": datetime.now().strftime("%Y-%m-%d")
                    },
                    "chunks": [
                        {
                            "symbol": "COMPANY_001",
                            "keyword": "company_info",
                            "tags": ["company", "business", "about", "information"],
                            "mapping": {
                                "category": "company",
                                "subcategory": "general",
                                "priority": "high",
                                "domain": vendor_id
                            },
                            "metadata": {
                                "source": "company",
                                "last_verified": datetime.now().strftime("%Y-%m-%d"),
                                "confidence": "high",
                                "requires_update": False,
                                "vendor_id": vendor_id
                            },
                            "content": f"{company_name} is a {business_type.replace('_', ' ')}. We provide quality services to our customers. Contact us for more information."
                        },
                        {
                            "symbol": "SERVICE_001",
                            "keyword": "services",
                            "tags": ["services", "what we do", "offerings"],
                            "mapping": {
                                "category": "services",
                                "subcategory": "general",
                                "priority": "high",
                                "domain": vendor_id
                            },
                            "metadata": {
                                "source": "company",
                                "last_verified": datetime.now().strftime("%Y-%m-%d"),
                                "confidence": "high",
                                "requires_update": False,
                                "vendor_id": vendor_id
                            },
                            "content": f"{company_name} offers various services. Please contact us to learn more about our service offerings and how we can help you."
                        },
                        {
                            "symbol": "CONTACT_001",
                            "keyword": "contact",
                            "tags": ["contact", "phone", "email", "reach us"],
                            "mapping": {
                                "category": "contact",
                                "subcategory": "general",
                                "priority": "high",
                                "domain": vendor_id
                            },
                            "metadata": {
                                "source": "company",
                                "last_verified": datetime.now().strftime("%Y-%m-%d"),
                                "confidence": "high",
                                "requires_update": False,
                                "vendor_id": vendor_id
                            },
                            "content": f"Contact {company_name}: Phone: 0000 000 0000, Email: info@{vendor_id.replace('_', '')}.com. We're here to help!"
                        }
                    ]
                }
                with open(rag_path, "w", encoding="utf-8") as f:
                    json.dump(default_rag, f, indent=2, ensure_ascii=False)
            
            # Generate ChromaDB collection name
            chroma_collection = f"{vendor_id}_kb"
            
            # Create vendor record in database
            SessionLocal = get_session_local()
            db = SessionLocal()
            try:
                vendor = Vendor(
                    vendor_id=vendor_id,
                    vendor_name=vendor_name,
                    company_name=company_name,
                    business_type=business_type,
                    config_path=str(config_path),
                    rag_path=str(rag_path),
                    chroma_collection=chroma_collection,
                    is_active=True,
                    vendor_metadata={
                        "created_by": "system",
                        "config_dir": str(vendor_config_dir),
                        "rag_dir": str(vendor_rag_dir)
                    }
                )
                db.add(vendor)
                db.commit()
                db.refresh(vendor)
                
                logger.info(f"Created vendor: {vendor_id} ({vendor_name})")
                
                return {
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "company_name": company_name,
                    "config_path": str(config_path),
                    "rag_path": str(rag_path),
                    "chroma_collection": chroma_collection,
                    "status": "success"
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error creating vendor {vendor_id}: {e}")
            raise
    
    def get_vendor_config_manager(self, vendor_id: str, version: Optional[str] = None) -> UnifiedConfigManager:
        """Get config manager for a specific vendor and version."""
        if version:
            config_path = self.vendors_dir / vendor_id / "versions" / version / "unified_config.json"
        else:
            config_path = self.vendors_dir / vendor_id / "unified_config.json"
        return UnifiedConfigManager(str(config_path))
    
    def get_vendor_rag_path(self, vendor_id: str, version: Optional[str] = None) -> Path:
        """Get RAG knowledge base path for a vendor and version."""
        if version:
            return self.rag_dir / vendor_id / "versions" / version / "knowledge_base.json"
        else:
            return self.rag_dir / vendor_id / "knowledge_base.json"
    
    def list_config_versions(self, vendor_id: str) -> List[str]:
        """List all config versions for a vendor."""
        versions_dir = self.vendors_dir / vendor_id / "versions"
        versions = []
        
        # Add current version (no version folder)
        current_config = self.vendors_dir / vendor_id / "unified_config.json"
        if current_config.exists():
            versions.append("current")
        
        # Add versioned configs
        if versions_dir.exists():
            for version_dir in versions_dir.iterdir():
                if version_dir.is_dir():
                    config_file = version_dir / "unified_config.json"
                    if config_file.exists():
                        versions.append(version_dir.name)
        
        return sorted(versions, key=lambda v: (v != "current", v))
    
    def list_kb_versions(self, vendor_id: str) -> List[str]:
        """List all knowledge base versions for a vendor."""
        versions_dir = self.rag_dir / vendor_id / "versions"
        versions = []
        
        # Add current version (no version folder)
        current_kb = self.rag_dir / vendor_id / "knowledge_base.json"
        if current_kb.exists():
            versions.append("current")
        
        # Add versioned KBs
        if versions_dir.exists():
            for version_dir in versions_dir.iterdir():
                if version_dir.is_dir():
                    kb_file = version_dir / "knowledge_base.json"
                    if kb_file.exists():
                        versions.append(version_dir.name)
        
        return sorted(versions, key=lambda v: (v != "current", v))
    
    def create_config_version(self, vendor_id: str, version: str, copy_from: Optional[str] = None) -> bool:
        """Create a new config version for a vendor."""
        try:
            versions_dir = self.vendors_dir / vendor_id / "versions" / version
            versions_dir.mkdir(parents=True, exist_ok=True)
            
            target_config = versions_dir / "unified_config.json"
            
            if copy_from:
                # Copy from specified version
                if copy_from == "current":
                    source_config = self.vendors_dir / vendor_id / "unified_config.json"
                else:
                    source_config = self.vendors_dir / vendor_id / "versions" / copy_from / "unified_config.json"
                
                if source_config.exists():
                    shutil.copy(source_config, target_config)
                    # Update version in metadata
                    with open(target_config, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    if "metadata" in config:
                        config["metadata"]["version"] = version
                        config["metadata"]["versioned"] = True
                    with open(target_config, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    return False
            else:
                # Create from current
                current_config = self.vendors_dir / vendor_id / "unified_config.json"
                if current_config.exists():
                    shutil.copy(current_config, target_config)
                    # Update version in metadata
                    with open(target_config, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    if "metadata" in config:
                        config["metadata"]["version"] = version
                        config["metadata"]["versioned"] = True
                    with open(target_config, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    # Create empty version
                    config_manager = UnifiedConfigManager(str(target_config))
                    default_config = config_manager._get_default_config()
                    default_config["metadata"]["version"] = version
                    default_config["metadata"]["versioned"] = True
                    config_manager.save_config(default_config)
            
            return True
        except Exception as e:
            logger.error(f"Error creating config version {version} for vendor {vendor_id}: {e}")
            return False
    
    def create_kb_version(self, vendor_id: str, version: str, copy_from: Optional[str] = None) -> bool:
        """Create a new knowledge base version for a vendor."""
        try:
            versions_dir = self.rag_dir / vendor_id / "versions" / version
            versions_dir.mkdir(parents=True, exist_ok=True)
            
            target_kb = versions_dir / "knowledge_base.json"
            
            if copy_from:
                # Copy from specified version
                if copy_from == "current":
                    source_kb = self.rag_dir / vendor_id / "knowledge_base.json"
                else:
                    source_kb = self.rag_dir / vendor_id / "versions" / copy_from / "knowledge_base.json"
                
                if source_kb.exists():
                    shutil.copy(source_kb, target_kb)
                    # Update version in metadata
                    with open(target_kb, "r", encoding="utf-8") as f:
                        kb = json.load(f)
                    if "metadata" in kb:
                        kb["metadata"]["version"] = version
                        kb["metadata"]["versioned"] = True
                    with open(target_kb, "w", encoding="utf-8") as f:
                        json.dump(kb, f, indent=2, ensure_ascii=False)
                else:
                    return False
            else:
                # Create from current
                current_kb = self.rag_dir / vendor_id / "knowledge_base.json"
                if current_kb.exists():
                    shutil.copy(current_kb, target_kb)
                    # Update version in metadata
                    with open(target_kb, "r", encoding="utf-8") as f:
                        kb = json.load(f)
                    if "metadata" in kb:
                        kb["metadata"]["version"] = version
                        kb["metadata"]["versioned"] = True
                    with open(target_kb, "w", encoding="utf-8") as f:
                        json.dump(kb, f, indent=2, ensure_ascii=False)
                else:
                    # Create empty version
                    default_kb = {
                        "metadata": {
                            "version": version,
                            "vendor_id": vendor_id,
                            "description": f"Knowledge base for vendor {vendor_id}",
                            "chunking_strategy": "semantic_chunks_with_metadata",
                            "versioned": True
                        },
                        "chunks": []
                    }
                    with open(target_kb, "w", encoding="utf-8") as f:
                        json.dump(default_kb, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Error creating KB version {version} for vendor {vendor_id}: {e}")
            return False
    
    def switch_config_version(self, vendor_id: str, version: str) -> bool:
        """Switch vendor's active config to a specific version."""
        try:
            current_config = self.vendors_dir / vendor_id / "unified_config.json"
            backup_config = self.vendors_dir / vendor_id / "unified_config.json.backup"
            
            if version == "current":
                # Already using current
                return True
            
            # Backup current config
            if current_config.exists():
                shutil.copy(current_config, backup_config)
            
            # Get version config
            version_config = self.vendors_dir / vendor_id / "versions" / version / "unified_config.json"
            if not version_config.exists():
                return False
            
            # Copy version to current
            shutil.copy(version_config, current_config)
            
            return True
        except Exception as e:
            logger.error(f"Error switching config version {version} for vendor {vendor_id}: {e}")
            return False
    
    def switch_kb_version(self, vendor_id: str, version: str) -> bool:
        """Switch vendor's active knowledge base to a specific version."""
        try:
            current_kb = self.rag_dir / vendor_id / "knowledge_base.json"
            backup_kb = self.rag_dir / vendor_id / "knowledge_base.json.backup"
            
            if version == "current":
                # Already using current
                return True
            
            # Backup current KB
            if current_kb.exists():
                shutil.copy(current_kb, backup_kb)
            
            # Get version KB
            version_kb = self.rag_dir / vendor_id / "versions" / version / "knowledge_base.json"
            if not version_kb.exists():
                return False
            
            # Copy version to current
            shutil.copy(version_kb, current_kb)
            
            return True
        except Exception as e:
            logger.error(f"Error switching KB version {version} for vendor {vendor_id}: {e}")
            return False
    
    def get_vendor_chroma_collection(self, vendor_id: str) -> str:
        """Get ChromaDB collection name for a vendor."""
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
            if vendor:
                return vendor.chroma_collection or f"{vendor_id}_kb"
            return f"{vendor_id}_kb"
        finally:
            db.close()
    
    def get_vendor_system_prompts_path(self, vendor_id: str) -> Path:
        """Get system prompts file path for a vendor."""
        return self.vendors_dir / vendor_id / "system_prompts.json"
    
    def get_vendor_chatbot_service_config_path(self, vendor_id: str) -> Path:
        """Get chatbot service config file path for a vendor."""
        return self.vendors_dir / vendor_id / "chatbot_service_config.json"
    
    def get_vendor_app_config_path(self, vendor_id: str) -> Path:
        """Get app config file path for a vendor."""
        return self.vendors_dir / vendor_id / "app_config.json"
    
    def _create_vendor_config_files(
        self,
        vendor_id: str,
        unified_config: Dict[str, Any],
        company_name: str
    ):
        """Create vendor-specific config files from unified config."""
        try:
            import json
            
            # Create system_prompts.json
            prompts_path = self.get_vendor_system_prompts_path(vendor_id)
            prompts_path.parent.mkdir(parents=True, exist_ok=True)
            prompts = unified_config.get("prompts", {})
            with open(prompts_path, "w", encoding="utf-8") as f:
                json.dump(prompts, f, indent=2, ensure_ascii=False)
            
            # Create chatbot_service_config.json
            chatbot_service_path = self.get_vendor_chatbot_service_config_path(vendor_id)
            chatbot_service_path.parent.mkdir(parents=True, exist_ok=True)
            chatbot_service = unified_config.get("chatbot_service", {})
            with open(chatbot_service_path, "w", encoding="utf-8") as f:
                json.dump(chatbot_service, f, indent=2, ensure_ascii=False)
            
            # Create app_config.json
            app_config_path = self.get_vendor_app_config_path(vendor_id)
            app_config_path.parent.mkdir(parents=True, exist_ok=True)
            business = unified_config.get("business", {})
            app_config = {
                "application": unified_config.get("application", {}),
                "database": unified_config.get("database", {}),
                "vector_database": unified_config.get("vector_database", {}),
                "embedding": unified_config.get("embedding", {}),
                "llm": unified_config.get("llm", {}),
                "openai": unified_config.get("openai", {}),
                "rag": unified_config.get("rag", {}),
                "memory": unified_config.get("memory", {}),
                "domain_restriction": unified_config.get("domain_restriction", {}),
                "credits": unified_config.get("credits", {}),
                "multi_vendor": unified_config.get("multi_vendor", {}),
                "logging": unified_config.get("logging", {}),
                "cors": unified_config.get("cors", {}),
                "security": unified_config.get("security", {}),
                "frontend": unified_config.get("frontend", {}),
                "contact": unified_config.get("contact", {}),
                "company": {
                    "name": business.get("company_name", company_name),
                    "company_number": business.get("company_number", ""),
                    "registered_address": business.get("registered_address", ""),
                    "trading_names": business.get("trading_names", [])
                },
                "branches": unified_config.get("branches", [])
            }
            with open(app_config_path, "w", encoding="utf-8") as f:
                json.dump(app_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created vendor-specific config files for {vendor_id}")
        except Exception as e:
            logger.warning(f"Error creating vendor config files: {e}")
    
    def list_vendors(self) -> list:
        """List all vendors."""
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            vendors = db.query(Vendor).all()
            return [
                {
                    "vendor_id": v.vendor_id,
                    "vendor_name": v.vendor_name,
                    "company_name": v.company_name,
                    "business_type": v.business_type,
                    "is_active": v.is_active,
                    "created_at": v.created_at.isoformat() if v.created_at else None
                }
                for v in vendors
            ]
        finally:
            db.close()
    
    def get_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """Get vendor information."""
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
            if vendor:
                return {
                    "vendor_id": vendor.vendor_id,
                    "vendor_name": vendor.vendor_name,
                    "company_name": vendor.company_name,
                    "business_type": vendor.business_type,
                    "is_active": vendor.is_active,
                    "config_path": vendor.config_path,
                    "rag_path": vendor.rag_path,
                    "chroma_collection": vendor.chroma_collection,
                    "metadata": vendor.vendor_metadata,
                    "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
                    "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None
                }
            return None
        finally:
            db.close()
    
    def update_vendor(self, vendor_id: str, **kwargs) -> bool:
        """Update vendor information."""
        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
            if not vendor:
                return False
            
            for key, value in kwargs.items():
                if hasattr(vendor, key):
                    setattr(vendor, key, value)
            
            db.commit()
            logger.info(f"Updated vendor: {vendor_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating vendor {vendor_id}: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def delete_vendor(self, vendor_id: str) -> bool:
        """Delete a vendor (soft delete by setting is_active=False)."""
        return self.update_vendor(vendor_id, is_active=False)


# Global vendor manager instance
_vendor_manager: Optional[VendorManager] = None


def get_vendor_manager() -> VendorManager:
    """Get global vendor manager instance."""
    global _vendor_manager
    if _vendor_manager is None:
        _vendor_manager = VendorManager()
    return _vendor_manager

