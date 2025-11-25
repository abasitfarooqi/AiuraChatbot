#!/usr/bin/env python3
"""
Migration script to:
1. Create chat_users table
2. Migrate existing chat_sessions to use chat_users instead of users
3. Update conversation_memories to use chat_users
4. Update suggestion_cache to use chat_users
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.config.database import get_database_engine, get_session_local
from backend.models.saas_models import (
    Base, ChatUser, ChatSession, ConversationMemory, SuggestionCache, Vendor, User
)
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from datetime import datetime

def migrate_to_chat_users():
    """Migrate existing data to use chat_users table."""
    try:
        logger.info("Starting migration to chat_users...")
        
        # Get database engine
        engine = get_database_engine()
        
        # Create chat_users table
        logger.info("Creating chat_users table...")
        ChatUser.__table__.create(engine, checkfirst=True)
        logger.info("✅ chat_users table created")
        
        # Get database session
        SessionLocal = get_session_local()
        db: Session = SessionLocal()
        
        try:
            # Step 1: Migrate existing chat_sessions to chat_users
            logger.info("Migrating chat_sessions to use chat_users...")
            
            # Check if old user_id column exists in the database
            inspector = inspect(engine)
            chat_sessions_columns = [col['name'] for col in inspector.get_columns('chat_sessions')]
            has_old_user_id = 'user_id' in chat_sessions_columns
            
            migrated_count = 0
            
            if has_old_user_id:
                # Use raw SQL to query the old user_id column
                logger.info("Found old 'user_id' column, migrating data...")
                result = db.execute(text("""
                    SELECT id, vendor_id, user_id, created_at 
                    FROM chat_sessions 
                    WHERE user_id IS NOT NULL
                """))
                
                for row in result:
                    try:
                        session_id, vendor_id, old_user_id, created_at = row
                        
                        # Get vendor
                        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
                        if not vendor:
                            logger.warning(f"Vendor {vendor_id} not found for session {session_id}")
                            continue
                        
                        # Get user
                        user = db.query(User).filter(User.id == old_user_id).first()
                        if not user:
                            logger.warning(f"User {old_user_id} not found for session {session_id}")
                            continue
                        
                        # Create or get chat_user
                        identifier = user.email or f"user_{user.id}"
                        chat_user = db.query(ChatUser).filter(
                            ChatUser.vendor_id == vendor.id,
                            ChatUser.identifier == identifier
                        ).first()
                        
                        if not chat_user:
                            chat_user = ChatUser(
                                vendor_id=vendor.id,
                                identifier=identifier,
                                name=user.name or identifier,
                                email=user.email,
                                is_anonymous=False,  # These are actual users
                                last_chat_at=created_at
                            )
                            db.add(chat_user)
                            db.flush()
                            logger.debug(f"Created chat_user {chat_user.id} for user {user.id}")
                        
                        # Update session to use chat_user_id using raw SQL
                        db.execute(text("""
                            UPDATE chat_sessions 
                            SET chat_user_id = :chat_user_id 
                            WHERE id = :session_id
                        """), {"chat_user_id": chat_user.id, "session_id": session_id})
                        
                        migrated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error migrating session {session_id}: {e}")
                        continue
            else:
                logger.info("No old 'user_id' column found. All sessions should already use chat_user_id.")
                # Check if there are any sessions without chat_user_id
                sessions_without_chat_user = db.execute(text("""
                    SELECT id FROM chat_sessions WHERE chat_user_id IS NULL
                """)).fetchall()
                
                if sessions_without_chat_user:
                    logger.warning(f"Found {len(sessions_without_chat_user)} sessions without chat_user_id. Creating anonymous chat_users...")
                    for (session_id,) in sessions_without_chat_user:
                        try:
                            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                            if not session:
                                continue
                            
                            vendor = db.query(Vendor).filter(Vendor.id == session.vendor_id).first()
                            if not vendor:
                                continue
                            
                            # Create anonymous chat_user
                            identifier = f"anonymous_{session_id}"
                            chat_user = ChatUser(
                                vendor_id=vendor.id,
                                identifier=identifier,
                                name=f"Anonymous User {session_id}",
                                is_anonymous=True,
                                last_chat_at=session.created_at
                            )
                            db.add(chat_user)
                            db.flush()
                            
                            session.chat_user_id = chat_user.id
                            migrated_count += 1
                        except Exception as e:
                            logger.error(f"Error creating chat_user for session {session_id}: {e}")
                            continue
            
            db.commit()
            logger.info(f"✅ Migrated {migrated_count} chat_sessions to use chat_users")
            
            # Step 2: Migrate conversation_memories
            logger.info("Migrating conversation_memories to use chat_users...")
            
            memories = db.query(ConversationMemory).all()
            memory_migrated = 0
            
            for memory in memories:
                try:
                    # Get chat session
                    if memory.session_id:
                        session = db.query(ChatSession).filter(
                            ChatSession.id == memory.session_id
                        ).first()
                        if session and session.chat_user_id:
                            memory.chat_user_id = session.chat_user_id
                            memory_migrated += 1
                    elif memory.chat_id:
                        # Try to find session by chat_id
                        session = db.query(ChatSession).filter(
                            ChatSession.session_uuid == memory.chat_id
                        ).first()
                        if session and session.chat_user_id:
                            memory.chat_user_id = session.chat_user_id
                            memory_migrated += 1
                            
                except Exception as e:
                    logger.error(f"Error migrating memory {memory.id}: {e}")
                    continue
            
            db.commit()
            logger.info(f"✅ Migrated {memory_migrated} conversation_memories to use chat_users")
            
            # Step 3: Migrate suggestion_cache (if it has user_id)
            logger.info("Migrating suggestion_cache to use chat_users...")
            
            # Check if old user_id column exists
            suggestion_cache_columns = [col['name'] for col in inspector.get_columns('suggestion_cache')]
            has_old_user_id_suggestion = 'user_id' in suggestion_cache_columns
            
            suggestion_migrated = 0
            
            if has_old_user_id_suggestion:
                # Use raw SQL to query the old user_id column
                result = db.execute(text("""
                    SELECT id, vendor_id, user_id 
                    FROM suggestion_cache 
                    WHERE user_id IS NOT NULL
                """))
                
                for row in result:
                    try:
                        suggestion_id, vendor_id, old_user_id = row
                        
                        # Get vendor
                        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
                        if not vendor:
                            continue
                        
                        # Get user
                        user = db.query(User).filter(User.id == old_user_id).first()
                        if not user:
                            continue
                        
                        # Find or create chat_user
                        identifier = user.email or f"user_{user.id}"
                        chat_user = db.query(ChatUser).filter(
                            ChatUser.vendor_id == vendor.id,
                            ChatUser.identifier == identifier
                        ).first()
                        
                        if chat_user:
                            db.execute(text("""
                                UPDATE suggestion_cache 
                                SET chat_user_id = :chat_user_id 
                                WHERE id = :suggestion_id
                            """), {"chat_user_id": chat_user.id, "suggestion_id": suggestion_id})
                            suggestion_migrated += 1
                            
                    except Exception as e:
                        logger.error(f"Error migrating suggestion {suggestion_id}: {e}")
                        continue
            else:
                logger.info("No old 'user_id' column found in suggestion_cache. Skipping migration.")
            
            db.commit()
            logger.info(f"✅ Migrated {suggestion_migrated} suggestion_cache entries to use chat_users")
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ Migration to chat_users completed successfully!")
            logger.info("=" * 60)
            logger.info(f"  - Chat sessions migrated: {migrated_count}")
            logger.info(f"  - Conversation memories migrated: {memory_migrated}")
            logger.info(f"  - Suggestion cache entries migrated: {suggestion_migrated}")
            logger.info("")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate_to_chat_users()

