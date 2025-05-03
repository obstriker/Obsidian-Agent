import os
import argparse
from dotenv import load_dotenv
from datetime import date

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.memory.v2.memory import Memory
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.memory.db.sqlite import SqliteMemoryDb
import re
import glob
import json
import datetime
from agno.tools.website import WebsiteTools
from prompts import *

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
API_KEY = os.getenv("OPENAI_API_KEY")

g_vault_path = os.getenv("VAULT_PATH")
daily_path = os.path.join(g_vault_path, "Daily")

def create_note(note_name: str, content: str) -> str:
    """
    Creates a new note with the specified name and content.
    The filename format is assumed to be '{note_name}.md'.

    Args:
        note_name (str): The name of the note to create (without the .md extension).
        content (str): The content to write in the note.

    Returns:
        str: A message indicating success or failure.
    """
    path = os.path.join(g_vault_path, f"{note_name}.md")
    if os.path.exists(path):
        return f"Note '{note_name}' already exists."

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Note '{note_name}' created successfully."
    except Exception as e:
        return f"Error creating note '{note_name}': {str(e)}"

def append_to_note(note_name: str, content: str, marker: str = "<!-- AI -->") -> str:
    """
    Appends content to a note, or inserts at marker if exists.
    """
    path = os.path.join(g_vault_path, f"{note_name}.md")
    if not os.path.exists(path):
        return f"Note '{note_name}' not found."
    with open(path, "r+", encoding="utf-8") as f:
        text = f.read()
        if marker in text:
            text = text.replace(marker, f"{marker}\n{content}")
        else:
            text += f"\n\n{content}"
        f.seek(0)
        f.write(text)
        f.truncate()
    return f"Appended to {note_name}.md."

def search_note_file(query: str) -> str:
    """
    Hybrid search for note filenames and their content for a partial match.
    Searches both the note titles and the body text of the notes, including subfolders.
    """
    matches = []

    # Recursive search for matching filenames in all subdirectories
    for root, dirs, files in os.walk(g_vault_path):
        for f in files:
            if query.lower() in f.lower() and f.endswith(".md"):
                matches.append(os.path.relpath(os.path.join(root, f), g_vault_path))

    # Search within note contents in all Markdown files, including subdirectories
    for path in glob.glob(os.path.join(g_vault_path, "**/*.md"), recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            if query.lower() in f.read().lower():
                matches.append(os.path.relpath(path, g_vault_path))

    return "\n".join(set(matches)) if matches else "No matching note titles or content found."

def search_content(query: str) -> str:
    """
    Searches the body text of all notes for a string match.
    """
    results = []
    for path in glob.glob(f"{g_vault_path}/**/*.md", recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            if query.lower() in f.read().lower():
                results.append(os.path.relpath(path, g_vault_path))
    return "\n".join(results) if results else "No content found."

def search_by_tag(tag: str) -> str:
    """
    Finds notes that contain a given tag (e.g., #topic).
    """
    matches = []
    pattern = re.compile(rf"(#|\btag:.*\b){re.escape(tag)}\b", re.IGNORECASE)
    for path in glob.glob(f"{g_vault_path}/**/*.md", recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            if pattern.search(f.read()):
                matches.append(os.path.relpath(path, g_vault_path))
    return "\n".join(matches) if matches else f"No notes found with tag #{tag}"

def list_directory(dir_path: str) -> str:
    """
    Returns a list of files and directories in the specified path as a JSON string.
    The dir_path is relative to the g_vault_path.

    Args:
        dir_path (str): The path of the directory to list files and folders from, relative to g_vault_path.

    Returns:
        str: A JSON-formatted string containing either a list of filenames and directories or an error message.
    """
    # Construct the full path relative to g_vault_path
    full_path = os.path.join(g_vault_path, dir_path)

    try:
        # List all files and directories in the constructed full path
        entries = [
            f + '/' if os.path.isdir(os.path.join(full_path, f)) else f
            for f in os.listdir(full_path)
        ]
        if entries:
            return json.dumps({"results": entries}, ensure_ascii=False)  # Return found entries in JSON format
        else:
            return json.dumps({"results": "No files or directories found."})  # Indicate none present
    except FileNotFoundError:
        return json.dumps({"error": f"Directory '{full_path}' not found."})  # Handle directory not found
    except Exception as e:
        return json.dumps({"error": str(e)})  # Handle any other exceptions

def read_note(note_name: str) -> str:
    """
    Reads the content of a specified note and returns it formatted as JSON.
    The note filename is expected to be in the format '{note_name}.md'.

    Args:
        note_name (str): The name of the note to read (with the .md extension).

    Returns:
        str: A JSON-formatted string containing the note file name and its content
              or an error message if the note does not exist.
    """
    path = os.path.join(g_vault_path, f"{note_name}")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            note_content = f.read()
            result = {
                "file_name": f"{note_name}",
                "content": note_content
            }
            return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"Note '{note_name}' not found."}, ensure_ascii=False)

def get_daily_note() -> str:
    """
    Returns today's daily note if it exists, formatted as JSON.
    The filename format is expected to be 'YYYY-MM-DD-Day.md'.
    """
    today = datetime.date.today().strftime("%Y-%m-%d")
    note_filename = f"{today}-{date.today().strftime('%A')}.md"  # Format: YYYY-MM-DD-Day.md
    path = os.path.join(daily_path, "Journal/" + note_filename)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            note_content = f.read()
            result = {
                "file_name": path + "/" + note_filename,
                "content": note_content
            }
            return json.dumps(result)
    return json.dumps({"result": f"No daily note found for {note_filename}."}, ensure_ascii=False)

def create_daily_note():
    pass

def get_recently_modified_notes(days: int = 7) -> str:
    """
    Returns a list of recently modified notes (Markdown files) within the specified number of days.
    Args:
        days (int): The number of days to look back for modified notes.
    Returns:
        str: A JSON-formatted string containing a list of modified note filenames or an error message.
    """
    current_time = datetime.datetime.now()
    recent_notes = []

    # Set the time threshold for "recently modified"
    time_threshold = current_time - datetime.timedelta(days=days)

    try:
        # Iterate over Markdown files in the vault path
        for path in glob.glob(os.path.join(g_vault_path, "**/*.md"), recursive=True):
            modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            if modification_time > time_threshold:
                recent_notes.append(os.path.relpath(path, g_vault_path))
        
        if recent_notes:
            return json.dumps({"results": recent_notes}, ensure_ascii=False)  # Return found notes in JSON format
        else:
            return json.dumps({"results": "No recently modified notes found."}, ensure_ascii=False)  # Indicate none found
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)  # Handle any exceptions that occur

# tool: move file to (goals)

# === Set up Memory V2 ===
memory_db_path = os.path.join(g_vault_path, ".ai-memory.db")
memory_db = SqliteMemoryDb(table_name="memory", db_file=memory_db_path)
memory = Memory(db=memory_db)

# === Initialize Agent ===
agent = Agent(
    model=OpenAIChat(id="gpt-4.1", api_key=API_KEY),
    memory=memory,
    storage=SqliteAgentStorage(table_name="agent_sessions", db_file="agent_storage.db"),
    add_history_to_messages=True,  # Adds recent chat history when generating a reply
    num_history_responses=3,
    tools=[
        # WebsiteTools(),
        get_daily_note,
        search_by_tag,
        # search_content,
        search_note_file,
        append_to_note,
        list_directory,
        get_recently_modified_notes,
        read_note,
        create_note
    ],
    markdown=True,
    name="obsidian-cli-agent",
    role="Smart Personal Knowledge Assistant for Obsidian",
    debug_mode=True,
    show_tool_calls=True,
    description = ObsidianAgent.description,
    instructions = ObsidianAgent.instructions
)

# === CLI Entrypoint ===
def main():
    parser = argparse.ArgumentParser(description="Query your Obsidian vault using AI")
    parser.add_argument("--vault", required=True, help="Path to your Obsidian vault folder")
    parser.add_argument("--query", type=str, help="Natural language query")
    parser.add_argument("--search", type=str, help="Raw search: content, tag:#tagname, or file:<title>")
    args = parser.parse_args()

    global g_vault_path

    if args.vault:
        g_vault_path = args.vault
    
    vault_path = os.path.expanduser(g_vault_path)

    if not os.path.isdir(vault_path):
        print(f"❌ Vault path '{vault_path}' does not exist.")
        return
    
    # === Run Agent ===
    if args.query:
        # result = agent.print_response(args.query)
        agent.cli_app()
    elif args.search:
        if args.search.startswith("tag:#"):
            tag = args.search.replace("tag:#", "")
            result = agent.run(f"Search for notes with tag #{tag}")
        elif args.search.startswith("file:"):
            name = args.search.replace("file:", "")
            result = agent.run(f"Search for notes with file name containing '{name}'")
        else:
            result = agent.run(f"Search inside notes for '{args.search}'")
    else:
        result = "Please provide --query, --search"

    print("\n🤖 Agent Response:\n")
    print(result)

if __name__ == "__main__":
    main()