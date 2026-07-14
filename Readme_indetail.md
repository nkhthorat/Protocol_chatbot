# Protocol Chatbot

Protocol Chatbot is a Retrieval-Augmented Generation (RAG) application for asking questions about uploaded clinical or medical PDF documents. It has two main parts:

- A FastAPI backend in `server/` that stores PDF chunks in Pinecone and answers questions using LangChain, Google Gemini embeddings, and Groq-hosted chat models.
- A Streamlit frontend in `client/` that lets a user upload PDFs, ask questions, and view answers.

The main user workflow is:

1. Start the FastAPI backend.
2. Start the Streamlit frontend.
3. Upload one or more PDF files from the Streamlit sidebar.
4. The backend saves each PDF, extracts text, chunks it, embeds each chunk, and upserts those vectors into Pinecone.
5. Ask a question in the Streamlit chat box.
6. The backend embeds the question, retrieves the most similar Pinecone chunks, sends those chunks to the LLM, and returns an answer plus source metadata.

## High-Level Architecture

```text
Streamlit UI
  client/app.py
    |
    | renders
    v
  client/components/upload.py --------\
  client/components/chatUI.py ---------+--> client/utils/api.py
  client/components/history_download.py/          |
                                                 | HTTP
                                                 v
FastAPI backend
  server/main.py
    |
    | includes routers
    v
  server/routes/upload_pdfs.py -----> server/modules/load_vectorstore.py
  server/routes/ask_question.py ----> server/modules/llm.py
                                  \-> server/modules/query_handlers.py

External services
  Google Gemini embeddings
  Pinecone vector database
  Groq chat model
```

## Runtime Data Flow

### 1. PDF Upload Flow

The upload flow begins in the Streamlit sidebar.

1. `client/app.py` calls `render_uploader()` from `client/components/upload.py`.
2. `client/components/upload.py` displays a multi-file PDF uploader.
3. When the user clicks `Upload DB`, it calls `upload_pdfs_api(uploaded_files)` from `client/utils/api.py`.
4. `client/utils/api.py` sends a `POST` request to `http://127.0.0.1:8000/upload_pdfs/`.
5. `server/main.py` has already registered the upload router from `server/routes/upload_pdfs.py`.
6. `server/routes/upload_pdfs.py` receives the uploaded files and calls `load_vectorstore(files)`.
7. `server/modules/load_vectorstore.py`:
   - saves each uploaded file into `./uploaded_docs`;
   - loads the PDF pages with `PyPDFLoader`;
   - splits documents into chunks with `RecursiveCharacterTextSplitter`;
   - embeds each chunk with `GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")`;
   - adds the chunk text into Pinecone metadata under the key `text`;
   - creates vector IDs using the PDF filename stem and chunk number;
   - upserts all vectors into the Pinecone index.
8. `server/routes/upload_pdfs.py` returns `{"messages": "Files processed and vectorstore updated"}` to the frontend.
9. The Streamlit sidebar shows either success or error status.

Important detail: `server/modules/pdf_handlers.py` also contains a `save_uploaded_files()` helper, but the current upload route does not call it. File saving is currently done directly inside `server/modules/load_vectorstore.py`.

### 2. Question Answering Flow

The chat flow begins in the Streamlit chat input.

1. `client/app.py` calls `render_chat()` from `client/components/chatUI.py`.
2. `client/components/chatUI.py` initializes `st.session_state.messages` if needed, renders previous messages, and waits for `st.chat_input()`.
3. When the user submits a question, `chatUI.py` calls `ask_question_function(user_input)` from `client/utils/api.py`.
4. `client/utils/api.py` sends a form-encoded `POST` request to `http://127.0.0.1:8000/ask/` with the form field `question`.
5. `server/main.py` has already registered the ask router from `server/routes/ask_question.py`.
6. `server/routes/ask_question.py`:
   - logs the user question;
   - connects to Pinecone using `PINECONE_API_KEY`;
   - opens the Pinecone index named by `PINECONE_INDEX_NAME`;
   - embeds the question with `GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")`;
   - queries Pinecone for the top 3 closest vectors;
   - converts those matches into LangChain `Document` objects using `match["metadata"]["text"]` as `page_content`;
   - wraps those documents in a small local `SimpleRetriever` class.
7. `server/routes/ask_question.py` passes the retriever to `get_llm_chain()` in `server/modules/llm.py`.
8. `server/modules/llm.py`:
   - creates a `ChatGroq` model using `GROQ_API_KEY`;
   - uses model `openai/gpt-oss-120b`;
   - builds a prompt that instructs the assistant to answer only from context and avoid medical advice or diagnosis;
   - returns a LangChain `RetrievalQA` chain.
9. `server/routes/ask_question.py` calls `query_chain(chain, question)` from `server/modules/query_handlers.py`.
10. `server/modules/query_handlers.py` executes the chain and returns a response shaped like:

```json
{
  "response": "answer text",
  "sources": ["source metadata values"]
}
```

11. `client/components/chatUI.py` renders the answer in the Streamlit chat and appends the assistant response to `st.session_state.messages`.

## File-by-File Guide

### Root Files

| File | Purpose | Connected to |
| --- | --- | --- |
| `README.md` | Main project documentation. | Human-facing guide for the whole repo. |
| `pyproject.toml` | Root Python project metadata and `uv` workspace configuration. It declares `server` as a workspace member. | `server/pyproject.toml`, `uv.lock`. |
| `uv.lock` | Lockfile generated by `uv`. | Used by `uv` for reproducible dependency resolution. |
| `main.py` | Placeholder root script. Running it prints `Hello from protocol-chatbot!`. | Not connected to the FastAPI or Streamlit runtime. |
| `agent.py` | Placeholder script that imports `openai` and `OpenAI`. | Not currently used by the app. |

### Client Files

| File | Purpose | Connected to |
| --- | --- | --- |
| `client/app.py` | Streamlit entry point. Sets page title/layout, renders the app title, then renders upload, chat, and history components. | Imports `render_uploader`, `render_chat`, `render_history_download`. |
| `client/config.py` | Stores backend base URL as `API_URL = "http://127.0.0.1:8000"`. | Imported by `client/utils/api.py`. |
| `client/utils/api.py` | HTTP client layer for the frontend. Sends uploaded PDFs to `/upload_pdfs/` and questions to `/ask/`. | Used by `client/components/upload.py` and `client/components/chatUI.py`; depends on `client/config.py`. |
| `client/components/upload.py` | Sidebar PDF upload UI. Converts Streamlit uploaded files into a request through `upload_pdfs_api()`. | Calls `client/utils/api.py`; targets `server/routes/upload_pdfs.py`. |
| `client/components/chatUI.py` | Main chat UI. Stores messages in Streamlit session state, sends questions to backend, renders answers and source values. | Calls `client/utils/api.py`; targets `server/routes/ask_question.py`. |
| `client/components/history_download.py` | Intended to let users download chat history as `chat_history.txt`. | Reads `st.session_state.messages`. Currently checks `st.session_state.get("message")`, singular, while the chat uses `messages`, plural. Because of that mismatch, the download button may not appear. |
| `client/requirements.txt` | Client dependency list. | Used to install Streamlit and Requests. |

### Server Files

| File | Purpose | Connected to |
| --- | --- | --- |
| `server/main.py` | FastAPI entry point. Creates the app, enables CORS, registers exception middleware, and includes upload/ask routers. | Imports `catch_exception_middleware`, `upload_router`, `ask_router`. Run with Uvicorn. |
| `server/routes/upload_pdfs.py` | Defines `POST /upload_pdfs/`. Accepts multiple files and sends them to vector indexing. | Calls `modules.load_vectorstore.load_vectorstore`; logs through `logger`. |
| `server/routes/ask_question.py` | Defines `POST /ask/`. Embeds a user question, queries Pinecone, wraps matches as documents, builds an LLM chain, and returns the answer. | Calls `modules.llm.get_llm_chain`, `modules.query_handlers.query_chain`, Pinecone, and Gemini embeddings. |
| `server/modules/load_vectorstore.py` | Main ingestion/indexing module. Loads environment variables, initializes Pinecone, creates the index if missing, saves uploaded PDFs, loads PDF text, splits chunks, embeds chunks, and upserts vectors. | Called by `server/routes/upload_pdfs.py`; uses Pinecone, Gemini embeddings, PyPDFLoader, and text splitters. |
| `server/modules/llm.py` | LLM chain factory. Creates the Groq chat model, prompt template, and LangChain `RetrievalQA` chain. | Called by `server/routes/ask_question.py`. |
| `server/modules/query_handlers.py` | Thin wrapper around LangChain chain execution. Converts chain output into the API response shape. | Called by `server/routes/ask_question.py`; uses `logger`. |
| `server/modules/pdf_handlers.py` | Utility for saving uploaded files into `./uploaded_docs`. | Not currently used by the active upload route. Similar behavior exists inside `load_vectorstore.py`. |
| `server/middlewares/exception_handlers.py` | Global FastAPI middleware for uncaught exceptions. Logs the error and returns a JSON 500 response. | Registered in `server/main.py`. |
| `server/logger.py` | Configures a Python logger named `Clinical Chatbot`. | Imported by routes, middleware, and query handlers. It currently logs several startup test messages on import. |
| `server/test.py` | Minimal standalone FastAPI test app with `GET /` returning `{"message": "HELLO"}`. | Not connected to the main backend. |
| `server/test_retrieval.py` | Manual retrieval diagnostic script. Embeds a hardcoded query, queries Pinecone, and prints top matches. | Uses the same Pinecone and Gemini services as the main app. |
| `server/requirements.txt` | Backend dependency list. | Used to install FastAPI, LangChain, Pinecone, Gemini embeddings, Groq, PDF parsing, and utilities. |
| `server/pyproject.toml` | Server package metadata. | Part of the root `uv` workspace. |
| `server/README.md` | Empty placeholder README. | Not currently used for documentation. |
| `server/uploaded_docs/` | Local storage for uploaded PDFs. | Written by `load_vectorstore.py`; read by `PyPDFLoader`. |
| `server/list/` | Appears to be a local Python virtual environment. | Not part of the application source code. |

### Postman Files

| File | Purpose | Connected to |
| --- | --- | --- |
| `postman/collections/Clinical/upload_pdfs.request.yaml` | Postman request for testing `POST /upload_pdfs/` with a PDF file. | Targets the FastAPI upload route. |
| `postman/collections/Clinical/ask.request.yaml` | Currently also points to `POST /upload_pdfs/`, despite its filename suggesting it should test `/ask/`. | Likely needs correction if you want a Postman ask request. |
| `postman/collections/Protocol chatbot/New Request.request.yaml` | Empty placeholder GET request. | Not connected to the active API. |
| `postman/globals/workspace.globals.yaml` | Empty Postman globals file. | Not currently used. |

## Environment Variables

Create the backend environment file at `server/.env` or otherwise export these variables before running the backend:

```env
GOOGLE_API_KEY=your_google_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=medicalindex
GROQ_API_KEY=your_groq_api_key
```

Current code detail: `server/modules/load_vectorstore.py` uses the hardcoded index name `medicalindex`, while `server/routes/ask_question.py` reads the index name from `PINECONE_INDEX_NAME`. For upload and retrieval to talk to the same Pinecone index, set `PINECONE_INDEX_NAME=medicalindex` unless you also update the hardcoded value in `load_vectorstore.py`.

## Running Locally

The project uses Python 3.11 in the existing setup notes.

### 1. Create and activate a virtual environment

From the project root:

```bash
uv venv --python 3.11
source .venv/bin/activate
```

If you need the Homebrew Python 3.11 path used in the original notes:

```bash
rm -rf .venv
uv venv --python /opt/homebrew/bin/python3.11
source .venv/bin/activate
python --version
```

### 2. Install backend dependencies

```bash
uv pip install --no-cache-dir -r server/requirements.txt
```

If `cryptography` causes local install issues, the previous setup notes used:

```bash
pip uninstall cryptography -y
uv pip install --no-binary cryptography cryptography
python -c "import cryptography; print('OK')"
```

### 3. Install client dependencies

```bash
uv pip install -r client/requirements.txt
```

### 4. Start the backend

Run from the `server/` directory so relative paths such as `./uploaded_docs` point to `server/uploaded_docs`:

```bash
cd server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend base URL should now be:

```text
http://127.0.0.1:8000
```

### 5. Start the frontend

In a second terminal from the project root:

```bash
streamlit run client/app.py
```

The frontend reads its API URL from `client/config.py`.

## API Reference

### `POST /upload_pdfs/`

Accepts one or more PDF files as multipart form data using the field name `files`.

Example with `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/upload_pdfs/" \
  -F "files=@/path/to/document.pdf"
```

Successful response:

```json
{
  "messages": "Files processed and vectorstore updated"
}
```

### `POST /ask/`

Accepts a form field named `question`.

Example with `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/ask/" \
  -F "question=What does this protocol say about eligibility?"
```

Successful response:

```json
{
  "response": "Answer generated from retrieved PDF context.",
  "sources": ["source metadata values"]
}
```

## Pinecone and Embedding Details

`server/modules/load_vectorstore.py` creates the Pinecone index if it does not already exist:

- index name: `medicalindex`
- cloud: `aws`
- region: `us-east-1`
- dimension: `3072`
- metric: `dotproduct`

The dimension is tied to the configured Gemini embedding model. If you change the embedding model, confirm the output dimension and recreate or migrate the Pinecone index if needed.

Each PDF chunk is stored with metadata copied from LangChain's PDF loader plus:

```json
{
  "text": "the chunk text"
}
```

The ask route depends on this `text` metadata field to reconstruct LangChain documents after querying Pinecone.

## Known Issues and Cleanup Notes

- `client/components/history_download.py` checks for `message`, but chat history is stored under `messages`. This likely prevents the download button from appearing.
- `server/modules/query_handlers.py` reads source metadata with `doc.metadata.get("sources", "")`. LangChain PDF metadata commonly uses fields like `source` and `page`, not `sources`, so the returned source list may contain empty strings.
- `server/modules/load_vectorstore.py` hardcodes `PINECONE_INDEX_NAME = "medicalindex"`, while `server/routes/ask_question.py` reads `PINECONE_INDEX_NAME` from the environment.
- `server/logger.py` emits debug/error/critical sample messages at import time. Those are useful while testing the logger but noisy in normal application startup.
- `server/modules/pdf_handlers.py`, root `main.py`, `agent.py`, and `server/test.py` are not connected to the main runtime path.
- `server/list/` appears to be a virtual environment and should normally not be treated as application source.
- The Postman file named `ask.request.yaml` currently points to the upload endpoint.

## Quick Connection Map

```text
client/app.py
  -> client/components/upload.py
       -> client/utils/api.py
            -> POST /upload_pdfs/
                 -> server/routes/upload_pdfs.py
                      -> server/modules/load_vectorstore.py
                           -> Pinecone
                           -> Google Gemini embeddings
                           -> server/uploaded_docs/

client/app.py
  -> client/components/chatUI.py
       -> client/utils/api.py
            -> POST /ask/
                 -> server/routes/ask_question.py
                      -> Pinecone
                      -> Google Gemini embeddings
                      -> server/modules/llm.py
                           -> Groq chat model
                      -> server/modules/query_handlers.py

server/main.py
  -> server/middlewares/exception_handlers.py
  -> server/routes/upload_pdfs.py
  -> server/routes/ask_question.py
```
