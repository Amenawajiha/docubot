import streamlit as st
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.log_helper import create_log_file
from src.ingestion.qdrant_loader import QdrantLoader
from src.ingestion.streamlit_doc_queue import display_document_queue
from src.ingestion.streamlit_stats import display_collection_stats
from src.ingestion.streamlit_upload import display_upload_section
from src.utils.config_loader import get_config

# Page configuration
st.set_page_config(
    page_title=get_config("streamlit.page_title", "Ingestion Pipeline"),
    page_icon=get_config("streamlit.page_icon", "📚"),
    layout=get_config("streamlit.layout", "wide"),
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def get_qdrant_loader():
    """Initialize and cache QdrantLoader."""
    return QdrantLoader()


def main():
    st.title("Ingestion Pipeline")
    st.markdown("Upload documents to the knowledge base.")
    st.markdown("")

    try:
        loader = get_qdrant_loader()

        # Get stats directly from loader
        stats = loader.get_collection_stats()

        
        # Count unique documents
        unique_docs = loader.get_unique_document_count()

        stats_display = {
            "total_chunks": stats["total_documents"],
            "unique_documents": unique_docs,
            "connection_type": (
                "Local (Docker)"
                if "localhost" in os.getenv("QDRANT_URL", "")
                else "Cloud"
            ),
        }

        display_collection_stats(stats_display)

        st.markdown("")

        # Pass loader and config to upload section
        display_upload_section(loader)

        # Pass loader to document queue for delete functionality
        display_document_queue(qdrant_loader=loader)

    except Exception as e:
        st.error(f"Error initializing application: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    create_log_file("Ingestion")
    main()
