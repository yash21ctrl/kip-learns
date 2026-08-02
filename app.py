import os

# Custom dotenv loader to load API key locally without Git security leaks
if os.path.exists(".env"):
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.strip() and not line.strip().startswith("#"):
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        os.environ[k.strip()] = v.strip()
    except Exception as e:
        print(f"Error loading .env: {e}")
import json
import time
import csv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS for all origins to allow index.html running locally or on another port to communicate
CORS(app)

QUESTIONS_FILE = 'questions.json'
LOGS_FILE = 'session_logs.json'
CSV_FILE = 'training_sessions.csv'

# In-memory single session state for test compatibility
session_state = {
    "asked_ids": [],
    "current_question_id": None,
    "start_time": None,
    "retry_counts": {}
}

# Multi-user session tracker
session_states = {}

def get_session_state(participant_id):
    if not participant_id:
        participant_id = "Unknown"
    if participant_id not in session_states:
        session_states[participant_id] = {
            "asked_ids": [],
            "current_question_id": None,
            "start_time": None,
            "retry_counts": {}
        }
    return session_states[participant_id]

# PostgreSQL Database Setup
DATABASE_URL = (
    os.environ.get("DATABASE_URL") or 
    os.environ.get("External_Database_URl") or 
    os.environ.get("External_Database_URL") or 
    os.environ.get("DATABASE URL")
)
use_postgres = False
db_initialized = False

import google.generativeai as genai
import random

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully.")
else:
    print("WARNING: GEMINI_API_KEY environment variable not set. Running in offline/mock mode.")

# Load pre-trained frustration classifier model
clf = None
MODEL_FILE = "frustration_model.joblib"
if os.path.exists(MODEL_FILE):
    try:
        import joblib
        clf = joblib.load(MODEL_FILE)
        print("Frustration classifier model loaded successfully.")
    except Exception as e:
        print(f"Error loading model from {MODEL_FILE}: {e}. Falling back to rule-based mock model.")
else:
    print(f"Model file {MODEL_FILE} not found. Running with rule-based mock model.")

# Reset Mission Pool
RESET_MISSIONS_POOL = [
    {
        "type": "silly_question",
        "prompt": "Kip wants to know: What is your absolute favorite snack right now? 🍕🍫"
    },
    {
        "type": "silly_question",
        "prompt": "If you could have any superhero power right now, what would it be? 🦸‍♂️✨"
    },
    {
        "type": "physical_reset",
        "prompt": "Kip says: Time for a stretch! Reach for the sky, touch your toes, and count to 5. 🤸‍♂️"
    },
    {
        "type": "physical_reset",
        "prompt": "Give Kip 3 quick jumping jacks to get your blood moving! 🤸‍♀️"
    },
    {
        "type": "imagination_prompt",
        "prompt": "Close your eyes for 3 seconds and imagine you are sitting on a warm beach. 🏖️"
    },
    {
        "type": "breathing_beat",
        "prompt": "Follow Kip's breathing bounce: breathe in... and breathe out... 🌬️"
    }
]

# Static Kip Narration Fallback Library
KIP_FALLBACK_REASONING = {
    "Low": [
        "You're doing great! Let's keep this momentum going.",
        "Awesome job on that question! You've got this.",
        "That was smooth! Kip is cheering you on."
    ],
    "Medium": [
        "Mistakes are just proof that you are trying and growing! Keep pushing.",
        "Take a deep breath. You're making progress with every attempt.",
        "Almost there! Try looking at it from a fresh angle."
    ],
    "High": [
        "Whew, that was a tough one! Let's pause, take a quick break, and try an easier one.",
        "Kip thinks we should shake things up with a reset before we try again. You're doing awesome!",
        "Don't worry about the mistakes—every challenge makes your brain stronger! Let's do a reset."
    ]
}

def predict_frustration_level(retry_count, time_taken, tab_switches, mouse_idle_time, typing_pauses, used_visual_toggle):
    """
    Layer 1: Frustration Prediction
    Pure Decision Tree classifier execution (frustration_model.joblib).
    Returns the raw prediction output from the machine learning model.
    """
    if clf is not None:
        try:
            used_vt = 1 if used_visual_toggle else 0
            features = [[retry_count, time_taken, tab_switches, mouse_idle_time, typing_pauses, used_vt]]
            pred = clf.predict(features)[0]
            mapping = {0: "Low", 1: "Medium", 2: "High"}
            return mapping.get(pred, "Low")
        except Exception as e:
            print(f"Error running model prediction: {e}. Using fallback prediction.")
            
    # Rule-based fallback if Decision Tree model is not loaded
    if retry_count >= 2 or tab_switches >= 2:
        return "High"
    elif retry_count == 1 or mouse_idle_time > 4.0:
        return "Medium"
    else:
        return "Low"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def call_openai_api(prompt, max_tokens=60, temp=0.5, timeout=1.5):
    """Call OpenAI API (gpt-4o-mini) using standard library."""
    if not OPENAI_API_KEY:
        return None
    try:
        import urllib.request
        url = 'https://api.openai.com/v1/chat/completions'
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temp
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}'
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        res = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(res.read().decode('utf-8'))
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"OpenAI API call notice: {e}")
        return None

def call_llm_with_fallback(prompt, max_tokens=60, temp=0.7, timeout=1.5):
    """Try OpenAI API first, then Gemini models dynamically."""
    if OPENAI_API_KEY:
        res = call_openai_api(prompt, max_tokens=max_tokens, temp=temp, timeout=timeout)
        if res:
            return res
            
    if GEMINI_API_KEY:
        models_to_try = ['gemini-2.0-flash', 'gemini-flash-latest', 'gemini-2.0-flash-lite', 'gemini-1.5-flash']
        for m in models_to_try:
            try:
                model = genai.GenerativeModel(m)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temp
                    ),
                    request_options={"timeout": timeout}
                )
                text = response.text.strip()
                if text:
                    return text
            except Exception:
                continue
    return None

def get_static_fallback_narration(frustration, sub_skill):
    """Fallback pre-written Kip messages matched to the student's sub-skill and frustration."""
    if frustration == "Low":
        return random.choice(KIP_FALLBACK_REASONING["Low"])
    elif frustration == "Medium":
        if "math" in str(sub_skill).lower() or "subtraction" in str(sub_skill).lower() or "fraction" in str(sub_skill).lower():
            return f"Math is all about practice, and taking your time is your superpower! Kip is proud of you."
        return random.choice(KIP_FALLBACK_REASONING["Medium"])
    else:
        return random.choice(KIP_FALLBACK_REASONING["High"])

def audit_and_narrate_with_llm(predicted_label, is_correct, retry_count, time_taken, tab_switches, mouse_idle_time, typing_pauses, used_visual_toggle, q_text="", q_diff="easy", q_type="mcq", off_tab_duration=0.0, sub_skill="general"):
    """
    Combined Layer 2 + Layer 3 Unified Single API Call.
    Enforces a strict 1.5-second timeout.
    If Gemini times out (> 1.5s) or fails, falls back INSTANTLY to pre-written offline fallback dictionary!
    """
    fallback_narration = get_static_fallback_narration(predicted_label, sub_skill)
    
    if not OPENAI_API_KEY and not GEMINI_API_KEY:
        return predicted_label, fallback_narration
        
    q_len = len(str(q_text))
    prompt = f"""
    You are Kip, the AI Cognitive Auditor & Mascot for an adaptive learning platform (CALM).
    Evaluate this student attempt and respond in JSON format ONLY.
    
    Layer 1 ML Prediction: {predicted_label}
    Question: {q_text} (Type: {q_type}, Difficulty: {q_diff}, Length: {q_len} chars)
    
    Student Telemetry:
    - Answer Status: {"CORRECT" if is_correct else "INCORRECT"}
    - Attempts: {retry_count}, Time Taken: {time_taken:.1f}s, Off-Tab Away: {off_tab_duration:.1f}s, Tab Switches: {tab_switches}, Mouse Idle: {mouse_idle_time:.1f}s, Typing Pauses: {typing_pauses}, Used Visual Scaffold: {used_visual_toggle}
    
    Auditing Rules:
    1. If CORRECT -> verified_frustration MUST be "Low".
    2. If Hard MCQ/Typing/Match with 0 tab switches -> verify as "Low" or "Medium" (deep thinking).
    3. If INCORRECT < 2.0s on Easy MCQ -> audit to "Medium" (Impulsive misclick).
    4. If 2+ failed retries or (idle > 15s AND off_tab_duration >= 15s) -> confirm "High".
    5. Otherwise -> keep Layer 1 ML prediction ({predicted_label}).
    
    Output JSON ONLY:
    {{"label": "Low|Medium|High", "narration": "One short, warm, empathetic sentence (under 18 words) in Kip's voice directly to the student."}}
    """
    res = call_llm_with_fallback(prompt, max_tokens=60, temp=0.5, timeout=1.5)
    if res:
        try:
            import re
            label_match = re.search(r'"label"\s*:\s*"(Low|Medium|High)"', res, re.IGNORECASE)
            narration_match = re.search(r'"narration"\s*:\s*"([^"]+)"', res)
            
            verified_label = label_match.group(1).capitalize() if label_match else predicted_label
            narration_text = narration_match.group(1).strip() if narration_match else fallback_narration
            
            return verified_label, narration_text
        except Exception:
            pass
            
    return predicted_label, fallback_narration

def init_db_if_needed():
    global db_initialized, use_postgres
    if db_initialized:
        return
    if DATABASE_URL:
        try:
            import psycopg2
            # Set a 3-second connection timeout to prevent hanging on startup
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS session_logs (
                        id SERIAL PRIMARY KEY,
                        participant_id TEXT,
                        device_type TEXT,
                        question_id INT,
                        answer_given TEXT,
                        tab_switches INT,
                        mouse_idle_time FLOAT,
                        typing_pauses INT,
                        backspaces INT,
                        used_visual_toggle BOOLEAN,
                        visual_level_used INT,
                        frustration_label TEXT,
                        correct BOOLEAN,
                        retry_count INT,
                        time_taken FLOAT,
                        sub_skill TEXT,
                        difficulty TEXT,
                        timestamp TEXT,
                        data_source TEXT DEFAULT 'real'
                    );
                """)
                conn.commit()
            conn.close()
            use_postgres = True
            print("Connected to PostgreSQL successfully.")
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}. Falling back to local JSON files.")
            use_postgres = False
    db_initialized = True

def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and "questions" in data:
                    return data["questions"]
                return data
        except Exception as e:
            print(f"Error reading {QUESTIONS_FILE}: {e}")
            return []
    return []

def load_logs():
    init_db_if_needed()
    if use_postgres:
        conn = None
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM session_logs ORDER BY id ASC")
                rows = cur.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error loading logs from PostgreSQL: {e}")
            return []
        finally:
            if conn:
                conn.close()
    else:
        if os.path.exists(LOGS_FILE):
            try:
                with open(LOGS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading {LOGS_FILE}: {e}")
                return []
        return []

def save_log_record(record):
    init_db_if_needed()
    if use_postgres:
        conn = None
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO session_logs (
                        participant_id, device_type, question_id, answer_given, 
                        tab_switches, mouse_idle_time, typing_pauses, backspaces, 
                        used_visual_toggle, visual_level_used, frustration_label, 
                        correct, retry_count, time_taken, sub_skill, difficulty, timestamp, data_source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    record["participant_id"], record["device_type"], record["question_id"], record["answer_given"],
                    record["tab_switches"], record["mouse_idle_time"], record["typing_pauses"], record["backspaces"],
                    record["used_visual_toggle"], record["visual_level_used"], record["frustration_label"],
                    record["correct"], record["retry_count"], record["time_taken"], record["sub_skill"],
                    record["difficulty"], record["timestamp"], record.get("data_source", "real")
                ))
                conn.commit()
        except Exception as e:
            print(f"Error saving log to PostgreSQL: {e}")
        finally:
            if conn:
                conn.close()
    else:
        logs = load_logs()
        logs.append(record)
        try:
            with open(LOGS_FILE, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Error writing to {LOGS_FILE}: {e}")

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/debug-db', methods=['GET'])
def debug_db():
    init_db_if_needed()
    keys = list(os.environ.keys())
    db_url_exists = DATABASE_URL is not None
    
    # Check connection test
    connection_test = "Not tested"
    if db_url_exists:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            conn.close()
            connection_test = "Success!"
        except Exception as e:
            connection_test = f"Failed: {e}"
            
    return jsonify({
        "use_postgres": use_postgres,
        "db_initialized": db_initialized,
        "db_url_exists": db_url_exists,
        "resolved_db_url_prefix": DATABASE_URL[:30] + "..." if DATABASE_URL else None,
        "connection_test": connection_test,
        "env_keys": keys
    })

@app.route('/get-next-question', methods=['GET'])
def get_next_question():
    participant_id = request.args.get('participant_id', 'Unknown')
    session = get_session_state(participant_id)
    
    questions = load_questions()
    asked_set = set(session["asked_ids"])
    
    # 1. Fetch latest log record for this user to check if they struggled
    latest_record = None
    if use_postgres:
        conn = None
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM session_logs 
                    WHERE participant_id = %s 
                    ORDER BY id DESC LIMIT 1
                """, (participant_id,))
                row = cur.fetchone()
                if row:
                    latest_record = dict(row)
        except Exception as e:
            print(f"Error fetching latest log for routing: {e}")
        finally:
            if conn:
                conn.close()
    else:
        # JSON fallback
        logs = load_logs()
        p_logs = [l for l in logs if l.get("participant_id") == participant_id]
        if p_logs:
            latest_record = p_logs[-1]
            
    # 2. Adaptive Routing: if frustration was High, scale down difficulty on same sub_skill
    next_q = None
    if latest_record and latest_record.get("frustration_label") == "High":
        failed_q_id = latest_record.get("question_id")
        failed_q = next((q for q in questions if str(q["id"]) == str(failed_q_id)), None)
        if failed_q:
            sub_skill = failed_q.get("sub_skill") or failed_q.get("sub_topic")
            if failed_q.get("difficulty") == "hard":
                difficulty_preference = ["medium", "easy"]
            else:
                difficulty_preference = ["easy"]
                
            for diff in difficulty_preference:
                for q in questions:
                    q_sub_skill = q.get("sub_skill") or q.get("sub_topic")
                    if q["id"] not in asked_set and q_sub_skill == sub_skill and q.get("difficulty") == diff:
                        next_q = q
                        break
                if next_q:
                    break
                    
    # 3. Fallback: Find the next unasked question in the standard sequence
    if not next_q:
        for q in questions:
            if q["id"] not in asked_set:
                next_q = q
                break
            
    if not next_q:
        return jsonify({
            "finished": True,
            "message": "All questions have been answered! Use /reset-session to start over."
        })
        
    # Start timer and track this question
    session["asked_ids"].append(next_q["id"])
    session["current_question_id"] = next_q["id"]
    session["start_time"] = time.time()
    
    # Sync compatibility for unit tests
    session_state.clear()
    session_state.update(session)
    
    # Return question details without the correct answer field
    # Support both sandbox (text/sub_skill) and teammate's repository (question_text/sub_topic) keys
    q_data = {
        "id": next_q["id"],
        "text": next_q.get("text") or next_q.get("question_text"),
        "question_text": next_q.get("text") or next_q.get("question_text"),
        "type": next_q["type"],
        "difficulty": next_q["difficulty"],
        "sub_skill": next_q.get("sub_skill") or next_q.get("sub_topic"),
        "sub_topic": next_q.get("sub_skill") or next_q.get("sub_topic"),
        "options": next_q.get("options", []),
        "finished": False
    }
    return jsonify(q_data)

@app.route('/submit-answer', methods=['POST'])
def submit_answer():
    data = request.get_json() or {}
    
    participant_id = data.get('participant_id', 'Unknown')
    device_type = data.get('device_type', 'Unknown')
    question_id = data.get('question_id')
    answer_given = data.get('answer_given')
    tab_switches = data.get('tab_switches', 0)
    mouse_idle_time = data.get('mouse_idle_time', 0.0)
    typing_pauses = data.get('typing_pauses', 0)
    backspaces = data.get('backspaces', 0)
    used_visual_toggle = data.get('used_visual_toggle', False)
    visual_level_used = data.get('visual_level_used', 0)
    frustration_label = data.get('frustration_label')  # 'Low', 'Medium', 'High', or null
    
    if question_id is None:
        return jsonify({"error": "Missing question_id"}), 400
        
    # Verify the question exists
    questions = load_questions()
    question = next((q for q in questions if str(q["id"]) == str(question_id)), None)
    if not question:
        return jsonify({"error": f"Question with ID {question_id} not found"}), 404
        
    session = get_session_state(participant_id)
    
    # Calculate time taken (with fallback to 'Unknown' state for test suite compatibility)
    start_time = session["start_time"]
    if start_time is None:
        unknown_session = get_session_state("Unknown")
        if unknown_session["start_time"] and unknown_session["current_question_id"] == question_id:
            start_time = unknown_session["start_time"]
            
    time_taken = 0.0
    if start_time:
        time_taken = time.time() - start_time
    
    # Support both old sandbox key names and teammate's new key names
    correct_ans_val = question.get("correct_answer") or question.get("answer")
    sub_skill_val = question.get("sub_skill") or question.get("sub_topic") or "general"
    
    # Check correctness (clean whitespaces, dollar signs, and lower-case comparison for safety)
    given_ans = str(answer_given).strip().lower().replace("$", "") if answer_given is not None else ""
    correct_ans = str(correct_ans_val).strip().lower().replace("$", "")
    
    # 1. Handle skips explicitly
    open_ended_skills = ['simple-writing', 'creative-writing', 'opinion-formulation', 'descriptive-summarization']
    if given_ans == "skipped":
        is_correct = False
    # 2. Open-ended writing questions (always correct if they type a response of >= 2 chars)
    elif sub_skill_val in open_ended_skills:
        is_correct = len(given_ans) >= 2
        
    # 3. Reading comprehension lenient match
    elif sub_skill_val == "simple-reading":
        # Accept if they contain core words (e.g. for Q10: "red" and "car")
        if "red" in correct_ans and "car" in correct_ans:
            is_correct = ("red" in given_ans) and ("car" in given_ans)
        else:
            is_correct = (correct_ans in given_ans)
            
    # 4. Missing operator lenient match (e.g. for Q15: "8 __ 4 __ 2 = 6")
    elif sub_skill_val == "missing-operator":
        has_minus = ('-' in given_ans or 'minus' in given_ans)
        has_plus = ('+' in given_ans or 'plus' in given_ans or 'add' in given_ans)
        has_divide = ('/' in given_ans or 'divide' in given_ans or 'div' in given_ans)
        is_correct = (has_minus and (has_plus or has_divide))
            
    # 5. Numeric float comparison (e.g. 2.8 == 2.80, or 8 == 8.0)
    else:
        try:
            is_correct = abs(float(given_ans) - float(correct_ans)) < 0.0001
        except ValueError:
            is_correct = (given_ans == correct_ans)
    
    # Increment retry count if wrong
    q_id_str = str(question_id)
    retry_count = session["retry_counts"].get(q_id_str, 0)
    
    if not is_correct:
        retry_count = retry_count + 1
        session["retry_counts"][q_id_str] = retry_count
        
    off_tab_duration = float(data.get('off_tab_duration', 0.0))
    q_type_val = question.get("type", "mcq")
    q_text_val = question.get("question_text") or question.get("text") or ""
    q_diff_val = question.get("difficulty", "easy")
    
    # 1. Layer 1: Decision Tree prediction
    pred_frustration = predict_frustration_level(
        retry_count, time_taken, tab_switches, mouse_idle_time, typing_pauses, used_visual_toggle
    )
    
    # 2. Unified Layer 2 + Layer 3 Single API Call (Strict 1.5s Timeout)
    if frustration_label:
        detected_frustration = frustration_label
        kip_narration = get_static_fallback_narration(detected_frustration, sub_skill_val)
    else:
        detected_frustration, kip_narration = audit_and_narrate_with_llm(
            pred_frustration, is_correct, retry_count, time_taken, tab_switches, mouse_idle_time, typing_pauses, used_visual_toggle, q_text=q_text_val, q_diff=q_diff_val, q_type=q_type_val, off_tab_duration=off_tab_duration, sub_skill=sub_skill_val
        )
        
    # Log the complete session records
    log_record = {
        "participant_id": participant_id,
        "device_type": device_type,
        "question_id": question_id,
        "answer_given": answer_given,
        "tab_switches": tab_switches,
        "mouse_idle_time": round(mouse_idle_time, 2),
        "typing_pauses": typing_pauses,
        "backspaces": backspaces,
        "used_visual_toggle": used_visual_toggle,
        "visual_level_used": visual_level_used,
        "frustration_label": detected_frustration,
        "correct": is_correct,
        "retry_count": retry_count,
        "time_taken": round(time_taken, 2),
        "sub_skill": sub_skill_val,
        "difficulty": question.get("difficulty", "easy"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_source": data.get("data_source", "real")
    }
    
    save_log_record(log_record)
    
    # Sync compatibility for unit tests
    session_state.clear()
    session_state.update(session)
    
    trigger_reset_mission = (detected_frustration == "High")
    reset_mission = None
    if trigger_reset_mission:
        reset_mission = random.choice(RESET_MISSIONS_POOL)
    
    return jsonify({
        "correct": is_correct,
        "correct_answer": correct_ans_val,
        "retry_count_after": session["retry_counts"].get(q_id_str, 0),
        "frustration_level": detected_frustration,
        "kip_narration": kip_narration,
        "trigger_reset_mission": trigger_reset_mission,
        "reset_mission": reset_mission
    })

@app.route('/get-dashboard-data', methods=['GET'])
def get_dashboard_data():
    logs = load_logs()
    
    dashboard = {}
    for log in logs:
        sub_skill = log.get("sub_skill")
        if not sub_skill:
            continue
            
        if sub_skill not in dashboard:
            dashboard[sub_skill] = {
                "attempts": 0,
                "correct": 0
            }
            
        dashboard[sub_skill]["attempts"] += 1
        if log.get("correct") is True:
            dashboard[sub_skill]["correct"] += 1
            
    return jsonify(dashboard)

@app.route('/export-training-csv', methods=['GET'])
def export_training_csv():
    logs = load_logs()
    
    # Filter logs that have a frustration_label filled in
    filtered_logs = [
        log for log in logs 
        if log.get("frustration_label") in ['Low', 'Medium', 'High']
    ]
    
    fieldnames = [
        'participant_id',
        'device_type',
        'retry_count', 
        'time_taken', 
        'tab_switches', 
        'mouse_idle_time', 
        'typing_pauses', 
        'used_visual_toggle', 
        'frustration_label',
        'data_source'
    ]
    
    try:
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for log in filtered_logs:
                # Ensure values match columns, default boolean used_visual_toggle to int or string
                row = {
                    'participant_id': log.get('participant_id', 'Unknown'),
                    'device_type': log.get('device_type', 'Unknown'),
                    'retry_count': log.get('retry_count', 0),
                    'time_taken': log.get('time_taken', 0.0),
                    'tab_switches': log.get('tab_switches', 0),
                    'mouse_idle_time': log.get('mouse_idle_time', 0.0),
                    'typing_pauses': log.get('typing_pauses', 0),
                    'used_visual_toggle': 1 if log.get('used_visual_toggle') else 0,
                    'frustration_label': log.get('frustration_label'),
                    'data_source': log.get('data_source', 'real')
                }
                writer.writerow(row)
                
        return send_file(
            CSV_FILE, 
            as_attachment=True, 
            download_name='training_sessions.csv', 
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/reset-session', methods=['POST'])
def reset_session():
    participant_id = request.args.get('participant_id', 'Unknown')
    init_db_if_needed()
    
    if use_postgres:
        conn = None
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM session_logs WHERE participant_id = %s", (participant_id,))
                conn.commit()
        except Exception as e:
            print(f"Error deleting logs from PostgreSQL: {e}")
        finally:
            if conn:
                conn.close()
    else:
        logs = load_logs()
        # Keep only logs that belong to other participants
        logs = [log for log in logs if log.get("participant_id") != participant_id]
        try:
            with open(LOGS_FILE, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Error writing to {LOGS_FILE}: {e}")
            
    # Reset session_states cache
    if participant_id in session_states:
        del session_states[participant_id]
    
    # Sync compatibility
    session_state.clear()
    
    return jsonify({
        "success": True,
        "message": f"In-memory and persistent session logs have been reset for {participant_id}."
    })

@app.route('/get-kip-reasoning', methods=['GET'])
def get_kip_reasoning():
    participant_id = request.args.get('participant_id', 'Unknown')
    
    # Query database for the latest log record
    latest_record = None
    if use_postgres:
        conn = None
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM session_logs 
                    WHERE participant_id = %s 
                    ORDER BY id DESC LIMIT 1
                """, (participant_id,))
                row = cur.fetchone()
                if row:
                    latest_record = dict(row)
        except Exception as e:
            print(f"Error fetching latest log: {e}")
        finally:
            if conn:
                conn.close()
    else:
        # JSON fallback
        logs = load_logs()
        p_logs = [l for l in logs if l.get("participant_id") == participant_id]
        if p_logs:
            latest_record = p_logs[-1]
            
    if not latest_record:
        return jsonify({
            "frustration_level": "Low",
            "reasoning": "Hi! I'm Kip, your learning buddy. Let's do some questions together!"
        })
        
    verified_frustration = latest_record.get("frustration_label", "Low")
    sub_skill = latest_record.get("sub_skill", "general")
    retry_count = latest_record.get("retry_count", 0)
    time_taken = latest_record.get("time_taken", 0.0)
    
    # Check if Gemini key is present
    if not GEMINI_API_KEY:
        reasoning = get_static_fallback_narration(verified_frustration, sub_skill)
        return jsonify({
            "frustration_level": verified_frustration,
            "reasoning": reasoning
        })
        
    # Query Gemini for Kip's narration
    prompt = f"""
    You are Kip, a friendly, supportive AI learning buddy mascot on a student's screen.
    Analyze the student's latest question performance and explain your thoughts in a warm, encouraging, conversational tone.
    
    Latest Question Details:
    - Subject Sub-skill: {sub_skill}
    - Verified student frustration level: {verified_frustration}
    - Attempts/Retries on this question: {retry_count}
    - Time spent: {time_taken:.1f} seconds
    
    Guidelines:
    - Speak directly to the student as Kip (e.g. "I noticed you took your time...", "Hey, math can be tricky but you're doing great!").
    - Keep it short: exactly 1 or 2 sentences.
    - Be empathetic and non-judgmental. If they are frustrated, explain that it's okay to make mistakes.
    - Do not mention technical terms like "classifier", "telemetry", "model", or "verification".
    """
    
    res = call_gemini_with_fallback(prompt, max_tokens=60, temp=0.7, timeout=2.5)
    if res:
        return jsonify({
            "frustration_level": verified_frustration,
            "reasoning": res
        })
        
    reasoning = get_static_fallback_narration(verified_frustration, sub_skill)
    return jsonify({
        "frustration_level": verified_frustration,
        "reasoning": reasoning
    })

if __name__ == '__main__':
    # Run server on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
