# auth.py
import sqlite3
import hashlib
import streamlit as st
from database import get_db_connection

def verify_user(username, password):
    """Verifies user credentials against the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    )
    user = cursor.fetchone()
    conn.close()
    return user

def login_form():
    """Displays the login form and handles authentication."""
    st.header("BRAC AI গাইড - লগইন")
    with st.form("login_form"):
        username = st.text_input("ইউজারনেম")
        password = st.text_input("পাসওয়ার্ড", type="password")
        submitted = st.form_submit_button("লগইন করুন")

        if submitted:
            user = verify_user(username, password)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["username"] = user["username"]
                st.session_state["user_id"] = user["id"]
                st.session_state["full_name"] = user["full_name"]
                st.session_state["role"] = user["role"]
                st.rerun()
            else:
                st.error("ইউজারনেম অথবা পাসওয়ার্ড সঠিক নয়।")