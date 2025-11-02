# views/admin_view.py
import streamlit as st
import pandas as pd
import json
import plotly.express as px
from database import (
    get_all_pcs, add_pc, delete_pc, update_pc,
    get_all_clients, get_supervision_sessions_for_client,
    add_knowledge_entry, get_all_knowledge_entries, delete_knowledge_entry
)
from constants import SRQ_QUESTIONS
from gemini_utils import get_admin_data_insights
from utils import parse_document

# ==============================================================================
# --- HELPER & VIEW FUNCTIONS for Admin Dashboard ---
# ==============================================================================

def format_referral_status(status):
    if status == 'Yes': return '<p style="color:red; font-weight:bold;">Yes</p>'
    return '<p style="color:green;">No</p>'

def show_view_client_page():
    st.header("Client Profile")
    client_id = st.session_state.view_client_id
    client = next((c for c in get_all_clients() if c['id'] == client_id), None)
    if not client: st.error("Client not found."); st.rerun(); return

    keys = client.keys()
    acceptance = client['client_acceptance_status'] if 'client_acceptance_status' in keys else "N/A"
    referral = client['supervisor_referral'] if 'supervisor_referral' in keys else "N/A"
    
    st.subheader(f"Name: {client['name']}")
    st.markdown(f"**Client Acceptance Status:** {acceptance}")
    st.metric("Supervisor Referral Required", referral)
    st.divider()

    initial_tab, followup_tab = st.tabs(["📊 Initial Assessment", "🗂️ Supervision History"])

    with initial_tab:
        pc_note = client['pc_note'] if 'pc_note' in keys and client['pc_note'] else "No note added."
        mood = client['mood_rating_initial'] if 'mood_rating_initial' in keys else "N/A"
        st.subheader("Key Issues & Psychosocial Context")
        st.markdown(f"**Key Issues & Concerns:** {client['key_issues']}")
        st.markdown(f"**Relevant Psychosocial History:** {client['psychosocial_history']}")
        st.subheader("Para-counselor's Note (from intake)")
        st.info(pc_note)
        st.divider()

        tab_titles = ["Personal & Case Details", "Scores", "AI-Powered Analysis"]
        if referral == 'Yes': tab_titles.append("🚨 Supervisor Referral Details")
        t1, t2, t3, *t4 = st.tabs(tab_titles)

        with t1:
            st.subheader("Demographics & Session Start")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Age", str(client['age'])); c2.metric("Gender", client['gender']); c3.metric("Marital Status", client['marital_status']); c4.metric("Initial Mood Rating", f"{mood}/10")
            st.write(f"**Location:** {client['location']}")
            st.write(f"**Socio-economic Background:** {client['socio_economic_background']}")
            st.divider()
            st.subheader("Presenting Problems")
            st.write(client['presenting_problems'])
        with t2:
            st.subheader("Assessment Scores")
            srq = client['srq_score'] if 'srq_score' in keys else "N/A"
            crisis_decision = client['ai_crisis_level_decision'] if 'ai_crisis_level_decision' in keys else "AI decision not available."
            c1, c2 = st.columns(2)
            c1.metric("SRQ Score (1-20)", srq)
            c2.metric("Mood Protocol Score", f"{mood}/10")
            st.subheader("AI Crisis Level Decision")
            st.success(crisis_decision)
        with t3: st.markdown(client['ai_proposed_syndrome'])
        if t4:
            with t4[0]:
                srq_json = client['srq_responses'] if 'srq_responses' in keys else None
                if srq_json:
                    srq_responses = json.loads(srq_json)
                    with st.container(border=True):
                        st.error("Immediate escalation required:", icon="🚨")
                        if srq_responses[14] == 1: st.markdown(f"**Suicidal Thoughts:** Answered 'Yes' to: *'{SRQ_QUESTIONS[14]}'*")
                        psych_triggers = [SRQ_QUESTIONS[i] for i in range(20, 24) if srq_responses[i] == 1]
                        if psych_triggers:
                            st.markdown("**Severe Psychiatric Indicators:** Answered 'Yes' to:")
                            for q_text in psych_triggers: st.markdown(f"- *'{q_text}'*")
                else: st.warning("SRQ response data not found.")

    with followup_tab:
        st.header("Supervision Session History")
        sessions = get_supervision_sessions_for_client(client_id)
        if not sessions:
            st.info("No supervision sessions have been conducted for this client yet.")
        else:
            for session in sessions:
                with st.expander(f"**Supervision #{session['session_number']}** - Date: {session['session_date']}"):
                    st.subheader("Para-counselor's Notes")
                    st.markdown(f"**Case Management:** {session['case_management_notes']}")
                    st.markdown(f"**Challenges Faced:** {session['challenges_faced']}")
                    st.markdown(f"**Stuck Points:** {session['stuck_points']}")
                    st.markdown(f"**PC's Questions:** {session['case_questions']}")
                    st.markdown(f"**Personal Barriers:** {session['personal_barriers']}")
                    st.divider()
                    st.subheader("AI Supervision Guidance")
                    st.markdown(session['ai_supervision_guidance'])

    if st.button("⬅️ Back to Client List"):
        st.session_state.admin_view = 'list'
        del st.session_state.view_client_id
        st.rerun()

def show_edit_pc_page():
    st.header("Edit Para-counselor")
    pc_id_to_edit = st.session_state.editing_pc_id
    pc_to_edit = next((p for p in get_all_pcs() if p['id'] == pc_id_to_edit), None)
    if not pc_to_edit:
        st.error("Para-counselor not found."); st.rerun()
        return
    with st.form("edit_pc_form"):
        st.text_input("Full Name", value=pc_to_edit['full_name'], key="edit_name")
        st.text_input("Phone (Username)", value=pc_to_edit['username'], key="edit_phone")
        st.text_input("District", value=pc_to_edit['district'], key="edit_district")
        st.text_input("City", value=pc_to_edit['city'], key="edit_city")
        if st.form_submit_button("Save Changes"):
            update_pc(pc_id_to_edit, st.session_state.edit_name, st.session_state.edit_phone, st.session_state.edit_district, st.session_state.edit_city)
            st.success("Para-counselor updated successfully.")
            st.session_state.admin_view = 'list'
            del st.session_state.editing_pc_id
            st.rerun()
    if st.button("⬅️ Back to PC List"):
        st.session_state.admin_view = 'list'
        del st.session_state.editing_pc_id
        st.rerun()

def show_admin_main_page():
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Insights", "👥 Para-counselor Management", "📄 Client List", "🧠 Knowledge Base"])

    with tab1:
        st.header("Dashboard Analytics")
        all_clients = get_all_clients()
        
        if not all_clients:
            st.warning("No client data available to generate insights.")
        else:
            # --- PURE PYTHON CALCULATIONS (ROBUST METHOD) ---
            total_clients = len(all_clients)
            female_clients, male_clients = 0, 0
            total_referrals, female_referrals, male_referrals = 0, 0, 0
            gender_counts = {'পুরুষ': 0, 'মহিলা': 0, 'অন্যান্য': 0}
            
            for client in all_clients:
                keys = client.keys()
                is_referred = 'supervisor_referral' in keys and client['supervisor_referral'] == 'Yes'
                
                if 'gender' in keys and client['gender'] in gender_counts:
                    gender = client['gender']
                    gender_counts[gender] += 1
                    
                    if gender == 'মহিলা':
                        female_clients += 1
                        if is_referred: female_referrals += 1
                    elif gender == 'পুরুষ':
                        male_clients += 1
                        if is_referred: male_referrals += 1
                
                if is_referred:
                    total_referrals += 1

            st.subheader("Overall Client Numbers")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Clients", total_clients)
            c2.metric("Female Clients", female_clients)
            c3.metric("Male Clients", male_clients)
            st.divider()

            st.subheader("Supervisor Referrals")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Clients Referred", total_referrals)
            c2.metric("Female Clients Referred", female_referrals)
            c3.metric("Male Clients Referred", male_referrals)
            st.divider()

            st.subheader("Distributions")
            c1, c2, c3 = st.columns(3)
            with c1:
                valid_gender_counts = {k: v for k, v in gender_counts.items() if v > 0}
                if valid_gender_counts:
                    fig1 = px.pie(values=list(valid_gender_counts.values()), names=list(valid_gender_counts.keys()), title="Gender Distribution")
                    st.plotly_chart(fig1, use_container_width=True)
            with c2:
                female_ref_dist = {'Referred': female_referrals, 'Not Referred': female_clients - female_referrals}
                if female_clients > 0:
                    fig2 = px.pie(values=list(female_ref_dist.values()), names=list(female_ref_dist.keys()), title="Female Referral Distribution")
                    st.plotly_chart(fig2, use_container_width=True)
            with c3:
                male_ref_dist = {'Referred': male_referrals, 'Not Referred': male_clients - male_referrals}
                if male_clients > 0:
                    fig3 = px.pie(values=list(male_ref_dist.values()), names=list(male_ref_dist.keys()), title="Male Referral Distribution")
                    st.plotly_chart(fig3, use_container_width=True)
            st.divider()
            
            st.header("Ask About the Data")
            if "admin_messages" not in st.session_state:
                st.session_state.admin_messages = [{"role": "assistant", "content": "ডেটা সম্পর্কে প্রশ্ন করুন।"}]
            for message in st.session_state.admin_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            if prompt := st.chat_input("Ask a question about the client data..."):
                st.session_state.admin_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing data to find insights..."):
                        df = pd.DataFrame(all_clients) # Create DF just for the chatbot
                        response = get_admin_data_insights(prompt, df)
                        st.markdown(response)
                st.session_state.admin_messages.append({"role": "assistant", "content": response})

    with tab2:
        st.header("প্যারাক কাউন্সেলর যোগ করুন")
        with st.expander("➕ একজন নতুন প্যারাক কাউন্সেলর যোগ করুন", expanded=False):
            with st.form("add_pc_form", clear_on_submit=True):
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                phone = st.text_input("Phone Number (username)")
                district = st.text_input("District")
                city = st.text_input("City / Area")
                submitted = st.form_submit_button("Create Para-counselor")
                if submitted:
                    if all([first_name, last_name, phone, district, city]):
                        password = f"{phone[-4:]}@{first_name.lower().strip()}"
                        full_name = f"{first_name.strip()} {last_name.strip()}"
                        success, message = add_pc(phone, password, full_name, district, city)
                        if success: st.success(f"Success! PC '{full_name}' created. Pass: `{password}`")
                        else: st.error(f"Error: {message}")
                    else: st.warning("Please fill all fields.")
        st.divider()
        st.header("প্যারাক কাউন্সেলরদের তালিকা")
        pcs = get_all_pcs()
        if not pcs: st.warning("No Para-counselors added yet.")
        else:
            cols = st.columns((0.5, 2, 2, 1, 1, 2))
            fields = ["ID", "Full Name", "Phone", "District", "City", "Actions"]
            for col, field_name in zip(cols, fields): col.write(f"**{field_name}**")
            for pc in pcs:
                col1, col2, col3, col4, col5, col6 = st.columns((0.5, 2, 2, 1, 1, 2))
                with col1: st.write(pc['id'])
                with col2: st.write(pc['full_name'])
                with col3: st.write(pc['username'])
                with col4: st.write(pc['district'])
                with col5: st.write(pc['city'])
                with col6:
                    b_col1, b_col2 = st.columns(2)
                    if b_col1.button("✏️ Edit", key=f"edit_{pc['id']}", use_container_width=True):
                        st.session_state.admin_view = 'edit_pc'
                        st.session_state.editing_pc_id = pc['id']
                        st.rerun()
                    if b_col2.button("🗑️ Delete", key=f"delete_{pc['id']}", use_container_width=True):
                        delete_pc(pc['id'])
                        st.rerun()
                st.divider()
    with tab3:
        st.header("সকল ক্লায়েন্ট")
        clients = get_all_clients()
        if not clients: st.info("No clients added yet.")
        else:
            cols = st.columns((0.7, 2, 1, 1.5, 2))
            fields = ["ID", "ক্লায়েন্টের নাম", "লিঙ্গ", "সুপারভাইজার রেফারেল", "Actions"]
            for col, field_name in zip(cols, fields): col.write(f"**{field_name}**")
            st.divider()
            for client in clients:
                col1, col2, col3, col4, col5 = st.columns((0.7, 2, 1, 1.5, 2))
                with col1: st.write(client['id'])
                with col2: st.write(client['name'])
                with col3:
                    gender = client['gender'] if 'gender' in client.keys() else 'N/A'
                    st.write(gender)
                with col4:
                    referral_status = client['supervisor_referral'] if 'supervisor_referral' in client.keys() else 'No'
                    st.markdown(format_referral_status(referral_status), unsafe_allow_html=True)
                with col5:
                    if st.button("View Details", key=f"view_{client['id']}", use_container_width=True):
                        st.session_state.admin_view = 'view_client'
                        st.session_state.view_client_id = client['id']
                        st.rerun()
                st.divider()
    
    with tab4:
        st.header("🧠 AI Knowledge Base Management")
        st.write("Add or modify instructions and documents to guide the AI's behavior across the application.")
        BOT_LIST = [
            "The Para-counselor (PC) Well-being Bot", "The Client Intake Bot", "The Session Guide Bot",
            "The Admin Data Analyst Bot", "The Clinical Report Writer Bot", "The Risk Assessment Bot", "The Scheduling Assistant Bot"
        ]
        with st.form("knowledge_form", clear_on_submit=True):
            st.subheader("Add New Knowledge Entry")
            title = st.text_input("Context Title", placeholder="e.g., Assessing Emotional Readiness of the User")
            instruction = st.text_area("Instructions for the AI", placeholder="e.g., Use this guide to assess the emotion readiness of the user...")
            uploaded_file = st.file_uploader("Upload a Document (Optional)", type=['pdf', 'docx', 'csv'])
            importance = st.slider("Importance (1=Low, 10=High)", 1, 10, 5)
            target_bots = st.multiselect("Apply to which Bot(s)? (Select 'General' for all)", options=["General"] + BOT_LIST)
            submitted = st.form_submit_button("Add to Knowledge Base")
            if submitted:
                if title and instruction and target_bots:
                    doc_content = parse_document(uploaded_file)
                    add_knowledge_entry(title, instruction, doc_content, importance, target_bots)
                    st.success(f"Knowledge entry '{title}' added successfully!")
                else:
                    st.warning("Please fill in Title, Instructions, and at least one Target Bot.")
        st.divider()
        st.subheader("Existing Knowledge Entries")
        entries = get_all_knowledge_entries()
        if not entries:
            st.info("No knowledge base entries have been added yet.")
        else:
            for entry in entries:
                with st.expander(f"**{entry['title']}** (Importance: {entry['importance_score']}/10)"):
                    st.markdown(f"**Instructions:**\n> {entry['instruction_text']}")
                    targets = json.loads(entry['target_bots'])
                    st.write(f"**Applied to:** {', '.join(targets)}")
                    if entry['document_content']:
                        st.text_area("Document Content (Preview)", value=entry['document_content'][:500] + "...", height=150, disabled=True)
                    if st.button("Delete Entry", key=f"del_kb_{entry['id']}", type="primary"):
                        delete_knowledge_entry(entry['id'])
                        st.rerun()

# --- MAIN DASHBOARD ROUTER ---
def admin_dashboard():
    if 'admin_view' not in st.session_state: st.session_state.admin_view = 'list'
    if st.session_state.admin_view == 'view_client': show_view_client_page()
    elif st.session_state.admin_view == 'edit_pc': show_edit_pc_page()
    else: show_admin_main_page()