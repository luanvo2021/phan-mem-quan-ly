import os
import streamlit as st
from github import Github
from github import Auth

def get_github_repo():
    try:
        # Lấy thông tin từ Streamlit Secrets
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        
        auth = Auth.Token(token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)
        return repo
    except Exception as e:
        st.error(f"Lỗi kết nối GitHub: {str(e)}\nVui lòng kiểm tra lại cấu hình GITHUB_TOKEN và REPO_NAME trong Secrets.")
        return None

def push_file_to_github(local_file_path, github_file_path, commit_message):
    """
    Đọc file từ local_file_path và push (commit) lên github_file_path trên repo.
    """
    repo = get_github_repo()
    if not repo:
        return False
        
    try:
        with open(local_file_path, "rb") as file:
            content = file.read()
            
        # Kiểm tra xem file đã tồn tại trên GitHub chưa
        try:
            contents = repo.get_contents(github_file_path)
            # File đã tồn tại -> Update
            repo.update_file(
                contents.path,
                commit_message,
                content,
                contents.sha,
                branch="main" # Có thể đổi nếu branch của bạn là master
            )
        except Exception:
            # File chưa tồn tại -> Create
            repo.create_file(
                github_file_path,
                commit_message,
                content,
                branch="main"
            )
        return True
    except Exception as e:
        st.error(f"Lỗi khi đồng bộ lên GitHub: {str(e)}")
        return False
