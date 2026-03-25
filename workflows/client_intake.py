# workflows/client_intake.py
import streamlit as st
import json
from database import add_client
from gemini_utils import (
    suggest_syndrome, generate_client_synopsis,
    decide_crisis_level, suggest_next_followup_date
)
from constants import INITIAL_CLIENT_QUESTIONS, SRQ_QUESTIONS

# ==============================================================================
# --- NEW HELPER FUNCTION ---
# ==============================================================================

def convert_bengali_to_english_numerals(text: str) -> str:
    """Converts a string containing Bengali numerals to English numerals."""
    if not isinstance(text, str):
        return str(text) # Ensure it's a string for processing
    
    bengali_to_english_map = {
        '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
        '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
    }
    translation_table = str.maketrans(bengali_to_english_map)
    return text.translate(translation_table).strip()

# ==============================================================================
# --- CLIENT INTAKE WORKFLOW ---
# ==============================================================================

def run_client_intake_workflow():
    """Manages the entire multi-stage process of adding a new client."""
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]): st.markdown(message["content"])

    stage = st.session_state.conversation_stage
    is_chat_disabled = stage not in ["adding_client_info", "adding_client_note_text"]

    if stage == "adding_client_gender" or stage == "adding_client_marital_status":
        q_index = st.session_state.info_question_index
        question = INITIAL_CLIENT_QUESTIONS[q_index]
        with st.chat_message("assistant", avatar="🤖"):
            cols = st.columns(len(question['options']))
            for i, option in enumerate(question['options']):
                if cols[i].button(option, key=f"option_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": option})
                    st.session_state.new_client_data[question['key']] = option
                    st.session_state.info_question_index += 1
                    advance_to_next_question()

    elif stage == "adding_client_mood":
        with st.chat_message("assistant", avatar="🤖"):
            st.slider("Mood Rating (1=Worst, 10=Best)", 1, 10, 5, key="mood_slider")
            if st.button("Confirm Mood Rating", use_container_width=True):
                st.session_state.new_client_data['mood_rating_initial'] = st.session_state.mood_slider
                st.session_state.messages.append({"role": "user", "content": f"Mood rating set to: {st.session_state.mood_slider}"})
                st.session_state.messages.append({"role": "assistant", "content": "মুড রেটিং রেকর্ড করা হয়েছে। এখন SRQ প্রশ্ন শুরু করা যাক।"})
                st.session_state.conversation_stage = "adding_client_srq"
                st.session_state.srq_question_index, st.session_state.srq_answers = 0, []
                st.rerun()

    elif stage == "adding_client_srq":
        q_index = st.session_state.get('srq_question_index', 0)
        with st.chat_message("assistant"): st.write(SRQ_QUESTIONS[q_index])
        col1, col2 = st.columns(2)
        if col1.button("✔️ হ্যাঁ", key=f"yes_{q_index}", use_container_width=True):
            st.session_state.srq_answers.append(1); st.session_state.srq_question_index += 1
            if st.session_state.srq_question_index >= len(SRQ_QUESTIONS): st.session_state.conversation_stage = "adding_client_note_prompt"; st.rerun()
            else: st.rerun()
        if col2.button("❌ না", key=f"no_{q_index}", use_container_width=True):
            st.session_state.srq_answers.append(0); st.session_state.srq_question_index += 1
            if st.session_state.srq_question_index >= len(SRQ_QUESTIONS): st.session_state.conversation_stage = "adding_client_note_prompt"; st.rerun()
            else: st.rerun()
        
    elif stage == "adding_client_note_prompt":
        with st.chat_message("assistant"):
            st.write("আপনি কি ক্লায়েন্ট সম্পর্কে কোনো অতিরিক্ত নোট যোগ করতে চান?")
            c1, c2 = st.columns(2)
            if c1.button("✔️ হ্যাঁ, নোট যোগ করুন", use_container_width=True):
                st.session_state.conversation_stage = "adding_client_note_text"
                st.session_state.messages.append({"role": "assistant", "content": "অনুগ্রহ করে আপনার নোটটি এখানে টাইপ করুন।"})
                st.rerun()
            if c2.button("❌ না, বাদ দিন", use_container_width=True):
                process_and_save_client()

    if prompt := st.chat_input("আপনার উত্তর দিন...", disabled=is_chat_disabled):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        if stage == "adding_client_info":
            q_index = st.session_state.info_question_index
            st.session_state.new_client_data[INITIAL_CLIENT_QUESTIONS[q_index]['key']] = prompt
            st.session_state.info_question_index += 1
            advance_to_next_question()
        elif stage == "adding_client_note_text":
            st.session_state.new_client_data['pc_note'] = prompt
            process_and_save_client()
        st.rerun()

def advance_to_next_question():
    """Determines the next step in the client intake conversational flow."""
    q_index = st.session_state.info_question_index
    if q_index < len(INITIAL_CLIENT_QUESTIONS):
        next_q = INITIAL_CLIENT_QUESTIONS[q_index]
        st.session_state.messages.append({"role": "assistant", "content": next_q['prompt']})
        if next_q['type'] == 'text': st.session_state.conversation_stage = "adding_client_info"
        elif next_q['type'] == 'options': st.session_state.conversation_stage = f"adding_client_{next_q['id']}"
    else:
        st.session_state.conversation_stage = "adding_client_mood"
        st.session_state.messages.append({"role": "assistant", "content": "ধন্যবাদ। এখন ক্লায়েন্টের মুড রেটিং করার জন্য প্রস্তুত। অনুগ্রহ করে নিচের প্রশ্নটি ক্লায়েন্টকে জিজ্ঞাসা করুন এবং স্লাইডারটি ব্যবহার করুন:"})
    st.rerun()

def process_and_save_client():
    """
    Finalizes the client intake process by calculating scores,
    calling AI models, displaying a summary, and saving to the database.
    """
    with st.spinner("Analyzing responses and creating profile..."):
        # --- DATA SANITIZATION & VALIDATION (THE FIX) ---
        try:
            # Get the age from session state, which could be in Bengali
            age_str = st.session_state.new_client_data.get('age', '')
            # Convert any Bengali numerals to English numerals
            english_age_str = convert_bengali_to_english_numerals(age_str)
            # Convert the sanitized string to an integer
            # If the string is empty, it becomes None, which is database-friendly (NULL)
            st.session_state.new_client_data['age'] = int(english_age_str) if english_age_str else None
        except (ValueError, TypeError):
            # If conversion fails (e.g., user entered "abc"), show an error and stop.
            st.error(f"'{age_str}' একটি সঠিক বয়স নয়। অনুগ্রহ করে শুধুমাত্র সংখ্যা ব্যবহার করুন।")
            st.stop()
        
        # --- 1. Calculations ---
        srq_responses = st.session_state.srq_answers
        score_1_20 = sum(srq_responses[:20])
        yes_1_20, no_1_20 = score_1_20, 20 - score_1_20
        psych_risk_qs = [SRQ_QUESTIONS[i] for i in range(20, 24) if srq_responses[i] == 1]
        acceptance = "Eligible for psychosocial support" if score_1_20 >= 7 else "Not eligible"
        suicide_risk = (srq_responses[14] == 1)
        referral = "Yes" if suicide_risk or psych_risk_qs else "No"
        mood = st.session_state.new_client_data['mood_rating_initial']
        pc_note = st.session_state.new_client_data.get('pc_note', 'No note was added by the Para-counselor.')
        
        # --- 2. AI Calls ---
        context_for_ai = (f"Client Info: {st.session_state.new_client_data}\n" f"Initial Mood Rating: {mood}/10\n" f"SRQ Score (1-20): {score_1_20}\n" f"Suicide Risk Detected: {'Yes' if suicide_risk else 'No'}\n" f"Severe Psychiatric Indicators: {len(psych_risk_qs)} found.\n" f"Para-counselor's Note: {pc_note}")
        ai_synopsis_for_pc = generate_client_synopsis(context_for_ai)
        ai_crisis_decision = decide_crisis_level(context_for_ai)
        ai_syndrome_for_report = suggest_syndrome(context_for_ai)
        next_followup = suggest_next_followup_date(context_for_ai)
        
        # --- 3. Display Summary to PC ---
        summary_msg = f"#### প্রাথমিক মূল্যায়ন সারসংক্ষেপ:\n\n**১. AI জেনারেটেড সিনোপসিস:**\n> {ai_synopsis_for_pc}\n\n**২. SRQ (প্রশ্ন ১-২০) ফলাফল:**\n- **মোট 'হ্যাঁ' উত্তর:** {yes_1_20}\n- **মোট 'না' উত্তর:** {no_1_20}\n\n**৩. গুরুতর মানসিক স্বাস্থ্য নির্দেশক (প্রশ্ন ২১-২৪):**\n- **মোট 'হ্যাঁ' উত্তর:** {len(psych_risk_qs)}"
        if psych_risk_qs: summary_msg += "\n" + "\n".join([f"  - *{q}*" for q in psych_risk_qs])
        summary_msg += f"\n\n**৪. SRQ স্কোর (১-২০):** {score_1_20}\n**৫. মুড রেটিং প্রোটোকল স্কোর:** {mood}/10"
        st.session_state.messages.append({"role": "assistant", "content": summary_msg})
        
        # --- 4. Prepare and Save to DB ---
        final_data = {
            **st.session_state.new_client_data,
            'pc_note': pc_note, 
            'srq_score': score_1_20, 
            'client_acceptance_status': acceptance, 
            'supervisor_referral': referral, 
            'srq_responses': json.dumps(srq_responses), 
            'ai_proposed_syndrome': ai_syndrome_for_report, 
            'ai_crisis_level_decision': ai_crisis_decision, 
            'created_by_pc_id': st.session_state.user_id, 
            'next_followup_date': next_followup
        }
        add_client(final_data)
        
        # --- 5. Final Confirmation & Transition ---
        confirmation = "ধন্যবাদ। ক্লায়েন্টের প্রোফাইল তৈরি করা হয়েছে।"
        if referral == "Yes": confirmation += "\n\n**গুরুত্বপূর্ণ:** SRQ প্রতিক্রিয়া অনুযায়ী সুপারভাইজারের কাছে অবিলম্বে রেফারেল প্রয়োজন।"
        st.session_state.messages.append({"role": "assistant", "content": confirmation})
        st.session_state.conversation_stage = "main_menu"
        st.rerun()