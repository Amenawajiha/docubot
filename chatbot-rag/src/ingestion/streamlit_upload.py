"""
Document upload section component.
Handles file upload and displays upload status.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
from src.utils.config_loader import get_config

def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def log_upload_to_file(file_name: str, status: str, file_size: int = None, error_msg: str = None):
    """
    Log upload status to a text file.
    
    Args:
        file_name: Name of the uploaded document
        status: "SUCCESS" or "FAILED"
        file_size: File size in bytes (optional)
        error_msg: Error message if failed (optional)
    """
    log_file = Path(get_config("upload.log_file"))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if status == "success":
        file_size_display = format_file_size(file_size) if file_size else "N/A"
        log_entry = f"[{timestamp}] SUCCESS: {file_name} | Size: {file_size_display}\n"
    else: 
        log_entry = f"[{timestamp}] FAILED: {file_name} - Error: {error_msg}\n"

    existing_lines = []
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    filtered_lines = [
        line for line in existing_lines
        if file_name not in line
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(filtered_lines)
        f.write(log_entry)

def display_upload_section(loader):
    """
    Display document upload section.
    
    Args:
        loader: QdrantLoader instance
    """
    st.markdown("Upload Document")
    st.markdown("---")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a .docx file",
        type=['docx', 'pdf', 'txt', 'md', 'xlsx', 'pptx', 'csv', 'epub', 'png', 'jpg', 'jpeg', 'webp', 'tiff', 'bmp'],
        accept_multiple_files=False,
        help="Upload a document to add to the knowledge base",
        key="docx_uploader"
    )
    
    if uploaded_file is not None:
        # Display file info
        file_size = len(uploaded_file.getvalue())
        st.info(f"📄 **File:** {uploaded_file.name} ({format_file_size(file_size)})")
        
        # Upload button
        if st.button("Process and Upload", type="secondary", use_container_width=True):
            try:
                # Show processing status
                with st.status("Processing document...", expanded=True) as status:
                    
                    file_bytes = uploaded_file.getvalue()
                    result = loader.process_document(file_bytes, uploaded_file.name)
                    
                    if result["status"] == "error":
                        raise RuntimeError(result.get('error', 'Unknown error'))
                    
                    status.update(label="Upload complete!", state="complete", expanded=False)

                log_upload_to_file(uploaded_file.name, "success", file_size=file_size)

                if result.get("was_replaced", False):                    
                    st.warning(                                          
                        f"**Replaced existing document:** {uploaded_file.name}\n\n"
                        f"- Old chunks: {result.get('old_chunk_count', 0)}\n"
                        f"- New chunks: {result['chunks_created']}"
                    )
                else:                                                    
                    st.success(f"Successfully uploaded **{uploaded_file.name}**")


                # Force page refresh to update stats
                st.rerun()
                
            except Exception as e:
                st.error(f"Error uploading document: {str(e)}")

                log_upload_to_file(uploaded_file.name, "failed", error_msg=str(e))

    
    else:
        st.info("Upload a .docx file to get started")