# database.py
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta

DB_NAME = "brac_bot.db"

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Creates and updates all necessary tables with robust migration checks."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Users Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin', 'pc')), district TEXT, city TEXT
        )''')

    # --- Clients Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER, 
            gender TEXT CHECK(gender IN ('পুরুষ', 'মহিলা', 'অন্যান্য')), 
            marital_status TEXT CHECK(marital_status IN ('বিবাহিত', 'অবিবাহিত', 'পৃথক', 'তালাকপ্রাপ্ত', 'বিধবা')),
            location TEXT, srq_score INTEGER, socio_economic_background TEXT, presenting_problems TEXT, key_issues TEXT,
            psychosocial_history TEXT, ai_proposed_syndrome TEXT, created_by_pc_id INTEGER,
            client_acceptance_status TEXT, supervisor_referral TEXT, srq_responses TEXT,
            mood_rating_initial INTEGER, pc_note TEXT, ai_crisis_level_decision TEXT,
            next_followup_date TEXT,
            FOREIGN KEY (created_by_pc_id) REFERENCES users (id)
        )''')
    
    # --- REDESIGNED SESSIONS TABLE for SUPERVISION ---
    cursor.execute("DROP TABLE IF EXISTS sessions") 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supervision_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            pc_id INTEGER NOT NULL,
            session_number INTEGER NOT NULL,
            session_date TEXT,
            case_management_notes TEXT,
            challenges_faced TEXT,
            stuck_points TEXT,
            case_questions TEXT,
            personal_barriers TEXT,
            ai_supervision_guidance TEXT,
            sessions_taken_by_pc INTEGER,
            client_current_mood INTEGER,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (pc_id) REFERENCES users (id)
        )
    ''')
    
    # --- Knowledge Base Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            instruction_text TEXT NOT NULL,
            document_content TEXT,
            importance_score INTEGER NOT NULL,
            target_bots TEXT NOT NULL
        )
    ''')

    # --- Comprehensive Schema Migration for clients table ---
    client_columns = [col[1] for col in cursor.execute("PRAGMA table_info(clients)").fetchall()]
    if 'first_session_proposed_date' in client_columns:
        cursor.execute("ALTER TABLE clients RENAME COLUMN first_session_proposed_date TO next_followup_date")
    if 'next_followup_date' not in client_columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN next_followup_date TEXT")
        
    # Add default admin if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        admin_pass_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",('admin', admin_pass_hash, 'Admin User', 'admin'))

    conn.commit()
    conn.close()

# --- User Management ---
def add_pc(username, password, full_name, district, city):
    conn = get_db_connection()
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn.execute("INSERT INTO users (username, password_hash, full_name, role, district, city) VALUES (?, ?, ?, 'pc', ?, ?)",(username, password_hash, full_name, district, city))
        conn.commit()
        return True, "User added successfully."
    except sqlite3.IntegrityError: return False, "This phone number is already registered."
    finally: conn.close()
def get_all_pcs():
    conn = get_db_connection()
    pcs = conn.execute("SELECT id, username, full_name, district, city FROM users WHERE role = 'pc'").fetchall()
    conn.close()
    return pcs
def update_pc(pc_id, full_name, username, district, city):
    conn = get_db_connection()
    conn.execute("UPDATE users SET full_name = ?, username = ?, district = ?, city = ? WHERE id = ?",(full_name, username, district, city, pc_id))
    conn.commit()
    conn.close()
def delete_pc(pc_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM supervision_sessions WHERE pc_id = ?", (pc_id,))
    conn.execute("DELETE FROM clients WHERE created_by_pc_id = ?", (pc_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (pc_id,))
    conn.commit()
    conn.close()

# --- Client and Session Management ---
def add_client(client_data):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO clients (name, age, gender, marital_status, location, srq_score, socio_economic_background, 
        presenting_problems, key_issues, psychosocial_history, ai_proposed_syndrome, created_by_pc_id, 
        client_acceptance_status, supervisor_referral, srq_responses, mood_rating_initial, pc_note, 
        ai_crisis_level_decision, next_followup_date) 
        VALUES (:name, :age, :gender, :marital_status, :location, :srq_score, :socio_economic_background, 
        :presenting_problems, :key_issues, :psychosocial_history, :ai_proposed_syndrome, :created_by_pc_id, 
        :client_acceptance_status, :supervisor_referral, :srq_responses, :mood_rating_initial, :pc_note, 
        :ai_crisis_level_decision, :next_followup_date)
    ''', {
        'name': client_data.get('name'),'age': client_data.get('age'),'gender': client_data.get('gender'),
        'marital_status': client_data.get('marital_status'),'location': client_data.get('location'),
        'srq_score': client_data.get('srq_score'),'socio_economic_background': client_data.get('socio_economic_background'),
        'presenting_problems': client_data.get('presenting_problems'),'key_issues': client_data.get('key_issues'),
        'psychosocial_history': client_data.get('psychosocial_history'),
        'ai_proposed_syndrome': client_data.get('ai_proposed_syndrome'),'created_by_pc_id': client_data.get('created_by_pc_id'),
        'client_acceptance_status': client_data.get('client_acceptance_status'),'supervisor_referral': client_data.get('supervisor_referral'),
        'srq_responses': client_data.get('srq_responses'),'mood_rating_initial': client_data.get('mood_rating_initial'),
        'pc_note': client_data.get('pc_note'),'ai_crisis_level_decision': client_data.get('ai_crisis_level_decision'),
        'next_followup_date': client_data.get('next_followup_date')
    })
    conn.commit()
    conn.close()

def get_all_clients():
    conn = get_db_connection()
    clients = conn.execute("SELECT c.*, u.full_name as pc_name FROM clients c LEFT JOIN users u ON c.created_by_pc_id = u.id").fetchall()
    conn.close()
    return clients

def get_clients_for_pc(pc_id):
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients WHERE created_by_pc_id = ?", (pc_id,)).fetchall()
    conn.close()
    return clients

def add_supervision_session(session_data):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO supervision_sessions (
            client_id, pc_id, session_number, session_date, case_management_notes,
            challenges_faced, stuck_points, case_questions, personal_barriers,
            ai_supervision_guidance, sessions_taken_by_pc, client_current_mood
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_data.get('client_id'), session_data.get('pc_id'), session_data.get('session_number'),
        session_data.get('session_date'), session_data.get('case_management_notes'),
        session_data.get('challenges_faced'), session_data.get('stuck_points'),
        session_data.get('case_questions'), session_data.get('personal_barriers'),
        session_data.get('ai_supervision_guidance'), session_data.get('sessions_taken_by_pc'),
        session_data.get('client_current_mood')
    ))
    conn.commit()
    conn.close()
    
def get_completed_supervision_count(client_id, pc_id):
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(id) FROM supervision_sessions WHERE client_id = ? AND pc_id = ?", (client_id, pc_id)).fetchone()[0]
    conn.close()
    return count

def get_supervision_sessions_for_client(client_id):
    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM supervision_sessions WHERE client_id = ? ORDER BY session_number ASC", (client_id,)).fetchall()
    conn.close()
    return sessions

# --- KNOWLEDGE BASE MANAGEMENT ---
def add_knowledge_entry(title, instruction, doc_content, importance, targets):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO knowledge_base (title, instruction_text, document_content, importance_score, target_bots) VALUES (?, ?, ?, ?, ?)",
        (title, instruction, doc_content, importance, json.dumps(targets, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
def get_all_knowledge_entries():
    conn = get_db_connection()
    entries = conn.execute("SELECT * FROM knowledge_base ORDER BY importance_score DESC").fetchall()
    conn.close()
    return entries
def get_knowledge_for_bots(bot_names: list):
    conn = get_db_connection()
    all_knowledge = conn.execute("SELECT * FROM knowledge_base ORDER BY importance_score DESC").fetchall()
    conn.close()
    relevant_knowledge = []
    for entry in all_knowledge:
        targets = json.loads(entry['target_bots'])
        if "General" in targets or any(name in targets for name in bot_names):
            relevant_knowledge.append(entry)
    return relevant_knowledge
def delete_knowledge_entry(entry_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM knowledge_base WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()