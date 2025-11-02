# views/pc_view.py
import streamlit as st
from workflows.client_intake import run_client_intake_workflow
from workflows.session import run_main_menu_workflow, run_session_workflow

def pc_dashboard():
    st.title("AI সুপারভিশন গাইড")
    stage = st.session_state.get("conversation_stage", "well_being_check")

    if stage.startswith("session_") or stage == "select_client_for_session":
        # The session workflow now handles both selecting and running a session
        run_session_workflow()
    elif stage.startswith("adding_client"):
        run_client_intake_workflow()
    else:
        # The main menu workflow handles well-being and the main menu
        run_main_menu_workflow()