import sqlite3


def store_project_usage_db(DB_PATH, project_name, model, temp_coder):
    cost = getattr(temp_coder, 'cost', 0)
    total_cost = getattr(temp_coder, 'total_cost', 0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
                INSERT INTO project_usage (project_id, model, input_token, output_token, cost, total_cost, datetime)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (project_name, model, temp_coder.input_token, temp_coder.output_token, cost, total_cost))
    conn.commit()
    conn.close()
    

def get_latest_usage_db(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(input_token + output_token) as total_tokens, SUM(cost) as total_cost
        FROM project_usage
    ''')
    result = cursor.fetchone()
    conn.close()
    return result

def get_monthly_usage_db(DB_PATH, first_day_of_month):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total tokens and cost for the current month
    cursor.execute('''
        SELECT SUM(input_token + output_token) as total_tokens, SUM(cost) as total_cost
        FROM project_usage
        WHERE datetime >= ?
    ''', (first_day_of_month,))
    
    result = cursor.fetchone()
    conn.close()

    return result

def get_usage_data_db(DB_PATH, per_page, offset):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM project_usage')
    total_count = cursor.fetchone()[0]
    
    # Get paginated data
    cursor.execute('''
        SELECT id, project_id, model, input_token, output_token, cost, total_cost, datetime
        FROM project_usage
        ORDER BY datetime DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    results = cursor.fetchall()
    conn.close()

    return total_count, results


def save_auto_commit_db(DB_PATH, auto_commit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Save or update the auto_commit setting
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ('auto_commit', str(auto_commit)))
    conn.commit()
    conn.close()
    return True

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