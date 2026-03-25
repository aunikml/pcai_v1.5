# auth.py
import hashlib
import streamlit as st
from database import get_db_connection

def verify_user(username, password):
    """Verifies user credentials against the database."""
    conn = None
    cursor = None # Initialize cursor
    try:
        conn = get_db_connection()
        # --- THIS IS THE FIX ---
        # Manually create and close the cursor instead of using a 'with' statement.
        # This is compatible with both sqlite3 and psycopg2.
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Determine the correct placeholder style based on the connection type
        placeholder = "%s"
        if "sqlite" in conn.__class__.__module__:
            placeholder = "?"

        sql_query = f"SELECT * FROM users WHERE username = {placeholder} AND password_hash = {placeholder}"
        
        cursor.execute(sql_query, (username, password_hash))
        user = cursor.fetchone()
        
        return user
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None
    finally:
        # Ensure both cursor and connection are closed if they were created
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def login_form():
    """Displays a clean, modern, centered-card login page."""
    # (The rest of the file is the same as the previous "redesign" version)
    # --- Custom CSS for the complete redesign ---
    st.markdown("""
        <style>
        /* Main container styling */
        [data-testid="stAppViewContainer"] > .main {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
            background: linear-gradient(to top right, #e0eafc, #ffffff);
        }
        .login-card {
            # background-color: white;
            # padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 450px;
        }
        [data-testid="stTextInput"] input {
            background-color: #f0f2f6;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
        }
        .stButton button {
            background-color: #0052cc;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px;
            font-size: 1.1em;
            font-weight: bold;
            width: 100%;
        }
        .stButton button:hover {
            background-color: #0041a3;
        }
        </style>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([0.3, 0.4, 0.3])
    with center_col:
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)
        
        logo_cols = st.columns([1, 1.5, 1])
        with logo_cols[1]:
            try:
                st.image("assets/logo.png", use_container_width=True)
            except FileNotFoundError:
                st.markdown("<h2 style='text-align: center; color: #0047AB;'>BRAC IED</h2>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown( """ <div style="text-align: center;"> <h2 style=" display: inline-block; padding-bottom: 5px; border-bottom: 3px solid #3498DB; color: #2C3E50; "> Para-Counsellor AI Guide </h2> </div> """, unsafe_allow_html=True )

        
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; color: #333; font-weight: 600;'>Welcome Back</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #666;'>Please login to your account</p>", unsafe_allow_html=True)
            
            username = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Login")

            if submitted:
                if not username or not password:
                    st.warning("Please enter your username and password.")
                else:
                    user = verify_user(username, password)
                    if user:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = user['username']
                        st.session_state["user_id"] = user['id']
                        st.session_state["full_name"] = user['full_name']
                        st.session_state["role"] = user['role']
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")
        
        st.markdown("</div>", unsafe_allow_html=True)