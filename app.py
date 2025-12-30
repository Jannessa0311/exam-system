import streamlit as st
import pandas as pd
import random
import json
import os
from datetime import datetime
from github_utils import get_file_path, check_file_exists_local
from result_manager import save_exam_result

# Page configuration
st.set_page_config(
    page_title="Online Exam System",
    page_icon="📝",
    layout="centered"
)

# Initialize session state
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.now()
if 'exam_questions' not in st.session_state:
    st.session_state.exam_questions = []
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'user_department' not in st.session_state:
    st.session_state.user_department = ""
if 'selected_training' not in st.session_state:
    st.session_state.selected_training = None
if 'config' not in st.session_state:
    st.session_state.config = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'  # 'login' or 'quiz' or 'results'

# Load configuration
def load_config():
    """Load configuration from config.json"""
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading config: {e}")
            return None
    else:
        # Return default config
        return {
            "github": {"enabled": False},
            "trainings": [],
            "local_mode": True
        }

# Initialize config
if st.session_state.config is None:
    st.session_state.config = load_config()

def load_questions_from_excel(file_path):
    """Load questions from Excel file"""
    df = pd.read_excel(file_path)
    
    questions = []
    for idx, row in df.iterrows():
        # Only process Single and Multi type questions
        question_type = str(row['Type']).strip()
        if question_type not in ['Single', 'Multi']:
            continue
        
        # Get question text
        question_text = str(row['Question Text']).strip()
        if pd.isna(question_text) or question_text == '':
            continue
        
        # Get options (columns A, B, C, D, E, F)
        options = []
        option_letters = ['A', 'B', 'C', 'D', 'E', 'F']
        for letter in option_letters:
            option_value = row[letter]
            if pd.notna(option_value) and str(option_value).strip() != '':
                options.append(str(option_value).strip())
        
        if len(options) == 0:
            continue
        
        # Get correct answer
        if pd.isna(row['Correct Answer']):
            continue
        correct_answer_raw = str(row['Correct Answer']).strip()
        if correct_answer_raw == '' or correct_answer_raw.lower() == 'nan':
            continue
        
        # Get points
        points = row['Points']
        if pd.isna(points):
            points = 1.0
        else:
            points = float(points)
        
        # Process correct answer
        if question_type == 'Single':
            # Single choice: correct answer is option letter, need to convert to option text
            correct_answer_letter = correct_answer_raw.upper()
            if correct_answer_letter in option_letters[:len(options)]:
                correct_answer = options[option_letters.index(correct_answer_letter)]
            else:
                continue
        else:  # Multi
            # Multiple choice: correct answer may be multiple letters (e.g., "AB" or "A,B")
            correct_answer_letters = [c.strip().upper() for c in correct_answer_raw.replace(',', ' ').split()]
            correct_answer = []
            for letter in correct_answer_letters:
                if letter in option_letters[:len(options)]:
                    correct_answer.append(options[option_letters.index(letter)])
            if len(correct_answer) == 0:
                continue
        
        # Build question object
        question = {
            "id": idx + 1,
            "type": "single_choice" if question_type == 'Single' else "multiple_choice",
            "question": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "points": points
        }
        
        questions.append(question)
    
    return questions

def get_random_questions_with_target_score(all_questions, target_score=100, max_attempts=1000):
    """
    Randomly select questions from all questions to make total score equal to target_score
    Uses backtracking algorithm to find all possible combinations, then randomly selects one
    If there are too many questions, uses greedy + random method
    """
    # If number of questions is small, use dynamic programming
    if len(all_questions) <= 30:
        return _find_combination_dp(all_questions, target_score)
    else:
        # If number of questions is large, use multiple random attempts
        return _find_combination_random(all_questions, target_score, max_attempts)

def _find_combination_dp(all_questions, target_score):
    """Find all possible combinations using dynamic programming"""
    # Shuffle questions to increase randomness
    shuffled_questions = all_questions.copy()
    random.shuffle(shuffled_questions)
    
    # Use dynamic programming to find all possible combinations
    # dp[i] stores list of question combinations that can reach score i (keep only one combo to save memory)
    # Use floating point, but for performance and memory, scale by 100 and convert to integer
    SCALE = 100  # Scale score by 100 for integer calculation
    target_score_scaled = int(target_score * SCALE)
    dp = {0: [[]]}  # 0 points corresponds to empty combination
    
    for question in shuffled_questions:
        points = float(question["points"])  # Keep as float
        points_scaled = int(points * SCALE)  # Scale and convert to integer for calculation
        new_dp = dp.copy()
        
        for score in sorted(dp.keys(), reverse=True):
            new_score = score + points_scaled
            if new_score <= target_score_scaled:
                if new_score not in new_dp:
                    new_dp[new_score] = []
                # Only keep some combinations to avoid memory explosion
                for combo in dp[score][:10]:  # Keep at most 10 combinations per score
                    new_combo = combo + [question]
                    new_dp[new_score].append(new_combo)
        
        dp = new_dp
    
    # If found combination exactly equal to target_score
    if target_score_scaled in dp and len(dp[target_score_scaled]) > 0:
        # Randomly select a combination
        selected_combo = random.choice(dp[target_score_scaled])
        return selected_combo
    
    # If cannot find exactly 100 points combination, try to find closest combination
    best_score = None
    best_combos = []
    
    # First find >= 100 points but closest
    for score in sorted(dp.keys(), reverse=True):
        if score >= target_score_scaled:
            if best_score is None or score < best_score:
                best_score = score
                best_combos = dp[score]
            elif score == best_score:
                best_combos.extend(dp[score])
    
    # If didn't find >= 100 points, find < 100 points but closest
    if best_score is None:
        for score in sorted(dp.keys(), reverse=True):
            if score < target_score_scaled:
                if best_score is None or score > best_score:
                    best_score = score
                    best_combos = dp[score]
                elif score == best_score:
                    best_combos.extend(dp[score])
    
    if best_combos:
        return random.choice(best_combos)
    
    return []

def _find_combination_random(all_questions, target_score, max_attempts):
    """Find combination using random attempt method"""
    shuffled_questions = all_questions.copy()
    
    best_combo = None
    best_diff = float('inf')
    
    for _ in range(max_attempts):
        random.shuffle(shuffled_questions)
        current_combo = []
        current_score = 0.0  # Use float
    
        for question in shuffled_questions:
            points = float(question["points"])  # Use float instead of integer
            if current_score + points <= target_score:
                current_combo.append(question)
                current_score += points
                
                # Use small tolerance to compare floats
                if abs(current_score - target_score) < 0.01:
                    return current_combo
        
        # Record closest combination
        diff = abs(current_score - target_score)
        if diff < best_diff:
            best_diff = diff
            best_combo = current_combo.copy()
    
    # If found close combination, try to fine-tune
    if best_combo and best_diff > 0.01:
        # Try to add or remove questions to reach target score
        remaining_questions = [q for q in shuffled_questions if q not in best_combo]
        current_score = sum(float(q["points"]) for q in best_combo)  # Use float
        
        if current_score < target_score:
            # Try to add questions
            for q in remaining_questions:
                new_score = current_score + float(q["points"])
                if abs(new_score - target_score) < 0.01:
                    return best_combo + [q]
        elif current_score > target_score:
            # Try to remove questions
            for q in best_combo:
                new_score = current_score - float(q["points"])
                if abs(new_score - target_score) < 0.01:
                    new_combo = best_combo.copy()
                    new_combo.remove(q)
                    return new_combo
    
    return best_combo if best_combo else []

def calculate_score():
    """Calculate total score"""
    total_score = 0
    exam_questions = st.session_state.exam_questions
    max_score = sum(q["points"] for q in exam_questions)
    
    for question in exam_questions:
        q_id = question["id"]
        if q_id in st.session_state.answers:
            user_answer = st.session_state.answers[q_id]
            correct_answer = question["correct_answer"]
            
            if question["type"] == "single_choice":
                if user_answer == correct_answer:
                    total_score += question["points"]
            elif question["type"] == "multiple_choice":
                if set(user_answer) == set(correct_answer):
                    total_score += question["points"]
    
    return total_score, max_score

def show_results():
    """Display exam results"""
    st.header("📊 Exam Results")
    
    # Display user information
    st.subheader("👤 Personal Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Name:** {st.session_state.user_name}")
    with col2:
        st.write(f"**Email:** {st.session_state.user_email}")
    with col3:
        st.write(f"**Department:** {st.session_state.user_department}")
    
    st.markdown("---")
    
    score, max_score = calculate_score()
    percentage = (score / max_score * 100) if max_score > 0 else 0
    
    # Display total score
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{score}/{max_score}")
    with col2:
        st.metric("Accuracy", f"{percentage:.1f}%")
    with col3:
        elapsed = datetime.now() - st.session_state.start_time
        minutes = elapsed.seconds // 60
        seconds = elapsed.seconds % 60
        st.metric("Time", f"{minutes} min {seconds} sec")
    
    # Save result to Excel
    if st.session_state.selected_training and st.session_state.config:
        exam_questions = st.session_state.exam_questions
        correct_count = 0
        questions_summary = []
        
        for question in exam_questions:
            q_id = question["id"]
            user_answer = st.session_state.answers.get(q_id)
            correct_answer = question["correct_answer"]
            
            is_correct = False
            if question["type"] == "single_choice":
                is_correct = user_answer == correct_answer
            elif question["type"] == "multiple_choice":
                is_correct = set(user_answer) == set(correct_answer) if isinstance(user_answer, list) else False
            
            if is_correct:
                correct_count += 1
            
            questions_summary.append({
                "question_id": q_id,
                "question": question["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "points": question["points"]
            })
        
        exam_data = {
            "score": score,
            "max_score": max_score,
            "percentage": percentage,
            "time_taken_minutes": minutes,
            "time_taken_seconds": seconds,
            "total_questions": len(exam_questions),
            "correct_answers": correct_count,
            "answers": st.session_state.answers,
            "questions_summary": questions_summary
        }
        
        user_info = {
            "email": st.session_state.user_email,
            "name": st.session_state.user_name,
            "department": st.session_state.user_department
        }
        
        # Try to get Streamlit secrets if available
        try:
            secrets = st.secrets
            # Debug: check if secrets are loaded
            if hasattr(secrets, 'gcp_service_account'):
                st.info("✅ Google Sheets credentials loaded")
        except Exception as e:
            secrets = None
            st.warning(f"⚠️ Could not load Streamlit secrets: {e}")
        
        saved = save_exam_result(st.session_state.config, st.session_state.selected_training, user_info, exam_data, secrets)
        if saved:
            st.success("✅ Exam result saved successfully!")
            
            # Provide download option for Excel file
            training = None
            for t in st.session_state.config.get("trainings", []):
                if t["id"] == st.session_state.selected_training:
                    training = t
                    break
            
            if training:
                result_file = training.get("result_file", "")
                if result_file and os.path.exists(result_file):
                    with open(result_file, 'rb') as f:
                        st.download_button(
                            label="📥 Download Results Excel File",
                            data=f.read(),
                            file_name=result_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Download the Excel file containing all exam results"
                        )
            
            # Check if we're in a cloud environment (Streamlit Cloud)
            is_cloud = os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("STREAMLIT_SERVER_PORT")
            if is_cloud:
                st.info("💡 **Note:** In cloud deployment, Excel files are temporary. Download the file above to save your data, or configure Google Sheets for automatic persistence.")
        else:
            st.error("❌ Failed to save exam result. Please check configuration.")
            # Check if we're in a cloud environment
            is_cloud = os.getenv("STREAMLIT_SHARING_MODE") or os.getenv("STREAMLIT_SERVER_PORT")
            if is_cloud:
                st.warning("⚠️ **Important:** If deployed on Streamlit Cloud, Excel files are temporary. Consider:")
                st.markdown("""
                - **Option 1:** Download the Excel file manually (if available)
                - **Option 2:** Configure Google Sheets for automatic persistence (see `GOOGLE_SHEETS_SETUP.md`)
                - **Option 3:** Use local deployment where Excel files are permanent
                """)
    
    # Display detailed results for each question
    st.subheader("📋 Detailed Answers")
    
    exam_questions = st.session_state.exam_questions
    for idx, question in enumerate(exam_questions, 1):
        q_id = question["id"]
        with st.expander(f"Question {idx}: {question['question']} ({question['points']} points)", expanded=False):
            user_answer = st.session_state.answers.get(q_id, "Not answered")
            correct_answer = question["correct_answer"]
            
            # Check if correct
            is_correct = False
            if question["type"] == "single_choice":
                is_correct = user_answer == correct_answer
            elif question["type"] == "multiple_choice":
                is_correct = set(user_answer) == set(correct_answer) if isinstance(user_answer, list) else False
            
            # Display answers
            if question["type"] == "multiple_choice":
                st.write(f"**Your answer:** {', '.join(user_answer) if isinstance(user_answer, list) else user_answer}")
                st.write(f"**Correct answer:** {', '.join(correct_answer)}")
            else:
                st.write(f"**Your answer:** {user_answer}")
                st.write(f"**Correct answer:** {correct_answer}")
            
            if is_correct:
                st.success(f"✅ Correct! Earned {question['points']} points")
            else:
                st.error(f"❌ Incorrect. This question is worth {question['points']} points")
    
    # Reset button
    if st.button("🔄 Retake Exam"):
        # Reset exam state but keep training selection
        training_id = st.session_state.selected_training
        for key in ['answers', 'submitted', 'score', 'start_time', 'exam_questions', 'user_email', 'user_name', 'user_department']:
            if key in st.session_state:
                if key == 'exam_questions':
                    st.session_state[key] = []
                elif key in ['user_email', 'user_name', 'user_department']:
                    st.session_state[key] = ""
                elif key == 'submitted':
                    st.session_state[key] = False
                elif key == 'score':
                    st.session_state[key] = 0
                elif key == 'start_time':
                    st.session_state[key] = datetime.now()
                elif key == 'answers':
                    st.session_state[key] = {}
        st.session_state.selected_training = training_id
        st.rerun()

def main():
    st.title("📝 Online Exam System")
    st.markdown("---")
    
    # Load configuration
    config = st.session_state.config
    if config is None:
        st.error("❌ Unable to load configuration. Please check config.json!")
        return
    
    # Training selection
    trainings = config.get("trainings", [])
    if len(trainings) == 0:
        st.error("❌ No trainings configured. Please add trainings to config.json!")
        return
    
    # Training selector in sidebar
    with st.sidebar:
        st.header("🎓 Training Selection")
        training_options = {t["name"]: t["id"] for t in trainings}
        selected_training_name = st.selectbox(
            "Select Training:",
            options=list(training_options.keys()),
            index=0 if not st.session_state.selected_training else 
                  next((i for i, t in enumerate(trainings) if t["id"] == st.session_state.selected_training), 0)
        )
        selected_training_id = training_options[selected_training_name]
        
        # Update selected training if changed
        if st.session_state.selected_training != selected_training_id:
            # Reset exam state when training changes
            for key in ['answers', 'submitted', 'score', 'exam_questions', 'start_time']:
                if key in st.session_state:
                    if key == 'exam_questions':
                        st.session_state[key] = []
                    elif key == 'submitted':
                        st.session_state[key] = False
                    elif key == 'score':
                        st.session_state[key] = 0
                    elif key == 'start_time':
                        st.session_state[key] = datetime.now()
                    elif key == 'answers':
                        st.session_state[key] = {}
            st.session_state.selected_training = selected_training_id
        
        # Display training info
        selected_training = next((t for t in trainings if t["id"] == selected_training_id), None)
        if selected_training:
            st.info(f"**Training:** {selected_training['name']}")
            st.info(f"**Description:** {selected_training.get('description', 'N/A')}")
            st.info(f"**Target Score:** {selected_training.get('target_score', 100)} points")
    
    # Get question file path (local or from GitHub)
    if selected_training:
        question_file_path = get_file_path(config, selected_training_id, "question")
        
        if question_file_path is None:
            st.error(f"❌ Unable to find question file for training '{selected_training['name']}'. Please check configuration!")
            return
        
        # Load question pool
        all_questions = load_questions_from_excel(question_file_path)
        
        if len(all_questions) == 0:
            st.error("❌ Unable to load questions from Excel file. Please check the file format!")
            return
        
        # Get target score from training config
        TARGET_SCORE = selected_training.get("target_score", 100)
    else:
        st.error("❌ No training selected!")
        return
    
    # If exam questions haven't been generated yet, or user clicked to reselect
    if len(st.session_state.exam_questions) == 0:
        # Settings in sidebar
        with st.sidebar:
            st.header("⚙️ Exam Settings")
            st.write(f"**Target Total Score:** {TARGET_SCORE} points")
            st.write(f"**Total Questions in Pool:** {len(all_questions)} questions")
            
            # Check maximum possible total score from question pool
            max_possible_score = sum(q["points"] for q in all_questions)
            
            if max_possible_score < TARGET_SCORE:
                st.warning(f"⚠️ Maximum possible total score from question pool is {max_possible_score} points, cannot reach {TARGET_SCORE} points")
                st.info(f"The system will select the closest combination ({max_possible_score} points)")
            
            if st.button(f"🎲 Generate Random Questions (Target: {TARGET_SCORE} points)", type="primary", use_container_width=True):
                with st.spinner("Generating questions..."):
                    selected_questions = get_random_questions_with_target_score(all_questions, TARGET_SCORE)
                    if len(selected_questions) == 0:
                        st.error("❌ Unable to find suitable question combination. Please check the question pool!")
                    else:
                        actual_score = sum(q["points"] for q in selected_questions)
                        if actual_score != TARGET_SCORE:
                            st.warning(f"⚠️ Cannot reach exactly {TARGET_SCORE} points. Selected closest combination ({actual_score} points)")
                        st.session_state.exam_questions = selected_questions
                        st.session_state.answers = {}
                        st.session_state.submitted = False
                        st.session_state.start_time = datetime.now()
                        st.rerun()
            
            st.markdown("---")
            st.write("**Instructions:**")
            st.write(f"The system will randomly select questions with a target total score of {TARGET_SCORE} points")
            st.write(f"Maximum possible total score from question pool: {max_possible_score} points")
    
    if not st.session_state.submitted:
        exam_questions = st.session_state.exam_questions
        
        if len(exam_questions) == 0:
            st.info("👆 Please click 'Generate Random Questions' in the sidebar to start the exam")
            return
        
        # Display exam instructions
        with st.sidebar:
            st.header("📌 Exam Instructions")
            st.write(f"**Total Questions:** {len(exam_questions)} questions")
            st.write(f"**Total Score:** {sum(q['points'] for q in exam_questions)} points")
            st.write(f"**Start Time:** {st.session_state.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown("---")
            st.write("**Notes:**")
            st.write("1. Please read each question carefully")
            st.write("2. Single choice questions allow only one answer")
            st.write("3. Multiple choice questions allow multiple answers")
            st.write("4. Answers cannot be changed after submission")
        
        # Display user information fields
        st.subheader("👤 Personal Information")
        st.markdown("**Please fill in the following information:**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.user_name = st.text_input(
                "Full Name *",
                value=st.session_state.user_name,
                key="user_name_input"
            )
        with col2:
            st.session_state.user_email = st.text_input(
                "Company Email *",
                value=st.session_state.user_email,
                key="user_email_input"
            )
        
        st.session_state.user_department = st.text_input(
            "Department *",
            value=st.session_state.user_department,
            key="user_department_input"
        )
        
        st.markdown("---")
        
        # Display questions
        st.subheader("📋 Exam Questions")
        
        for idx, question in enumerate(exam_questions, 1):
            # Display question type clearly
            question_type_label = "[Single Choice]" if question["type"] == "single_choice" else "[Multiple Choice]"
            st.markdown(f"### Question {idx} ({question['points']} points) {question_type_label}")
            st.write(f"**{question['question']}**")
            
            q_id = question["id"]
            
            if question["type"] == "single_choice":
                # Single choice question - use radio buttons, no default selection
                current_answer = st.session_state.answers.get(q_id)
                
                # Determine index: use current answer if exists, otherwise None (no default)
                # Note: index=None requires Streamlit >= 1.28.0
                if current_answer and current_answer in question["options"]:
                    default_index = question["options"].index(current_answer)
                else:
                    default_index = None
                
                selected = st.radio(
                    "Please select your answer:",
                    options=question["options"],
                    key=f"q_{q_id}",
                    index=default_index
                )
                
                if selected is not None:
                    st.session_state.answers[q_id] = selected
                else:
                    # Remove from answers if no selection
                    if q_id in st.session_state.answers:
                        del st.session_state.answers[q_id]
                
            elif question["type"] == "multiple_choice":
                # Multiple choice question - use checkboxes
                current_answers = st.session_state.answers.get(q_id, [])
                if not isinstance(current_answers, list):
                    current_answers = []
                
                st.write("Please select your answer(s):")
                selected_options = []
                
                for option in question["options"]:
                    is_selected = option in current_answers
                    checkbox_key = f"q_{q_id}_{option}"
                    if st.checkbox(option, value=is_selected, key=checkbox_key):
                        selected_options.append(option)
                
                st.session_state.answers[q_id] = selected_options
            
            st.markdown("---")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✅ Submit Exam", type="primary", use_container_width=True):
                # Check if user information is filled
                missing_info = []
                if not st.session_state.user_name or st.session_state.user_name.strip() == "":
                    missing_info.append("Full Name")
                if not st.session_state.user_email or st.session_state.user_email.strip() == "":
                    missing_info.append("Company Email")
                if not st.session_state.user_department or st.session_state.user_department.strip() == "":
                    missing_info.append("Department")
                
                if missing_info:
                    st.warning(f"⚠️ Please fill in the following information: {', '.join(missing_info)}")
                else:
                    # Check if all questions have been answered
                    unanswered = []
                    for question in exam_questions:
                        q_id = question["id"]
                        if q_id not in st.session_state.answers:
                            unanswered.append(q_id)
                        elif question["type"] == "multiple_choice" and len(st.session_state.answers[q_id]) == 0:
                            unanswered.append(q_id)
                    
                    if unanswered:
                        st.warning(f"⚠️ There are {len(unanswered)} unanswered question(s). Please complete all questions before submitting!")
                    else:
                        st.session_state.submitted = True
                        st.session_state.score = calculate_score()[0]
                        st.rerun()
    else:
        # Display results
        show_results()

if __name__ == "__main__":
    main()

