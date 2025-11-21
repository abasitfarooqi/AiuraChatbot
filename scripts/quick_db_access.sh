#!/bin/bash
# Quick database access script for AiuraChatbot

DB_FILE="./data/chatbot.db"

echo "=== AiuraChatbot Database Quick Access ==="
echo ""

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "❌ Database file not found: $DB_FILE"
    echo "   Run: python3 scripts/init_saas_db.py"
    exit 1
fi

echo "Database: $DB_FILE"
echo ""

# Function to show menu
show_menu() {
    echo "Choose an option:"
    echo "1. Open SQLite interactive shell"
    echo "2. List all tables"
    echo "3. Show vendor information"
    echo "4. Show table schema"
    echo "5. Count records in all tables"
    echo "6. Export vendors to CSV"
    echo "7. Backup database"
    echo "8. Show database info"
    echo "9. Exit"
    echo ""
}

# Function to list tables
list_tables() {
    echo "=== All Tables ==="
    sqlite3 "$DB_FILE" ".tables"
    echo ""
}

# Function to show vendors
show_vendors() {
    echo "=== Vendors ==="
    sqlite3 -header -column "$DB_FILE" "SELECT id, slug, name, status, plan_code, credit_balance, created_at FROM vendors;"
    echo ""
}

# Function to show schema
show_schema() {
    read -p "Enter table name (or 'all' for all tables): " table_name
    if [ "$table_name" = "all" ]; then
        sqlite3 "$DB_FILE" ".schema"
    else
        sqlite3 "$DB_FILE" ".schema $table_name"
    fi
    echo ""
}

# Function to count records
count_records() {
    echo "=== Record Counts ==="
    sqlite3 -header -column "$DB_FILE" "
    SELECT 'vendors' as table_name, COUNT(*) as count FROM vendors
    UNION ALL SELECT 'users', COUNT(*) FROM users
    UNION ALL SELECT 'models', COUNT(*) FROM models
    UNION ALL SELECT 'roles', COUNT(*) FROM roles
    UNION ALL SELECT 'billing_plans', COUNT(*) FROM billing_plans
    UNION ALL SELECT 'quota_allocations', COUNT(*) FROM quota_allocations
    UNION ALL SELECT 'knowledge_bases', COUNT(*) FROM knowledge_bases
    UNION ALL SELECT 'vendor_configs', COUNT(*) FROM vendor_configs
    UNION ALL SELECT 'vendor_model_assignments', COUNT(*) FROM vendor_model_assignments
    ORDER BY table_name;
    "
    echo ""
}

# Function to export vendors
export_vendors() {
    output_file="vendors_export_$(date +%Y%m%d_%H%M%S).csv"
    sqlite3 -header -csv "$DB_FILE" "SELECT * FROM vendors;" > "$output_file"
    echo "✅ Exported to: $output_file"
    echo ""
}

# Function to backup
backup_db() {
    backup_file="data/chatbot_backup_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB_FILE" "$backup_file"
    echo "✅ Backup created: $backup_file"
    echo ""
}

# Function to show database info
show_info() {
    echo "=== Database Information ==="
    echo "File: $DB_FILE"
    echo "Size: $(du -h "$DB_FILE" | cut -f1)"
    echo "Modified: $(stat -f "%Sm" "$DB_FILE")"
    echo ""
    echo "Table count: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';")"
    echo ""
}

# Main loop
while true; do
    show_menu
    read -p "Enter choice (1-9): " choice
    echo ""
    
    case $choice in
        1)
            echo "Opening SQLite shell..."
            echo "Type '.quit' to exit"
            echo ""
            sqlite3 "$DB_FILE"
            ;;
        2)
            list_tables
            ;;
        3)
            show_vendors
            ;;
        4)
            show_schema
            ;;
        5)
            count_records
            ;;
        6)
            export_vendors
            ;;
        7)
            backup_db
            ;;
        8)
            show_info
            ;;
        9)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            echo ""
            ;;
    esac
    
    read -p "Press Enter to continue..."
    clear
done

