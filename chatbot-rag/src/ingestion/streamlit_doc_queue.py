"""
Document queue component.
Displays list of uploaded documents from log file.
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from src.utils.config_loader import get_config


class DocumentQueue:
    """
    Manages the document queue display.
    
    Key Concepts:
    - Reads from upload_log.txt (single source of truth)
    - Displays newest documents first
    - Handles empty states gracefully
    - Supports document deletion
    """

    def __init__(self, log_file: str = None, qdrant_loader=None):
        self.log_file = Path(log_file) if log_file else Path(get_config("upload.log_file"))
        self.qdrant_loader = qdrant_loader

    def _parse_log_line(self, line: str) -> Dict:
        """
        Parse a single log line into a structured dict.
        
        Args:
            line: Raw log line
            
        Returns:
            Dict with timestamp, status, filename, error (optional)
        """
        try:
            parts = line.strip().split('] ', 1)  
            if len(parts) != 2:
                return None
            
            timestamp_str = parts[0].replace('[', '')
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

            rest = parts[1]

            if 'SUCCESS:' in rest:
                status = "success"
                if ' | Size:' in rest:
                    file_part, size_part = rest.split(' | Size:')
                    filename = file_part.replace('SUCCESS: ', '').strip()
                    file_size_display = size_part.strip()  
                else:
                    filename = rest.replace('SUCCESS: ', '').strip()
                    file_size_display = "N/A"
            
                error = None

            elif 'FAILED:' in rest:
                status = "failed"
                file_size_display = "N/A"

                if ' - Error:' in rest:
                    parts = rest.split('FAILED: ')[1].split(' - Error:')
                    filename = parts[0].strip()
                    error = parts[1].strip() if len(parts) > 1 else "Unknown error"
                else:
                    filename = rest.replace('FAILED: ', '').strip()
                    error = "Unknown error"
            else:
                return None
            
            return {
                'timestamp': timestamp,
                'status': status,
                'filename': filename,
                'file_size': file_size_display,
                'timestamp_str': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'error': error  
            }
        
        except Exception as e:
            st.error(f"Error parsing log line: {line} - {str(e)}")
            return 
        
    def _remove_from_log(self, filename: str):
        """
        Remove all entries for a specific document from the log file.
        
        Args:
            filename: Name of the document to remove
        """
        if not self.log_file.exists():
            return
        
        # Read all lines
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out lines containing this filename
        filtered_lines = []
        for line in lines:
            parsed = self._parse_log_line(line)
            # Keep line if parsing failed OR filename doesn't match exactly
            if parsed is None or parsed['filename'] != filename:
                filtered_lines.append(line)
        
        # Write back
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
    
    def delete_document(self, filename: str) -> bool:
        """
        Delete a document from both Qdrant and the log file.
        
        Args:
            filename: Name of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from Qdrant if loader is available
            if self.qdrant_loader:
                self.qdrant_loader.delete_document_chunks(filename)
            
            # Remove from log file
            self._remove_from_log(filename)
            
            return True
            
        except Exception as e:
            st.error(f"Error deleting document: {str(e)}")
            return False
        
    def load_documents(self) -> List[Dict]:
        """
        Load all documents from log file.
        
        Returns newest first (LIFO order).
        Latest uploads appear at the top.
        """
        if not self.log_file.exists():
            return []

        documents = {}  

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = self._parse_log_line(line)
                if parsed:
                    # Keep only the latest entry for each filename
                    documents[parsed['filename']] = parsed

        doc_list = list(documents.values())
        doc_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return doc_list
    
    def display(self):
        """Display the document queue section."""
        st.markdown("---")

        show_queue = st.checkbox(
            "Show Documents in Collection",
            value=False,  
            help="View the list of uploaded documents in the knowledge base."
        )

        if show_queue:
            documents = self.load_documents()

            if not documents:
                st.info("No documents uploaded yet.")
                return
            
            st.markdown(f"### Document Queue ({len(documents)} documents)")
            st.markdown("")

            for idx, doc in enumerate(documents, 1):
                self._display_document_card(doc, idx)

    def _display_document_card(self, doc: Dict, position: int):
        """
        Display a single document card in expander format.
        
        Args:
            doc: Document dictionary with timestamp, status, filename, error
            position: Position in queue (for auto-expand first item)
        """
        # Determine status icon and text
        if doc['status'] == "success":
            icon = "✅"
        else:
            icon = "❌"

        doc_key = f"{doc['filename']}_{doc['timestamp_str'].replace(' ', '_').replace(':', '-')}"
        
        # Container for the card header with menu
        col_expand, col_menu = st.columns([0.95, 0.05])
        
        with col_menu:
            # Create a popover menu for delete action
            with st.popover("⋮", use_container_width=False):
                st.markdown("**Actions**")
                if st.button("Delete", key=f"delete_{doc_key}", use_container_width=True):
                    with st.spinner(f"Deleting {doc['filename']}..."):
                        success = self.delete_document(doc['filename'])
                        if success:
                            st.success(f"Deleted {doc['filename']}")
                            st.rerun()
                        else:
                            st.error("Failed to delete document")
        
        with col_expand:
            with st.expander(
                f"{icon} {doc['filename']}",
                expanded=(position == 1)
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**File Name:** {doc['filename']}")
                    st.markdown(f"**File Size:** {doc.get('file_size', 'N/A')}")

                with col2:
                    st.markdown(f"**Uploaded At:** {doc['timestamp_str']}")
                    
                    if doc['status'] == "success":
                        st.markdown("**Status:** Success")
                    else:
                        st.markdown("**Status:** Failed")

                # Show error details if failed
                if doc['status'] == "failed" and doc.get('error'):
                    st.markdown("---")
                    st.markdown("**Error Details:**")
                    st.code(doc['error'], language=None)
        


def display_document_queue(qdrant_loader=None):
    """Display the document queue component."""
    queue = DocumentQueue(qdrant_loader=qdrant_loader)
    queue.display()