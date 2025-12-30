"""
Result management for saving exam results to Excel sheets and Google Sheets
"""
import pandas as pd
import os
from datetime import datetime
from pathlib import Path

# Optional Google Sheets support
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

def save_to_google_sheets(config, training_id, user_info, exam_data, secrets=None):
    """
    Save exam result to Google Sheets (if configured)
    
    Args:
        config: Configuration dictionary
        training_id: Training ID
        user_info: Dictionary with user information
        exam_data: Dictionary with exam data
        secrets: Streamlit secrets object (optional)
    
    Returns:
        bool: True if saved successfully, False otherwise
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        return False
    
    # Check if Google Sheets is configured
    training = None
    for t in config.get("trainings", []):
        if t["id"] == training_id:
            training = t
            break
    
    if not training:
        return False
    
    google_config = training.get("google_sheets", {})
    if not google_config.get("enabled", False):
        return False
    
    try:
        # Get credentials from Streamlit secrets or config
        if secrets:
            s_info = secrets.get("gcp_service_account")
        else:
            s_info = config.get("google_sheets", {}).get("service_account")
        
        if not s_info:
            return False
        
        # Authenticate
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(s_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        # Open the sheet
        sheet_id = google_config.get("sheet_id")
        sheet_name = google_config.get("sheet_name", training.get("result_sheet", "Results"))
        
        sh = gc.open_by_key(sheet_id)
        
        # Try to get worksheet, with better error handling
        try:
            worksheet = sh.worksheet(sheet_name)
        except Exception as e:
            # If worksheet not found, try to list available worksheets
            available_sheets = [ws.title for ws in sh.worksheets()]
            error_msg = f"Worksheet '{sheet_name}' not found. Available sheets: {available_sheets}"
            print(error_msg)
            # Try to use the first worksheet if available
            if available_sheets:
                worksheet = sh.worksheet(available_sheets[0])
                print(f"Using first available worksheet: {available_sheets[0]}")
            else:
                raise Exception(f"No worksheets found in the spreadsheet. {error_msg}")
        
        # Prepare row
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_info.get("name", ""),
            user_info.get("email", ""),
            user_info.get("department", ""),
            exam_data.get("score", 0),
            exam_data.get("max_score", 0),
            str(exam_data.get("answers", {}))
        ]
        
        # Append row
        worksheet.append_row(row)
        print(f"Successfully saved to Google Sheets: {row}")
        return True
    except Exception as e:
        import traceback
        error_msg = f"Error saving to Google Sheets: {e}\n{traceback.format_exc()}"
        print(error_msg)
        # Also try to show error in Streamlit if possible
        try:
            import streamlit as st
            st.error(f"Google Sheets 保存失败: {str(e)}")
        except:
            pass
        return False

def save_exam_result(config, training_id, user_info, exam_data, secrets=None):
    """
    Save exam result to Excel file with training-specific sheet
    Also saves to Google Sheets if configured
    
    Args:
        config: Configuration dictionary
        training_id: Training ID
        user_info: Dictionary with user information (email, name, department)
        exam_data: Dictionary with exam data (score, max_score, answers, questions, etc.)
        secrets: Streamlit secrets object (optional, for Google Sheets)
    
    Returns:
        bool: True if saved successfully, False otherwise
    """
    # Find training config
    training = None
    for t in config.get("trainings", []):
        if t["id"] == training_id:
            training = t
            break
    
    if not training:
        return False
    
    result_file = training["result_file"]
    sheet_name = training["result_sheet"]
    
    # Try to save to Google Sheets first (if configured) - RECOMMENDED for cloud deployment
    google_saved = save_to_google_sheets(config, training_id, user_info, exam_data, secrets)
    
    # Also save to Excel file (for local development)
    # NOTE: In Streamlit Cloud, local files are temporary and may be lost.
    # Always enable Google Sheets for production deployment!
    excel_saved = False
    result_row = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Email": user_info.get("email", ""),
        "Name": user_info.get("name", ""),
        "Department": user_info.get("department", ""),
        "Score": exam_data.get("score", 0),
        "Max_Score": exam_data.get("max_score", 0),
        "Percentage": exam_data.get("percentage", 0),
        "Time_Taken_Minutes": exam_data.get("time_taken_minutes", 0),
        "Time_Taken_Seconds": exam_data.get("time_taken_seconds", 0),
        "Total_Questions": exam_data.get("total_questions", 0),
        "Correct_Answers": exam_data.get("correct_answers", 0),
        "Training_ID": training_id,
        "Training_Name": training.get("name", "")
    }
    
    # Add detailed answers (as JSON string for storage)
    import json
    result_row["Answers_JSON"] = json.dumps(exam_data.get("answers", {}), ensure_ascii=False)
    result_row["Questions_JSON"] = json.dumps(exam_data.get("questions_summary", []), ensure_ascii=False)
    
    # Convert to DataFrame
    new_row_df = pd.DataFrame([result_row])
    
    # Try to save to Excel file (for local development)
    # NOTE: In Streamlit Cloud, local files are temporary and may be lost.
    # Always enable Google Sheets for production deployment!
    excel_saved = False
    try:
        if os.path.exists(result_file):
            # Read existing file
            with pd.ExcelFile(result_file) as xls:
                if sheet_name in xls.sheet_names:
                    # Sheet exists, append to it
                    existing_df = pd.read_excel(result_file, sheet_name=sheet_name)
                    updated_df = pd.concat([existing_df, new_row_df], ignore_index=True)
                else:
                    # Sheet doesn't exist, create new
                    updated_df = new_row_df
                
                # Read all sheets
                all_sheets = {}
                with pd.ExcelFile(result_file) as xls:
                    for sheet in xls.sheet_names:
                        if sheet != sheet_name:
                            all_sheets[sheet] = pd.read_excel(result_file, sheet_name=sheet)
                
                # Write all sheets back
                with pd.ExcelWriter(result_file, engine='openpyxl') as writer:
                    for sheet, df in all_sheets.items():
                        df.to_excel(writer, sheet_name=sheet, index=False)
                    updated_df.to_excel(writer, sheet_name=sheet_name, index=False)
            excel_saved = True
        else:
            # File doesn't exist, create new
            with pd.ExcelWriter(result_file, engine='openpyxl') as writer:
                new_row_df.to_excel(writer, sheet_name=sheet_name, index=False)
            excel_saved = True
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        excel_saved = False
    
    # Return True if either Excel or Google Sheets save succeeded
    # For cloud deployment, Google Sheets is recommended
    return excel_saved or google_saved

def get_training_results(config, training_id, limit=100):
    """
    Get recent exam results for a training
    
    Args:
        config: Configuration dictionary
        training_id: Training ID
        limit: Maximum number of results to return
    
    Returns:
        pd.DataFrame: DataFrame with results, or empty DataFrame if error
    """
    # Find training config
    training = None
    for t in config.get("trainings", []):
        if t["id"] == training_id:
            training = t
            break
    
    if not training:
        return pd.DataFrame()
    
    result_file = training["result_file"]
    sheet_name = training["result_sheet"]
    
    if not os.path.exists(result_file):
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(result_file, sheet_name=sheet_name)
        # Return most recent results
        return df.tail(limit)
    except Exception as e:
        print(f"Error reading results: {e}")
        return pd.DataFrame()

