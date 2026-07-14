# Protocol Chatbot

Protocol Chatbot is a Retrieval-Augmented Generation (RAG) application that lets users upload clinical or medical PDF documents and ask questions about their contents.

The app has two main parts:

- **Streamlit frontend**: provides the user interface for uploading PDFs and chatting with the assistant.
- **FastAPI backend**: processes documents, stores searchable embeddings, retrieves relevant context, and generates answers.

## What It Does

1. A user uploads one or more PDF documents from the Streamlit sidebar.
2. The backend saves the PDFs, extracts their text, splits the text into smaller chunks, and creates embeddings for each chunk.
3. Those embeddings are stored in Pinecone, which acts as the vector database.
4. When the user asks a question, the backend embeds the question and searches Pinecone for the most relevant document chunks.
5. The retrieved chunks are passed into a LangChain RetrievalQA chain.
6. A Groq-hosted LLM generates an answer using only the retrieved document context.
7. The answer is returned to the Streamlit chat interface.

## Tech Stack

- **Python**: main programming language.
- **Streamlit**: frontend chat and PDF upload interface.
- **FastAPI**: backend API server.
- **LangChain**: retrieval and question-answering workflow.
- **Google Gemini Embeddings**: converts PDF chunks and user questions into vectors.
- **Pinecone**: vector database for semantic search.
- **Groq / ChatGroq**: LLM provider for generating answers.
- **PyPDFLoader**: loads and extracts PDF text.
- **Uvicorn**: runs the FastAPI server.
- **uv**: Python environment and dependency management.

## Project Structure

```text
Protocol_chatbot/
  client/
    app.py                    # Streamlit app entry point
    config.py                 # Backend API URL
    components/
      upload.py               # PDF upload UI
      chatUI.py               # Chat interface
      history_download.py     # Chat history download helper
    utils/
      api.py                  # Calls backend endpoints

  server/
    main.py                   # FastAPI app entry point
    routes/
      upload_pdfs.py          # Upload PDF endpoint
      ask_question.py         # Question-answering endpoint
    modules/
      load_vectorstore.py     # PDF processing and Pinecone upload
      llm.py                  # LLM and RetrievalQA chain setup
      query_handlers.py       # Runs the QA chain
      pdf_handlers.py         # File-saving helper
    middlewares/
      exception_handlers.py   # Global error handling
    logger.py                 # Logging setup
```

## How The App Works

### Upload Flow

The user uploads PDFs in the Streamlit frontend. The frontend sends those files to the backend endpoint:

```text
POST /upload_pdfs/
```

The backend then:

- saves the uploaded PDFs;
- loads the PDF text;
- splits the text into chunks;
- creates embeddings using Google Gemini;
- stores the vectors and chunk text in Pinecone.

### Chat Flow

The user types a question in the Streamlit chat box. The frontend sends the question to:

```text
POST /ask/
```

The backend then:

- embeds the user question;
- searches Pinecone for the most relevant PDF chunks;
- creates a temporary retriever from those chunks;
- passes the retrieved context into the LangChain QA chain;
- uses Groq to generate a grounded response;
- returns the answer to the frontend.

## Environment Variables

Create a `server/.env` file with:

```env
GOOGLE_API_KEY=your_google_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=medicalindex
GROQ_API_KEY=your_groq_api_key
```

The current ingestion code uses the Pinecone index name `medicalindex`, so `PINECONE_INDEX_NAME` should match that unless the code is updated.

## Running Locally

Create and activate a Python environment:

```bash
uv venv --python 3.11
source .venv/bin/activate
```

Install backend dependencies:

```bash
uv pip install -r server/requirements.txt
```

Install frontend dependencies:

```bash
uv pip install -r client/requirements.txt
```

Start the backend:

```bash
cd server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```bash
streamlit run client/app.py
```

The Streamlit app connects to the backend URL defined in `client/config.py`:

```python
API_URL = "http://127.0.0.1:8000"
```

## API Endpoints

### Upload PDFs

```text
POST /upload_pdfs/
```

Accepts PDF files using the form field `files`.

### Ask A Question

```text
POST /ask/
```

Accepts a form field named `question` and returns an answer generated from the retrieved document context.

## Summary

Protocol Chatbot is a document-question-answering system for clinical PDFs. It combines a Streamlit interface, FastAPI backend, LangChain retrieval pipeline, Gemini embeddings, Pinecone vector search, and Groq LLM responses to help users ask questions over uploaded documents.
