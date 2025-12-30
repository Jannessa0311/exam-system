"""
GitHub utilities for downloading resources
"""
import os
import requests
import json
from pathlib import Path

def download_file_from_github(repo_owner, repo_name, file_path, branch="main", token=None, save_path=None):
    """
    Download a file from GitHub repository
    
    Args:
        repo_owner: GitHub repository owner
        repo_name: Repository name
        file_path: Path to file in repository
        branch: Branch name (default: main)
        token: GitHub personal access token (optional, for private repos)
        save_path: Local path to save the file
    
    Returns:
        str: Path to downloaded file, or None if failed
    """
    # GitHub raw content URL
    if token:
        url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/{file_path}"
        headers = {"Authorization": f"token {token}"}
    else:
        # For public repos, use raw.githubusercontent.com
        url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/{file_path}"
        headers = {}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Determine save path
        if save_path is None:
            save_path = os.path.join("downloads", file_path)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save file
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return save_path
    except Exception as e:
        print(f"Error downloading file from GitHub: {e}")
        return None

def download_file_from_github_api(repo_owner, repo_name, file_path, branch="main", token=None, save_path=None):
    """
    Download a file from GitHub using GitHub API (supports larger files)
    
    Args:
        repo_owner: GitHub repository owner
        repo_name: Repository name
        file_path: Path to file in repository
        branch: Branch name (default: main)
        token: GitHub personal access token (required for private repos)
        save_path: Local path to save the file
    
    Returns:
        str: Path to downloaded file, or None if failed
    """
    if not token:
        # Fallback to raw content for public repos
        return download_file_from_github(repo_owner, repo_name, file_path, branch, None, save_path)
    
    # GitHub API URL
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    params = {"ref": branch}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        # Determine save path
        if save_path is None:
            save_path = os.path.join("downloads", file_path)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save file
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return save_path
    except Exception as e:
        print(f"Error downloading file from GitHub API: {e}")
        return None

def check_file_exists_local(file_path):
    """Check if file exists locally"""
    return os.path.exists(file_path)

def get_file_path(config, training_id, file_type="question"):
    """
    Get file path for a training, checking local first, then GitHub if needed
    
    Args:
        config: Configuration dictionary
        training_id: Training ID
        file_type: "question" or "result"
    
    Returns:
        str: File path, or None if not found
    """
    # Find training config
    training = None
    for t in config.get("trainings", []):
        if t["id"] == training_id:
            training = t
            break
    
    if not training:
        return None
    
    # Determine file name
    if file_type == "question":
        file_name = training["question_file"]
    else:
        file_name = training["result_file"]
    
    # Check local first
    if check_file_exists_local(file_name):
        return file_name
    
    # If GitHub is enabled, try to download
    if config.get("github", {}).get("enabled", False) and not config.get("local_mode", True):
        github_config = config["github"]
        repo_owner = github_config.get("repo_owner")
        repo_name = github_config.get("repo_name")
        branch = github_config.get("branch", "main")
        token = github_config.get("token")
        
        if repo_owner and repo_name:
            # Try to download from GitHub
            downloaded_path = download_file_from_github_api(
                repo_owner, repo_name, file_name, branch, token
            )
            if downloaded_path:
                return downloaded_path
    
    return None

