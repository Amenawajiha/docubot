---
applyTo: "**/*"
# This file is ONLY for the coding agent.
excludeAgent: ["code-review"]
---

# Coding Agent Instructions

Welcome to the `chatbot-rag` project! This document provides essential guidelines for AI coding agents to be productive in this codebase. Follow these instructions to understand the architecture, workflows, and conventions of the project.

## Project Overview

`chatbot-rag` is a chatbot application built using a combination of Python for the backend and React for the frontend. The project is structured into distinct modules for handling various functionalities, such as:

- **Backend**: Located in the `src/` directory, it includes modules for authentication, chat management, ingestion, LLM orchestration, and vector database interactions.
- **Frontend**: Located in the `frontend-react/` directory, it is a React-based application for the user interface.
- **Streamlit Apps**: Several Streamlit-based tools for document processing and statistics visualization are in the `src/ingestion/` directory.

## Configuration Files

- RAG and Ingestion pipeline settings: stored in `#file:config.yaml` (all pipeline parameters, retrieval/rerank settings, chunking, vector DB endpoints, etc.).
- Sensitive values (API keys, secrets, DB passwords): stored in `#file:.env`. Use env vars or a secret manager for production.

## Key Workflows

### Setting Up the Environment
1. Activate the virtual environment:
   ```bash
   source /home/raviteja/Documents/chatbot-rag/.venv/bin/activate
   export PYTHONPATH='/home/raviteja/Documents/chatbot-rag'
   ```
2. Install dependencies:
   ```bash
   uv sync
   ```

### Running the Application
- Start the backend:
  ```bash
  uv run src/main.py
  ```
- Start the frontend:
  ```bash
  streamlit run frontend.py
  ```

### Testing
- Tests are organized by module in the `tests/` directory. Use `pytest` to run tests:
  ```bash
  pytest
  ```

#### Coverage Testing
- Option 1: Cover just the single module (recommended for focused testing). Example:
  ```bash
  pytest tests/vector/test_vector_retriever.py --cov=src.vector.vector_retriever --cov-report=term-missing
  ```

- Option 2: Cover the entire `src` directory (recommended for comprehensive coverage). Example:
  ```bash
  pytest tests/vector/test_vector_retriever.py --cov=src --cov-report=term-missing
  ```

## Architecture and Patterns

### Backend
- **Service-Oriented Design**: Each major functionality is encapsulated in its own module (e.g., `auth/`, `chat/`, `ingestion/`, `llm/`, `vector/`).
- **Database Interaction**: Vector databases like Qdrant and Chroma are used for storing embeddings. See `vector/` for database client implementations.
- **LLM Integration**: The `llm/` module handles interactions with large language models, including prompt building and orchestration.

### Frontend
- **React Components**: The `frontend-react/src/` directory contains reusable components, such as the `chat_widget/`.
- **Configuration**: Frontend configurations are managed in `frontend-react/src/config/`.

### Streamlit Tools
- Streamlit apps for document ingestion and statistics are in `ingestion/`.

## Conventions
- **Logging**: Use the `log_helper.py` utility in `utils/` for consistent logging.
- **Singletons**: The `singleton_meta.py` in `utils/` provides a metaclass for singleton patterns.
- **Database Context Management**: Use `db_enter_exit_mixin.py` for managing database connections.

## External Dependencies
- **Reranker Model**: Download the model using:
  ```bash
  uv run hf download BAAI/bge-reranker-v2-m3
  ```
- **Vector Databases**: Ensure Qdrant is set up for vector storage.

## Virtual Environment Details

- The virtual environment is located at `/home/raviteja/Documents/chatbot-rag/.venv`.
- Python version: `3.14.2`.
- The environment is managed using `uv`, not `pip`. Use the following commands to manage dependencies:
  - Add a package: `uv add <package-name>`
  - Remove a package: `uv remove <package-name>`
