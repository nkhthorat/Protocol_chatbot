from logger import logger
from pathlib import Path


def _format_source(doc):
    metadata = doc.metadata or {}
    raw_source = metadata.get("source") or metadata.get("file_path") or metadata.get("filename") or ""
    page = metadata.get("page")
    score = metadata.get("score")
    text = metadata.get("text") or doc.page_content or ""

    source_name = Path(raw_source).name if raw_source else "Uploaded document"
    page_number = page + 1 if isinstance(page, int) else page
    snippet = " ".join(text.split())[:300]

    return {
        "document": source_name,
        "page": page_number,
        "score": score,
        "snippet": snippet,
    }


def _dedupe_sources(source_documents):
    sources = []
    seen = set()

    for doc in source_documents:
        source = _format_source(doc)
        key = (source["document"], source["page"], source["snippet"])
        if key in seen:
            continue

        seen.add(key)
        sources.append(source)

    return sources

def query_chain(chain,user_input:str):
    try:
        logger.debug(f"Running chain for input: {user_input}")
        result=chain({"query":user_input})
        response={
            "response":result["result"],
            "sources": _dedupe_sources(result["source_documents"])
        }
        logger.debug(f"Chain response:{response}")
        return response
    except Exception as e:
        logger.exception("Error on query chain")
        raise
