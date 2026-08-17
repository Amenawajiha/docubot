"""
Collection statistics display component.
Shows total documents and chunks in the Qdrant collection.
"""

import streamlit as st
from typing import Dict, Any


def display_collection_stats(stats: Dict[str, Any]):
    """
    Display collection statistics in a nice format.
    
    Args:
        stats: Dictionary with collection statistics
    """
    st.markdown("Collection Statistics")
    st.markdown("---")
    
    # Check for errors
    if "error" in stats:
        st.error(f"Error fetching statistics: {stats['error']}")
        return
    
    unique_documents = stats.get("unique_documents") or 0
    total_chunks = stats.get("total_chunks") or 0
    connection_type = stats.get("connection_type") or "Unknown"
    
    # Create three columns for stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Documents",
            value=unique_documents,
            delta=None
        )
    
    with col2:
        st.metric(
            label="Total Chunks",
            value=total_chunks,
            delta=None
        )
    
    with col3:
        st.metric(
            label="Connection",
            value=connection_type,
            delta=None
        )
    
    st.markdown("---")