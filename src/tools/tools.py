import os
import json
import glob
import re
from datetime import date
import datetime


class note_utils:
    vault_path = None
    daily_path = None
    @staticmethod
    def create_note(note_name: str, content: str) -> str:
        path = os.path.join(note_utils.vault_path, f"{note_name}")
        if os.path.exists(path):
            return f"Note '{note_name}' already exists."

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Note '{note_name}' created successfully."
        except Exception as e:
            return f"Error creating note '{note_name}': {str(e)}"

    @staticmethod
    def append_to_note(note_name: str, content: str, marker: str = "<!-- AI -->") -> str:
        path = os.path.join(note_utils.vault_path, f"{note_name}")
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

    @staticmethod
    def search_note_file(query: str) -> str:
        matches = []
        for root, dirs, files in os.walk(note_utils.vault_path):
            for f in files:
                if query.lower() in f.lower() and f.endswith(".md"):
                    matches.append(os.path.relpath(os.path.join(root, f), note_utils.vault_path))

        for path in glob.glob(os.path.join(note_utils.vault_path, "**/*.md"), recursive=True):
            with open(path, "r", encoding="utf-8") as f:
                if query.lower() in f.read().lower():
                    matches.append(os.path.relpath(path, note_utils.vault_path))

        return "\n".join(set(matches)) if matches else "No matching note titles or content found."

    @staticmethod
    def read_note(note_name: str) -> str:
        path = os.path.join(note_utils.vault_path, f"{note_name}")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                note_content = f.read()
                result = {
                    "file_name": f"{note_name}",
                    "content": note_content
                }
                return json.dumps(result, ensure_ascii=False)

        return json.dumps({"error": f"Note '{note_name}' not found."}, ensure_ascii=False)

    @staticmethod
    def get_daily_note() -> str:
        today = date.today().strftime("%Y-%m-%d")
        note_filename = f"{today}-{date.today().strftime('%A')}.md"
        path = os.path.join(note_utils.daily_path, note_filename)

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                note_content = f.read()
                result = {
                    "file_name": path + "/" + note_filename,
                    "content": note_content
                }
                return json.dumps(result)
        return json.dumps({"result": f"No daily note found for {note_filename}."}, ensure_ascii=False)

    @staticmethod
    def search_by_tag(tag: str) -> str:
        matches = []
        for path in glob.glob(os.path.join(note_utils.vault_path, "**/*.md"), recursive=True):
            with open(path, "r", encoding="utf-8") as f:
                if f"#{tag.lower()}" in f.read().lower():
                    matches.append(os.path.relpath(path, note_utils.vault_path))

        return "\n".join(set(matches)) if matches else "No notes with tag found."
    @staticmethod
    def list_directory(dir_path: str) -> str:
        cleaned = dir_path.lstrip("/\\")
        full_path = os.path.join(note_utils.vault_path, cleaned)

        try:
            entries = [
                f + '/' if os.path.isdir(os.path.join(full_path, f)) else f
                for f in os.listdir(full_path)
            ]
            if entries:
                return json.dumps({"results": entries}, ensure_ascii=False)
            else:
                return json.dumps({"results": "No files or directories found."})
        except FileNotFoundError:
            return json.dumps({"error": f"Directory '{full_path}' not found."})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @staticmethod
    def get_recently_modified_notes(days: int = 7) -> str:
        current_time = datetime.datetime.now()
        recent_notes = []
        time_threshold = current_time - datetime.timedelta(days=days)

        try:
            for path in glob.glob(os.path.join(note_utils.vault_path, "**/*.md"), recursive=True):
                modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
                if modification_time > time_threshold:
                    recent_notes.append(os.path.relpath(path, note_utils.vault_path))

            if recent_notes:
                return json.dumps({"results": recent_notes}, ensure_ascii=False)
            else:
                return json.dumps({"results": "No recently modified notes found."}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

def _load_tags_from_json(file_path: str) -> set:
    """Loads tags from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tags = json.load(f)
            return set(tags)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading tags from {file_path}: {e}")
        return None


def _save_tags_to_json(file_path: str, tags: set):
    """Saves tags to a JSON file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(list(tags), f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving tags to {file_path}: {e}")


class tag_utils:
    vault_path = None
    daily_path = None
    def get_vault_tags(vault_path: str) -> set:
        """
        Scans all files in the Obsidian vault and extracts all the tags.
        The tool should output a list of unique tags.
        Saves all tags to .json and uses it when it exists.
        """
        tags_file = os.path.join(vault_path, "tags.json")
        unique_tags = _load_tags_from_json(tags_file)

        if unique_tags is None:
            unique_tags = set()
            for root, _, files in os.walk(vault_path):
                for file in files:
                    if file.endswith(".md"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                tags = re.findall(r"#\w+", content)
                                unique_tags.update(tags)
                        except Exception as e:
                            print(f"Error reading file {file_path}: {e}")
            _save_tags_to_json(tags_file, unique_tags)

        return unique_tags