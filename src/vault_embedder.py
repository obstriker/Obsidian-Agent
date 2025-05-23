"""
Vault Embedder for Obsidian Assistant

Embeds documents from an Obsidian vault using a pluggable vector DB.
Supports initial sync, incremental updates, and monitoring mode.
"""

import os
import glob
import time
import hashlib
import json
import threading
from typing import List, Optional, Tuple
import io
import sys

# Set stdout encoding to utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

from agno.document import Document
from agno.knowledge.document import DocumentKnowledgeBase
from agno.embedder.openai import OpenAIEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType

INDEX_FILENAME = ".vault_index.json"

class VaultEmbedder:
    def __init__(self, vault_path: str, vector_db = None, recreate: bool = False):
        self.vault_path = os.path.abspath(vault_path)
        print(f"Vault path: {self.vault_path}")
        self.db_path = os.path.join(vault_path, ".assistant")
        self.db_path = os.path.join(self.db_path, "lancedb")
        self.index = self._load_index()

        if not vector_db:
            self.vector_db = LanceDb(
                uri=self.db_path,
                table_name="vault_docs",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder()
                )

        self.kb = DocumentKnowledgeBase(documents=[], vector_db=self.vector_db, skip_existing=True)
        self.kb.load(recreate=recreate)
        print(f"Knowledge base loaded. Vector DB exists: {self.vector_db.exists()}")
        try:
            self._initial_sync(recreate=recreate)
        except Exception as e:
            print(f"Error during _initial_sync: {e}")
            raise

    # ----------------- Internal Utilities -----------------

    def _get_markdown_files(self) -> List[str]:
        return glob.glob(os.path.join(self.vault_path, "**/*.md"), recursive=True)

    def _compute_md5(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _load_index(self) -> dict:
        path = os.path.join(self.db_path, INDEX_FILENAME)
        print(f"Loading index from path: {path}")
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading index: {e}")
            raise

    def _save_index(self):
        path = os.path.join(self.db_path, INDEX_FILENAME)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.index, f, indent=2)

    def _get_modified_documents(self) -> List[Tuple[Document, Optional[str]]]:
        docs = []
        for file_path in self._get_markdown_files():
            rel_path = os.path.relpath(file_path, self.vault_path)
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read().replace("\x00", "\ufffd")
                doc_hash = self._compute_md5(content)
                prev_hash = self.index.get(rel_path)
                if prev_hash != doc_hash:
                    docs.append((
                        Document(
                            id=doc_hash,
                            name=rel_path,
                            content=content,
                            meta_data={"file_path": rel_path, "timestamp": time.time()}
                        ),
                        prev_hash
                    ))
            except Exception as e:
                print(f"⚠️ Error reading {rel_path}: {e}")
        return docs

    # ----------------- Core Methods -----------------

    def sync(self):
        updates = self._get_modified_documents()

        if not updates:
            print("✅ Vault is already in sync.")
            return

        print(f"🔁 Syncing {len(updates)} new or updated files...")
        for doc, old_id in updates:
            if old_id and old_id != doc.id:
                self.vector_db.table.delete(f"id = '{old_id}'")
            self.kb.load_documents([doc])
            self.index[doc.name] = doc.id

        self._save_index()
        print("✅ Sync complete.")

    def _initial_sync(self, recreate: bool):
        if recreate or not self.index:
            print("📭 No index or recreate=True — syncing full vault.")
            self.index = {}
        else:
            print("Using existing index.")
        self.sync()

    def query(self, query: str, top_k: int = 5):
        print(f"Querying with query: {query} and top_k: {top_k}")
        try:
            results = self.kb.search(query=query, num_documents=top_k)
            return results
            
        except Exception as e:
            print(f"Error searching for documents: {e}")
            raise

    def search_knowledge(self, query: str, top_k: int = 5):
        """Agno-style alias."""
        return self.query(query, top_k)

    def start_monitoring(self, interval: int = 300) -> threading.Thread:
        def loop():
            while True:
                print(f"\n🔄 Scanning vault: {self.vault_path}")
                self.sync()
                print(f"⏳ Sleeping for {interval} seconds...")
                time.sleep(interval)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        return thread

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Query Obsidian vault")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    parser.add_argument("--query", required=True, help="Query string")
    args = parser.parse_args()

    ve = VaultEmbedder(vault_path=args.vault)
    results = ve.query(args.query)
    for result in results:
        print(f"Document: {result.meta_data}")
