"""
Vault Embedder for Obsidian Assistant

Embeds documents from an Obsidian vault into Agno + LanceDB.
Supports incremental updates and monitoring mode.
"""

import os, glob, time, argparse
from typing import List, Optional
from dotenv import load_dotenv
import json

from agno.document import Document
from agno.embedder.openai import OpenAIEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.knowledge.document import DocumentKnowledgeBase

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

def get_markdown_files(path: str) -> List[str]:
    return glob.glob(os.path.join(path, "**/*.md"), recursive=True)

def build_documents(path: str) -> List[Document]:
    abs_path = os.path.abspath(path)
    documents = []
    for file_path in get_markdown_files(abs_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            rel_path = os.path.relpath(file_path, abs_path)
            documents.append(
                Document(
                    name=rel_path,
                    content=content,
                    meta_data={"file_path": rel_path, "timestamp": time.time()}
                )
            )
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
    return documents

import json

def load_index(path): 
    try: return json.load(open(os.path.join(path, ".vault_index.json")))
    except: return {}

def save_index(path, index): 
    json.dump(index, open(os.path.join(path, ".vault_index.json"), "w"), indent=2)

def get_modified_docs(path, index): 
    docs, base = [], os.path.abspath(path)
    for fp in get_markdown_files(base):
        rel = os.path.relpath(fp, base)
        mtime = os.path.getmtime(fp)
        if rel not in index or mtime > index[rel]:
            try:
                content = open(fp, encoding="utf-8").read()
                docs.append(Document(
                    id=rel,  # Ensures uniqueness across versions
                    name=rel,
                    content=content,
                    meta_data={"file_path": rel, "timestamp": time.time()}
                ))
                index[rel] = mtime
            except Exception as e:
                print(f"⚠️ {rel}: {e}")
    return docs

def embed_vault(path: str, vector_db: Optional[LanceDb] = None, recreate: bool = False) -> DocumentKnowledgeBase:
    abs_path = os.path.abspath(path)
    db_path = os.path.join(abs_path, "tmp/lancedb")

    if not vector_db:
        vector_db = LanceDb(
            uri=db_path,
            table_name="vault_docs",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder()
        )

    documents = build_documents(abs_path)
    print(f"📄 Found {len(documents)} markdown files.")

    kb = DocumentKnowledgeBase(
        documents=documents,
        vector_db=vector_db,
        skip_existing=True
    )
    kb.load(recreate=recreate)
    return kb

def add_document(document: Document, kb: DocumentKnowledgeBase):
    """Upsert a single document: delete existing by ID, then insert."""
    if not document.id:
        raise ValueError("Document must have an 'id' field for upsert behavior.")
    
    # kb.vector_db.delete(ids=[document.id])  # Manual upsert: delete first
    kb.load_documents([document])
    print(f"🔁 Upserted: {document.name}")


def monitor_vault(path: str, interval: int = 300):
    abs_path = os.path.abspath(path)
    db = LanceDb(
        uri=os.path.join(abs_path, "tmp/lancedb"),
        table_name="vault_docs",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder()
    )
    kb = DocumentKnowledgeBase(documents=[], vector_db=db, skip_existing=True)
    index = load_index(abs_path)

    try:
        while True:
            print(f"\n🔄 Scanning vault: {abs_path}")
            docs = get_modified_docs(abs_path, index)

            if docs:
                for doc in docs:
                    add_document(doc, kb)  # uses delete + insert for upsert
                save_index(abs_path, index)
                print(f"🔁 Upserted {len(docs)} modified docs")
            else:
                print("🟢 No changes detected")

            print(f"⏳ Sleeping {interval}s...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("🛑 Monitoring stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed Obsidian vault with Agno + LanceDB")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    parser.add_argument("--monitor", action="store_true", help="Enable monitoring mode")
    parser.add_argument("--interval", type=int, default=300, help="Monitoring interval (seconds)")
    parser.add_argument("--recreate", action="store_true", help="Recreate vector DB")
    args = parser.parse_args()

    vault = os.path.expanduser(args.vault)
    if not os.path.isdir(vault):
        print(f"❌ Invalid vault path: {vault}")
    else:
        kb = embed_vault(vault, recreate=args.recreate)
        print("✅ Vault embedded successfully.")
        if args.monitor:
            monitor_vault(vault, args.interval)
