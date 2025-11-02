# gemini_utils.py
import os
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timedelta
from database import get_knowledge_for_bots

# Load environment variables from the .env file
load_dotenv()

# Configure the Gemini API with the key from the environment
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Error configuring Gemini API: {e}. Please check your .env file and API key.")

# ==============================================================================
# --- MODEL INITIALIZATION ---
# ==============================================================================
pc_assistant_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-lite",
    system_instruction="You are a helpful and empathetic AI assistant for Para-counselors in Bangladesh. All your responses must be in professional and clear Bengali."
)
data_analyst_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-lite",
    system_instruction="You are a helpful data analyst assistant for a mental health program manager. Base your answers STRICTLY on the data provided. Provide your answers in clear, professional Bengali."
)

# ==============================================================================
# --- KNOWLEDGE BASE HELPER ---
# ==============================================================================
def _get_knowledge_context(bot_names: list):
    knowledge_entries = get_knowledge_for_bots(bot_names)
    if not knowledge_entries: return ""
    context_str = "\n\n--- ADMINISTRATIVE KNOWLEDGE BASE ---\n"
    context_str += "You MUST strictly follow these instructions when generating your response. They override any previous general instructions.\n"
    for entry in knowledge_entries:
        context_str += f"\n**Instruction (Title: {entry['title']}, Importance: {entry['importance_score']}/10):**\n{entry['instruction_text']}\n"
        if entry['document_content']:
            context_str += f"\n**Reference Document Content (Summary):**\n---\n{entry['document_content'][:1500]}...\n---\n"
    context_str += "--- END OF KNOWLEDGE BASE ---\n"
    return context_str

# ==============================================================================
# --- KNOWLEDGE-AWARE AI FUNCTIONS ---
# ==============================================================================

def assess_emotional_readiness(pc_response: str):
    bot_name = "The Para-counselor (PC) Well-being Bot"
    knowledge_context = _get_knowledge_context([bot_name])
    prompt = f"""{knowledge_context}\nA Para-counselor was asked "আপনি কেমন আছেন?" and replied: "{pc_response}". Analyze their readiness and respond in JSON format with 'is_ready' (boolean) and 'bot_response_bengali'."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        text_response = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(text_response)
        return result["is_ready"], result["bot_response_bengali"]
    except Exception as e: print(f"Error in readiness assessment: {e}"); return True, "ধন্যবাদ। চলুন, পরবর্তী ধাপে যাওয়া যাক।"

def suggest_syndrome(client_info_text: str):
    bot_names = ["The Clinical Report Writer Bot", "The Risk Assessment Bot"]
    knowledge_context = _get_knowledge_context(bot_names)
    prompt = f"""{knowledge_context}\nBased on the following client data, provide a detailed clinical analysis with specific sections (Observations, Proposed Syndrome, Rationale, Considerations).\n**Client Data:**\n---\n{client_info_text}\n---"""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI analysis error for report: {e}"

def generate_client_synopsis(synopsis_data: str):
    bot_name = "The Client Intake Bot"
    knowledge_context = _get_knowledge_context([bot_name])
    prompt = f"""{knowledge_context}\nBased on the following data, write a concise, explanatory, one-paragraph clinical synopsis in Bengali for the Para-counselor.\n**Collected Data:**\n---\n{synopsis_data}\n---"""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Synopsis generation error: {e}"

def decide_crisis_level(context_data: str):
    bot_name = "The Risk Assessment Bot"
    knowledge_context = _get_knowledge_context([bot_name])
    prompt = f"""{knowledge_context}\nAssess the client's crisis level (Crisis Level, Moderate Concern, or Stable) based on the provided data. Provide your output as a single, concise statement in Bengali.\n**Provided Data:**\n---\n{context_data}\n---"""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e: return f"Crisis level decision error: {e}"

def suggest_next_followup_date(client_context: str):
    bot_name = "The Scheduling Assistant Bot"
    knowledge_context = _get_knowledge_context([bot_name])
    prompt = f"""{knowledge_context}\nBased on the client's risk profile, suggest a next follow-up date. Provide only the date in YYYY-MM-DD format. Today's date is {datetime.now().strftime('%Y-%m-%d')}.\n**Client's Data:**\n---\n{client_context}\n---"""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error suggesting followup date: {e}")
        return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

def get_admin_data_insights(admin_question: str, client_df: pd.DataFrame):
    bot_name = "The Admin Data Analyst Bot"
    knowledge_context = _get_knowledge_context([bot_name])
    client_data_csv = client_df.to_csv(index=False)
    prompt = f"""{knowledge_context}\nAn admin asked: "{admin_question}". Analyze the provided CSV data to answer it.\n**Client Dataset (CSV Format):**\n---\n{client_data_csv}\n---"""
    try:
        response = data_analyst_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"ডেটা বিশ্লেষণ করতে সমস্যা হচ্ছে: {e}"

# --- SUPERVISION SESSION FUNCTIONS ---

def get_supervision_analysis(client_data: dict, supervision_notes: dict):
    """Generates ONLY the Analysis and Observations part of the supervision."""
    client_context = json.dumps(client_data, indent=2, ensure_ascii=False)
    supervision_context = json.dumps(supervision_notes, indent=2, ensure_ascii=False)
    knowledge_context = _get_knowledge_context(["The Session Guide Bot", "The Clinical Report Writer Bot"])
    prompt = f"""You are a master-level AI Clinical Supervisor. Analyze the provided data. Your task is to generate ONLY the "Analysis and Observations" section in Bengali.\n{knowledge_context}\n**Client Assessment Data:**\n---\n{client_context}\n---\n**PC's Supervision Notes:**\n---\n{supervision_context}\n---\n**Your Task:**\n### ১. বিশ্লেষণ ও পর্যবেক্ষণ (Analysis and Observations)\n- Identify gaps in assessment.\n- Highlight connections between history, problems, and PC challenges.\n- Offer scientific hypotheses for client behavior."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI Analysis error: {e}"

def get_exploration_guidelines(full_context: str):
    """Generates ONLY the Client Exploration guidelines."""
    knowledge_context = _get_knowledge_context(["The Session Guide Bot"])
    prompt = f"""Based on the full context below, generate ONLY the "Guideline on Facilitating Client Exploration" section in Bengali.\n{knowledge_context}\n**Full Context:**\n---\n{full_context}\n---\n**Your Task:**\n### ২. ক্লায়েন্টের সাথে কথোপকথনের জন্য নির্দেশিকা (Guideline on Facilitating Client Exploration)\n- Provide 2-3 specific, open-ended questions.\n- Give examples of empathetic statements."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI Exploration guideline error: {e}"

def get_empowerment_guidelines(full_context: str):
    """Generates ONLY the Empowerment guidelines."""
    knowledge_context = _get_knowledge_context(["The Session Guide Bot"])
    prompt = f"""Based on the full context below, generate ONLY the "Guideline on Empowerment and Finding Solutions" section in Bengali.\n{knowledge_context}\n**Full Context:**\n---\n{full_context}\n---\n**Your Task:**\n### ৩. ক্ষমতায়ন এবং সমাধানের জন্য নির্দেশিকা (Guideline on Empowerment and Finding Solutions)\n- Guide the PC on helping the client find their own solutions.\n- Suggest techniques for self-reflection and empowerment."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI Empowerment guideline error: {e}"

def compare_mood_scores(previous_mood, current_mood):
    knowledge_context = _get_knowledge_context(["The Session Guide Bot"])
    prompt = f"""{knowledge_context}\nA client's mood score was {previous_mood}/10 in the previous session and is now {current_mood}/10. Write a short, one-sentence contextualized message in Bengali remarking on this change."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Mood comparison error: {e}"

def provide_supervision_guidance_s2(client_data: dict, session1_data: dict, session2_notes: dict):
    client_context = json.dumps(client_data, indent=2, ensure_ascii=False)
    s1_context = json.dumps(session1_data, indent=2, ensure_ascii=False)
    s2_context = json.dumps(session2_notes, indent=2, ensure_ascii=False)
    bot_names = ["The Session Guide Bot", "The Clinical Report Writer Bot"]
    knowledge_context = _get_knowledge_context(bot_names)
    prompt = f"""You are a master-level AI Clinical Supervisor. This is Supervision Session 2. Analyze all data, **referring back to Session 1 to highlight progress or new challenges.** Your response must follow the three-part structure in professional Bengali.\n{knowledge_context}\n**Client Assessment Data:**\n---\n{client_context}\n---\n**Supervision Session 1 Data:**\n---\n{s1_context}\n---\n**PC's Supervision Notes (Session 2):**\n---\n{s2_context}\n---\n**Your Task: Generate the updated Supervision Guidance Report for Session 2**"""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI Supervision guidance error for S2: {e}"

def explain_from_knowledge_base(topic_name: str, instruction: str):
    knowledge_context = _get_knowledge_context(["The Session Guide Bot"])
    prompt = f"""{knowledge_context}\nYou are an AI trainer for a Para-counselor. Your task is to explain a clinical concept. **Topic to Explain:** {topic_name}. **Core Instruction:** {instruction}. First, pull the definition of '{topic_name}' from the knowledge base. Then, explain its importance to the user in a simple, structured way. Finally, show a simple, clear sample. Provide the response in Bengali."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Knowledge explanation error: {e}"

def discuss_coping_strategies():
    knowledge_context = _get_knowledge_context(["The Session Guide Bot"])
    prompt = f"""{knowledge_context}\nYou are an AI trainer for a Para-counselor. Your task is to discuss strategies for common client issues. Discuss detailed strategies in Bengali for helping a client manage: Day-to-day stress, Anger regulation, and Other emotional difficulties."""
    try:
        response = pc_assistant_model.generate_content(prompt)
        return response.text
    except Exception as e: return f"Coping strategy discussion error: {e}"