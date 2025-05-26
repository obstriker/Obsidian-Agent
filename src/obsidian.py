import os
import argparse
from dotenv import load_dotenv
from datetime import date

from agno.agent import Agent
from tools.git_auto_sync import GitAutoSync
# from agno.models.openai import OpenAIChat
# from agno.memory.memory import Memory
# from agno.storage.agent.sqlite import SqliteAgentStorage
# from agno.memory.db.sqlite import SqliteMemoryDb
# import re
# import glob
# import json
# import datetime
import tools.tools as tools
from tools.tools import note_utils, tag_utils
from prompts import *
from workflows.obsidian_workflow import ObsidianWorkflow
# from watchdog.vault_watcher import start_vault_sync_thread, init_knowledge_base
from tools.vault_embedder import *
# from watchdog.vault_watcher import *

## Improve tools 
## Embed my vault at first? how would that update?
#### Embed all files and save them with hash, each unmatched hash will be embedded again.
## Create file tree as context?
## implement get_daily_note
## return in classes (note class for example)
## Note(name,tags,reference, content, etc..)
## Save insights or memories to better query the vault
## periodic pull and push to and from obsidian
## add datetime to prompt
## add periodic git push to obsidian (commit push)

# === Load API Key from .env ===
load_dotenv()
# API_KEY = os.setenv("OPENAI_API_KEY")

# g_vault_path = os.getenv("VAULT_PATH")
# daily_path = os.path.join(g_vault_path, "Daily")

# tool: move file to (goals)
# tool: get_all_tags - used for search, overview of topic
# improve searching in the vault - especially cross languages

# === Set up Memory V2 ===
# memory_db_path = os.path.join(g_vault_path, ".ai-memory.db")
# memory_db = SqliteMemoryDb(table_name="memory", db_file=memory_db_path)
# memory = Memory(db=memory_db)

# vector_db = LanceDb(
# uri="my_vault/tmp/lancedb",
# table_name="vault_docs",
# search_type=SearchType.hybrid,
# embedder=OpenAIEmbedder()
# )

# memory_db_path = os.path.join(g_vault_path, ".ai-memory.db")
# memory_db = SqliteMemoryDb(table_name="memory", db_file=memory_db_path)
# memory = Memory(db=memory_db)

# setup workflow, run agent, setup tools, run threads, 

# Create class to orchestrate multiple workflows and export one agent for wwbot?

import threading

def setup_workflow(vault_path):
    note_utils.vault_path = vault_path
    tag_utils.vault_path = vault_path
    note_utils.daily_path = os.path.join(vault_path, "Daily", "Journal")

    assitant_path = os.path.join(vault_path, ".assistant")
    if not os.path.exists(assitant_path):
        os.makedirs(assitant_path)

    # === Initialize Workflow ===
    print("Starting vault syncing...")
    obsidian_workflow = ObsidianWorkflow(vault_path)
    obsidian_workflow.sync_vault()

    # Git syncing
    print("Starting git syncing...")
    git = GitAutoSync(vault_path)
    git_thread = threading.Thread(target=git.run)
    print("Starting Git sync thread...")
    git_thread.start()
    print("Git sync thread started.")

    return obsidian_workflow

def create_agent(vault_path):
    obsidian_workflow = setup_workflow(vault_path)
    return obsidian_workflow.main_agent


# === CLI Entrypoint ===
def main():
    parser = argparse.ArgumentParser(description="Query your Obsidian vault using AI")
    parser.add_argument("--vault", required=True, help="Path to your Obsidian vault folder")
    parser.add_argument("--query", type=str, help="Natural language query")
    parser.add_argument("--search", type=str, help="Raw search: content, tag:#tagname, or file:<title>")
    args = parser.parse_args()

    if args.vault:
        vault_path = os.path.expanduser(args.vault)
    else:
        print("❌ Vault path is required. Please provide --vault argument.")
        return

    if not os.path.isdir(vault_path):
        print(f"❌ Vault path '{vault_path}' does not exist.")
        return

    # === Initialize Workflow ===
    obsidian_workflow = setup_workflow(vault_path)

    # === Run Agent ===
    if args.query:
        obsidian_workflow.sync_vault()

        # obsidian_workflow.main_agent.cli_app(args.query)
    elif args.search:
        if args.search.startswith("tag:#"):
            tag = args.search.replace("tag:#", "")
            result = obsidian_workflow.run(f"Search for notes with tag #{tag}")
        elif args.search.startswith("file:"):
            name = args.search.replace("file:", "")
            result = obsidian_workflow.run(f"Search for notes with file name containing '{name}'")
        else:
            result = obsidian_workflow.run(f"Search inside notes for '{args.search}'")
    else:
        result = "Please provide a query or search argument"
    print("\n🤖 Agent Response:\n")
    if 'result' in locals():
        print(result.content)
    else:
        print("No result to display.")

if __name__ == "__main__":
    main()

def signal_handler(sig, frame):
    print("Exiting gracefully...")
    sys.exit(0)
