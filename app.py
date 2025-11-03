# app.py
import streamlit as st
from database import setup_database
from auth import login_form
from views.admin_view import admin_dashboard
from views.pc_view import pc_dashboard

st.set_page_config(page_title="BRAC IED PARA-COUNSELLOR AI GUIDE", layout="wide")

setup_database()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "admin_view" not in st.session_state: st.session_state.admin_view = 'list'
if "conversation_stage" not in st.session_state: st.session_state.conversation_stage = 'well_being_check'

if not st.session_state.logged_in:
    login_form()
else:
    with st.sidebar:
        st.subheader(f"স্বাগতম, {st.session_state.full_name}")
        role_display = "অ্যাডমিন" if st.session_state.role == 'admin' else "প্যারাক কাউন্সেলর"
        st.write(f"ভূমিকা: {role_display}")
        if st.button("লগআউট"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    if st.session_state.role == 'admin': admin_dashboard()
    elif st.session_state.role == 'pc': pc_dashboard()