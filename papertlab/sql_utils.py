import sqlite3

def get_auto_commit_db_status(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'auto_commit'")
    result = cursor.fetchone()
    conn.close()

    if result[0] == 'True':
        return True
    return False

def init_db(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            model TEXT,
            input_token INTEGER,
            output_token INTEGER,
            cost REAL,
            total_cost REAL,
            datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if all required columns exist, if not, add them
    cursor.execute("PRAGMA table_info(project_usage)")
    columns = [column[1] for column in cursor.fetchall()]
    required_columns = ['project_id','model', 'input_token', 'output_token', 'cost', 'total_cost', 'datetime']
    for column in required_columns:
        if column not in columns:
            cursor.execute(f'ALTER TABLE project_usage ADD COLUMN {column}')
            if column == 'datetime':
                cursor.execute(f'UPDATE project_usage SET {column} = CURRENT_TIMESTAMP WHERE {column} IS NULL')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        );
    ''')

    # Insert default auto_commit value if not present
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('auto_commit', 'True')")

    conn.commit()
    conn.close()