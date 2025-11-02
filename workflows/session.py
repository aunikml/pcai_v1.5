# workflows/session.py
import streamlit as st
import json
from datetime import datetime
from database import (
    get_clients_for_pc, get_completed_supervision_count,
    add_supervision_session, get_supervision_sessions_for_client
)
from gemini_utils import (
    assess_emotional_readiness, compare_mood_scores,
    explain_from_knowledge_base, discuss_coping_strategies,
    get_supervision_analysis, get_exploration_guidelines, get_empowerment_guidelines,
    provide_supervision_guidance_s2
)
from constants import INITIAL_CLIENT_QUESTIONS, SRQ_QUESTIONS

# --- WORKFLOW 1 (PART 2): MAIN MENU & CLIENT SELECTION ---
def run_main_menu_workflow():
    stage = st.session_state.get("conversation_stage", "well_being_check")
    
    if stage == 'well_being_check' and "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": f"স্বাগতম, {st.session_state.full_name}। আপনি কেমন আছেন?"}]

    if stage in ['well_being_check', 'main_menu']:
        for msg in st.session_state.get("messages", []):
            with st.chat_message(msg['role']): st.markdown(msg['content'])

    if stage == "main_menu":
        with st.chat_message("assistant"):
            st.markdown("এখন আপনি কী করতে চান তা নির্বাচন করুন:")
            c1, c2 = st.columns(2)
            if c1.button("➕ নতুন ক্লায়েন্ট যোগ করুন", use_container_width=True):
                st.session_state.conversation_stage = "adding_client_info"
                st.session_state.new_client_data, st.session_state.info_question_index = {}, 0
                st.session_state.messages = [{"role": "assistant", "content": INITIAL_CLIENT_QUESTIONS[0]['prompt']}]
                st.rerun()
            if c2.button("💬 সুপারভিশন সেশন করুন", use_container_width=True):
                st.session_state.conversation_stage = "select_client_for_session"
                st.session_state.messages = []
                st.rerun()
    
    if prompt := st.chat_input("..."):
        if stage == "well_being_check":
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("..."): _, bot_response = assess_emotional_readiness(prompt)
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            st.session_state.conversation_stage = "main_menu"
            st.rerun()

# --- WORKFLOW 3: SUPERVISION SESSION ---
def run_session_workflow():
    stage = st.session_state.conversation_stage

    if stage == "select_client_for_session":
        st.header("সুপারভিশন সেশন")
        clients = get_clients_for_pc(st.session_state.user_id)
        eligible_clients = [c for c in clients if c['supervisor_referral'] != 'Yes']
        if not eligible_clients:
            st.warning("সেশন শুরু করার জন্য কোনো উপযুক্ত ক্লায়েন্ট নেই।")
        else:
            st.write("একজন ক্লায়েন্ট নির্বাচন করুন:")
            for client in eligible_clients:
                with st.container(border=True):
                    session_count = get_completed_supervision_count(client['id'], st.session_state.user_id)
                    st.subheader(client['name'])
                    st.caption(f"Date of Adding: {client['next_followup_date']}")
                    sc1, sc2 = st.columns(2)
                    mood_rating = client['mood_rating_initial'] if 'mood_rating_initial' in client.keys() else "N/A"
                    srq_score = client['srq_score'] if 'srq_score' in client.keys() else "N/A"
                    sc1.metric("Initial Mood", f"{mood_rating}/10")
                    sc2.metric("Initial SRQ", srq_score)
                    st.write("---")
                    st.write("**AI Supervision Session**")
                    s1_col, s2_col, s3_col, s4_col = st.columns(4)

                    def start_session(session_number):
                        st.session_state.session_client = dict(client)
                        st.session_state.session_data = {'client_id': client['id'], 'pc_id': st.session_state.user_id, 'session_number': session_number}
                        
                        if session_number == 3:
                            st.session_state.conversation_stage = 'session_3_start_prompt'
                            st.session_state.messages = []
                        else:
                            st.session_state.conversation_stage = 'session_pc_wellbeing_chat'
                            st.session_state.messages = [{"role": "assistant", "content": "সেশন শুরু করার আগে, অনুগ্রহ করে বলুন আপনি কেমন আছেন? আপনি প্রস্তুত হলে 'start session' বা 'শুরু করুন' টাইপ করুন।"}]
                        st.rerun()

                    with s1_col:
                        if st.button("Session 1", key=f"s1_{client['id']}", disabled=(session_count != 0), use_container_width=True): start_session(1)
                    with s2_col:
                        if st.button("Session 2", key=f"s2_{client['id']}", disabled=(session_count != 1), use_container_width=True): start_session(2)
                    with s3_col:
                        if st.button("Session 3", key=f"s3_{client['id']}", disabled=(session_count != 2), use_container_width=True): start_session(3)
                    with s4_col:
                        if st.button("Session 4", key=f"s4_{client['id']}", disabled=(session_count != 3), use_container_width=True): start_session(4)
        
        if st.button("Back to Main Menu"):
            st.session_state.conversation_stage = "main_menu"
            st.session_state.messages = []
            st.rerun()
        return

    client = st.session_state.session_client
    session_num = st.session_state.session_data['session_number']
    st.info(f"**Client:** {client['name']} | **Supervision Session #:** {session_num}")
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg['role']): st.markdown(msg['content'])

    is_chat_disabled = not stage.endswith(('_text', '_chat', '_wait'))

    if stage.endswith('_get_date'):
        with st.chat_message("assistant", avatar="🤖"):
            st.write("অনুগ্রহ করে আজকের সুপারভিশন সেশনের তারিখ নির্বাচন করুন।")
            st.date_input("Supervision Date", value=datetime.now(), key="session_date_picker", format="YYYY-MM-DD")
            if st.button("Confirm Date", use_container_width=True):
                date_str = st.session_state.session_date_picker.strftime('%Y-%m-%d')
                st.session_state.session_data['session_date'] = date_str
                st.session_state.messages.append({"role": "user", "content": f"Date set to: {date_str}"})
                if session_num == 1:
                    st.session_state.conversation_stage = 'session_1_case_management_text'
                    st.session_state.messages.append({"role": "assistant", "content": "ধন্যবাদ। অনুগ্রহ করে ব্যাখ্যা করুন আপনি এখন পর্যন্ত কেসটি কীভাবে পরিচালনা করেছেন।"})
                elif session_num == 2:
                    st.session_state.conversation_stage = 'session_2_sessions_taken_text'
                    st.session_state.messages.append({"role": "assistant", "content": "আপনি ক্লায়েন্টের সাথে এ পর্যন্ত কয়টি সেশন করেছেন?"})
                st.rerun()
    elif stage == 'session_2_mood_rating':
        with st.chat_message("assistant", avatar="🤖"):
            st.write("👉 ক্লায়েন্টের বর্তমান মুড রেটিং ইনপুট করুন (১=সবচেয়ে খারাপ, ১০=সবচেয়ে ভালো)।")
            st.slider("Current Mood Rating", 1, 10, 5, key="session_2_mood_slider")
            if st.button("Confirm Mood", use_container_width=True):
                st.session_state.session_data['client_current_mood'] = st.session_state.session_2_mood_slider
                st.session_state.messages.append({"role": "user", "content": f"Current mood set to: {st.session_state.session_2_mood_slider}"})
                st.session_state.conversation_stage = 'session_2_mood_comparison'
                st.rerun()
    elif stage == 'session_2_mood_comparison':
        with st.chat_message("assistant"):
            with st.spinner("Analyzing mood..."):
                previous_sessions = get_supervision_sessions_for_client(client['id'])
                previous_mood = client.get('mood_rating_initial')
                if previous_sessions:
                    last_completed_session = previous_sessions[-1]
                    if 'client_current_mood' in last_completed_session.keys() and last_completed_session['client_current_mood'] is not None:
                         previous_mood = last_completed_session['client_current_mood']
                current_mood = st.session_state.session_data['client_current_mood']
                remark = compare_mood_scores(previous_mood, current_mood)
                st.markdown(remark)
                st.session_state.messages.append({"role": "assistant", "content": remark})
        st.session_state.conversation_stage = 'session_2_case_management_update_text'
        st.session_state.messages.append({"role": "assistant", "content": "কেস ম্যানেজমেন্ট প্রক্রিয়ার আপডেট সম্পর্কে বলুন।"})
        st.rerun()
    elif stage == 'session_3_start_prompt':
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown("""
            ### Session 3: Psychoeducation and Formulation
            এই সেশনে আপনাকে স্বাগত জানাই। আশা করি আপনি শারীরিক ও মানসিকভাবে সুস্থ আছেন। 
            এই সেশনে আমরা কেস ফর্মুলেশনের একটি গুরুত্বপূর্ণ অংশ **(PPPPP Formulation)** এবং ক্লায়েন্টের সমস্যা মোকাবিলার কৌশল নিয়ে আলোচনা করব। এটি আপনার দক্ষতাকে আরও বৃদ্ধি করতে সাহায্য করবে। 
            *যদি আপনি কোনো কারণে মানসিক চাপে থাকেন, তবে সেশনের পর আপনার সুপারভাইজারের সাথে কথা বলার জন্য অনুরোধ করা হচ্ছে।*
            """)
            if st.button("Start Session 3", use_container_width=True, type="primary"):
                st.session_state.conversation_stage = 'session_3_intro'
                st.rerun()
    elif stage == 'session_3_intro' or stage == 'session_3_ppppp_explanation' or stage == 'session_3_coping_strategies' or stage == 'session_3_craft_formulation':
        with st.chat_message("assistant"):
            with st.spinner("AI is preparing the materials..."):
                if stage == 'session_3_intro':
                    intro_msg = "আপনি অসাধারণ কাজ করছেন। এই সেশনে আমরা কিছু গুরুত্বপূর্ণ প্রক্রিয়া শিখব। অনুগ্রহ করে মনোযোগী হন।"
                    st.markdown(intro_msg)
                    if not any(msg['content'] == intro_msg for msg in st.session_state.messages):
                        st.session_state.messages.append({"role": "assistant", "content": intro_msg})
                    st.session_state.conversation_stage = 'session_3_ppppp_explanation'
                    st.rerun()
                elif stage == 'session_3_ppppp_explanation':
                    topic = "PPPPP Formulation"; instruction = "উপস্থাপনকারী সমস্যা (Presenting Problem), পূর্বনির্ধারক কারণ (Predisposing Factors), précipitating কারণ (Precipitating Factors), স্থায়ী কারণ (Perpetuating factor), এবং প্রতিরক্ষামূলক কারণ (Protective Factors)"
                    explanation = explain_from_knowledge_base(topic, instruction)
                    st.markdown(explanation); st.session_state.messages.append({"role": "assistant", "content": explanation})
                    st.session_state.conversation_stage = 'session_3_coping_strategies'; st.rerun()
                elif stage == 'session_3_coping_strategies':
                    st.markdown("চমৎকার। এখন ক্লায়েন্টের দৈনন্দিন মানসিক চাপ, রাগ নিয়ন্ত্রণ এবং অন্যান্য মানসিক সমস্যা মোকাবেলার কৌশল নিয়ে আলোচনা করা যাক।")
                    if st.button("কৌশলগুলো নিয়ে আলোচনা করুন"):
                        with st.spinner("AI কৌশলগুলো প্রস্তুত করছে..."):
                            strategies = discuss_coping_strategies()
                            st.markdown(strategies)
                            st.session_state.messages.append({"role": "assistant", "content": strategies})
                        st.session_state.conversation_stage = 'session_3_craft_formulation'; st.rerun()
                elif stage == 'session_3_craft_formulation':
                    final_instruction = "ধন্যবাদ। এখন, এই কেসের জন্য PPPPP ফর্মুলেশন এবং মোকাবিলা করার কৌশলগুলি তৈরি করে আপনার সুপারভাইজারের সাথে আলোচনা করার জন্য অনুরোধ করা হচ্ছে।"
                    st.markdown(final_instruction); st.session_state.messages.append({"role": "assistant", "content": final_instruction})
                    st.session_state.conversation_stage = 'session_3_followups_had_text'
                    st.session_state.messages.append({"role": "assistant", "content": "আপনি এ পর্যন্ত ক্লায়েন্টের সাথে কতগুলি ফলো-আপ করেছেন?"}); st.rerun()
    elif stage == 'session_show_analysis' or stage == 'session_show_exploration' or stage == 'session_end':
        with st.chat_message("assistant"):
            if stage == 'session_show_analysis':
                if st.button("Show Client Exploration Guidelines"):
                    with st.spinner("AI is generating exploration guidelines..."):
                        guidance = get_exploration_guidelines(st.session_state.session_data['full_context_for_guidance'])
                        st.markdown(guidance); st.session_state.messages.append({"role": "assistant", "content": guidance})
                        st.session_state.session_data['ai_supervision_guidance'] += f"\n\n{guidance}"
                    st.session_state.conversation_stage = 'session_show_exploration'; st.rerun()
            elif stage == 'session_show_exploration':
                if st.button("Show Empowerment Guidelines"):
                    with st.spinner("AI is generating empowerment guidelines..."):
                        guidance = get_empowerment_guidelines(st.session_state.session_data['full_context_for_guidance'])
                        st.markdown(guidance); st.session_state.messages.append({"role": "assistant", "content": guidance})
                        st.session_state.session_data['ai_supervision_guidance'] += f"\n\n{guidance}"
                    st.session_state.conversation_stage = 'session_end'; st.rerun()
            elif stage == 'session_end':
                if st.button("Finish and Save Session", type="primary", use_container_width=True):
                    st.session_state.session_data['pc_id'] = st.session_state.user_id
                    add_supervision_session(st.session_state.session_data)
                    st.success("Supervision session saved successfully!")
                    for key in list(st.session_state.keys()):
                        if key.startswith('session_'): del st.session_state[key]
                    st.session_state.conversation_stage = 'main_menu'
                    st.session_state.messages = [{"role": "assistant", "content": "সেশনটি সফলভাবে সংরক্ষণ করা হয়েছে।"}]; st.rerun()

    if prompt := st.chat_input("...", disabled=is_chat_disabled):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        if stage == 'session_pc_wellbeing_chat':
            with st.spinner("..."): _, bot_response = assess_emotional_readiness(prompt)
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            st.session_state.conversation_stage = 'session_pc_wellbeing_chat_wait'; st.rerun()
        elif stage == 'session_pc_wellbeing_chat_wait':
            if "start" in prompt.lower() or "শুরু" in prompt:
                if session_num < 3:
                    st.session_state.conversation_stage = f'session_{session_num}_get_date'
                else:
                    st.session_state.conversation_stage = 'session_3_intro'
                st.session_state.messages.append({"role": "assistant", "content": "চলুন সেশন শুরু করা যাক."})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "আপনার কথা শোনার জন্য আমি এখানে আছি। আপনি যখন প্রস্তুত হবেন, তখন 'সেশন শুরু করুন' টাইপ করুন."})
            st.rerun()
        elif stage == 'session_1_case_management_text':
            st.session_state.session_data['case_management_notes'] = prompt
            st.session_state.conversation_stage = 'session_1_challenges_text'
            st.session_state.messages.append({"role": "assistant", "content": "ধন্যবাদ। সেশনের সময় আপনি কী কী নির্দিষ্ট চ্যালেঞ্জের মুখোমুখি হয়েছেন?"}); st.rerun()
        elif stage == 'session_1_challenges_text':
            st.session_state.session_data['challenges_faced'] = prompt
            st.session_state.conversation_stage = 'session_1_stuck_points_text'
            st.session_state.messages.append({"role": "assistant", "content": "কোথায় আপনি আটকে গেছেন বা পরবর্তী পদক্ষেপ সম্পর্কে অনিশ্চিত বোধ করছেন?"}); st.rerun()
        elif stage == 'session_1_stuck_points_text':
            st.session_state.session_data['stuck_points'] = prompt
            st.session_state.conversation_stage = 'session_1_case_questions_text'
            st.session_state.messages.append({"role": "assistant", "content": "এই কেস সম্পর্কে আপনার নির্দিষ্ট প্রশ্ন কী কী?"}); st.rerun()
        elif stage == 'session_1_case_questions_text':
            st.session_state.session_data['case_questions'] = prompt
            st.session_state.conversation_stage = 'session_1_personal_barriers_text'
            st.session_state.messages.append({"role": "assistant", "content": "এই কেসটি পরিচালনা করার সময় কোনো ব্যক্তিগত বাধা বা মানসিক প্রতিক্রিয়া কি আপনার কাজকে প্রভাবিত করছে?"}); st.rerun()
        elif stage == 'session_1_personal_barriers_text':
            st.session_state.session_data['personal_barriers'] = prompt
            with st.chat_message("assistant"):
                with st.spinner("AI আপনার উত্তর বিশ্লেষণ করে পর্যবেক্ষণ তৈরি করছে..."):
                    supervision_notes = {k: v for k, v in st.session_state.session_data.items() if k.endswith(('_notes', '_faced', '_points', '_questions', '_barriers'))}
                    analysis_guidance = get_supervision_analysis(st.session_state.session_client, supervision_notes)
                    st.session_state.session_data['full_context_for_guidance'] = f"Client: {st.session_state.session_client}\nNotes: {supervision_notes}\nInitial Analysis: {analysis_guidance}"
                    st.session_state.session_data['ai_supervision_guidance'] = analysis_guidance
                    st.markdown(analysis_guidance)
                    st.session_state.messages.append({"role": "assistant", "content": analysis_guidance})
            st.session_state.conversation_stage = 'session_show_analysis'; st.rerun()
        elif stage == 'session_2_sessions_taken_text':
            st.session_state.session_data['sessions_taken_by_pc'] = prompt
            st.session_state.conversation_stage = 'session_2_mood_rating'; st.rerun()
        elif stage == 'session_2_case_management_update_text':
            st.session_state.session_data['case_management_notes'] = prompt
            st.session_state.conversation_stage = 'session_2_challenges_text'
            st.session_state.messages.append({"role": "assistant", "content": "নতুন কোনো চ্যালেঞ্জের মুখোমুখি হয়েছেন?"}); st.rerun()
        elif stage == 'session_2_challenges_text':
            st.session_state.session_data['challenges_faced'] = prompt
            st.session_state.conversation_stage = 'session_2_stuck_points_text'
            st.session_state.messages.append({"role": "assistant", "content": "নতুন কোনো বিষয়ে আটকে গেছেন?"}); st.rerun()
        elif stage == 'session_2_stuck_points_text':
            st.session_state.session_data['stuck_points'] = prompt
            st.session_state.conversation_stage = 'session_2_feelings_text'
            st.session_state.messages.append({"role": "assistant", "content": "এই কেস সম্পর্কে আপনার অনুভূতি কী?"}); st.rerun()
        elif stage == 'session_2_feelings_text':
            st.session_state.session_data['case_questions'] = prompt
            st.session_state.conversation_stage = 'session_2_personal_barriers_text'
            st.session_state.messages.append({"role": "assistant", "content": "আর কোনো ব্যক্তিগত বাধা কি কাজকে প্রভাবিত করছে?"}); st.rerun()
        elif stage == 'session_2_personal_barriers_text':
            st.session_state.session_data['personal_barriers'] = prompt
            with st.chat_message("assistant"):
                with st.spinner("AI আপনার উত্তর বিশ্লেষণ করে সুপারভিশন নির্দেশিকা তৈরি করছে..."):
                    session1_data = get_supervision_sessions_for_client(client['id'])[0]
                    session2_notes = {k: v for k, v in st.session_state.session_data.items() if k.endswith(('_notes', '_faced', '_points', '_questions', '_barriers', '_taken', '_mood'))}
                    guidance = provide_supervision_guidance_s2(st.session_state.session_client, dict(session1_data), session2_notes)
                    st.session_state.session_data['ai_supervision_guidance'] = guidance
                    st.markdown(guidance)
                    st.session_state.messages.append({"role": "assistant", "content": guidance})
            st.session_state.session_data['pc_id'] = st.session_state.user_id
            add_supervision_session(st.session_state.session_data)
            st.success("Supervision session saved successfully!")
            st.session_state.messages.append({"role": "assistant", "content": "সেশনটি সফলভাবে সংরক্ষণ করা হয়েছে।"}); 
            for key in list(st.session_state.keys()):
                if key.startswith('session_'): del st.session_state[key]
            st.session_state.conversation_stage = 'main_menu'; st.rerun()
        elif stage == 'session_3_followups_had_text':
            st.session_state.session_data['sessions_taken_by_pc'] = prompt
            st.session_state.conversation_stage = 'session_3_latest_mood_text'
            st.session_state.messages.append({"role": "assistant", "content": "ক্লায়েন্টের সর্বশেষ মুড প্রোটোকল স্কোর কত ছিল?"}); st.rerun()
        elif stage == 'session_3_latest_mood_text':
            st.session_state.session_data['client_current_mood'] = prompt
            with st.chat_message("assistant"):
                with st.spinner("Analyzing progress..."):
                    previous_sessions = get_supervision_sessions_for_client(client['id'])
                    previous_mood = previous_sessions[-1]['client_current_mood'] if previous_sessions and 'client_current_mood' in previous_sessions[-1].keys() else client.get('mood_rating_initial')
                    remark = compare_mood_scores(previous_mood, prompt)
                    st.markdown(remark)
                    st.session_state.messages.append({"role": "assistant", "content": remark})
            st.session_state.session_data['pc_id'] = st.session_state.user_id
            add_supervision_session(st.session_state.session_data)
            st.success("Supervision session saved successfully!")
            st.session_state.messages.append({"role": "assistant", "content": "সেশনটি সফলভাবে সংরক্ষণ করা হয়েছে।"}); 
            for key in list(st.session_state.keys()):
                if key.startswith('session_'): del st.session_state[key]
            st.session_state.conversation_stage = 'main_menu'; st.rerun()