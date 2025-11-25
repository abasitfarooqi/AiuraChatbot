#!/usr/bin/env python3
"""
List all tables in the MySQL database aiura_chatbots.
Uses credentials from environment variables or prompts for them.
"""
import os
import sys
import pymysql
from getpass import getpass

def get_mysql_credentials():
    """Get MySQL credentials from environment or prompt."""
    db_host = os.getenv('MYSQL_HOST', 'localhost')
    db_port = int(os.getenv('MYSQL_PORT', '3306'))
    db_user = os.getenv('MYSQL_USER', 'aiura_chatbot')
    db_password = os.getenv('MYSQL_PASSWORD', None)
    db_name = os.getenv('MYSQL_DATABASE', 'aiura_chatbots')
    
    # If password not in env, prompt for it
    if not db_password:
        print(f"MySQL credentials:")
        print(f"  Host: {db_host}:{db_port}")
        print(f"  Database: {db_name}")
        print(f"  User: {db_user}")
        db_password = getpass("  Password: ")
    
    return db_host, db_port, db_user, db_password, db_name

def list_tables():
    """List all tables in the MySQL database."""
    db_host, db_port, db_user, db_password, db_name = get_mysql_credentials()
    
    print('=' * 80)
    print('CONNECTING TO MYSQL DATABASE')
    print('=' * 80)
    print(f'Host: {db_host}:{db_port}')
    print(f'Database: {db_name}')
    print(f'User: {db_user}')
    print()
    
    try:
        # Connect to MySQL
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4'
        )
        
        print('✅ Connected to MySQL successfully!')
        print()
        
        # Get all tables
        cursor = connection.cursor()
        cursor.execute('SHOW TABLES')
        tables = [row[0] for row in cursor.fetchall()]
        
        print('=' * 80)
        print(f'ALL TABLES IN MySQL DATABASE: {db_name}')
        print('=' * 80)
        print(f'Total tables: {len(tables)}')
        print()
        
        # Categorize tables
        categories = {
            'Core Platform': ['admins', 'vendors', 'users', 'roles', 'user_roles'],
            'Chat System (New)': ['chat_users', 'chat_sessions', 'chat_messages', 'conversation_memories', 'suggestion_cache'],
            'Legacy Chat': ['chats', 'messages', 'conversation_memory', 'token_usage'],
            'Models & LLM': ['models', 'model_configs', 'model_presets', 'model_cache'],
            'Knowledge Base': ['knowledge_bases', 'kb_documents', 'kb_embeddings_refs'],
            'Caching': ['main_cache', 'temporary_cache'],
            'Billing': ['billing_plans', 'quota_allocations', 'usage_records', 'invoices', 'payments'],
            'Vendor Config': ['vendor_configs', 'vendor_endpoints'],
            'API & Security': ['api_keys', 'rate_limits', 'ip_allowlist', 'webhook_deliveries'],
            'System': ['vendor_model_assignments', 'audit_logs', 'feature_flags', 'support_tickets', 'notifications', 'data_export_requests']
        }
        
        # Print categorized
        for category, expected_tables in categories.items():
            found = [t for t in expected_tables if t in tables]
            if found:
                print(f'{category}:')
                for table in sorted(found):
                    status = '⚠️ LEGACY' if category == 'Legacy Chat' else '✅'
                    print(f'  {status} {table}')
                print()
        
        # Show uncategorized
        categorized = [t for tables_list in categories.values() for t in tables_list]
        uncategorized = [t for t in tables if t not in categorized]
        if uncategorized:
            print('Uncategorized Tables:')
            for table in sorted(uncategorized):
                print(f'  ⚠️ {table}')
            print()
        
        # Print full list
        print('=' * 80)
        print('COMPLETE TABLE LIST (Alphabetical)')
        print('=' * 80)
        for i, table in enumerate(sorted(tables), 1):
            print(f'{i:2d}. {table}')
        
        print()
        print('=' * 80)
        print(f'Total: {len(tables)} tables')
        print('=' * 80)
        
        # Get table counts
        print()
        print('=' * 80)
        print('TABLE RECORD COUNTS')
        print('=' * 80)
        for table in sorted(tables):
            try:
                cursor.execute(f'SELECT COUNT(*) FROM `{table}`')
                count = cursor.fetchone()[0]
                print(f'{table:40s} : {count:>10,} records')
            except Exception as e:
                print(f'{table:40s} : ERROR - {str(e)[:50]}')
        
        connection.close()
        print()
        print('✅ Connection closed')
        return tables
        
    except pymysql.Error as e:
        print(f'❌ MySQL Error: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    list_tables()

