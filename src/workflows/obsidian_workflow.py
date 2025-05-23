from agno.agent import Agent
from agno.workflow import RunResponse, Workflow

import logging
import os

from prompts import *
from agno.models.openai import OpenAIChat
from agno.storage.agent.sqlite import SqliteAgentStorage
from tools import *
from prompts import *
from dotenv import load_dotenv
from agno.memory.memory import Memory
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.memory.db.sqlite import SqliteMemoryDb
from prompts import TaggingAgent
from vault_embedder import VaultEmbedder

load_dotenv()
logging.basicConfig(level=logging.WARNING)

OVERVIEW_FILENAME = "overview.md"

class ObsidianWorkflow(Workflow):
    name = "Obsidian Workflow"
    description = "Orchestrates the main agent and tagging agent to create and tag notes."
    overviewed = False

    vault_overview_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4.1"),
        # memory=memory,
        storage=SqliteAgentStorage(table_name="vault_overview_agent_sessions", db_file="vault_overview_agent_storage.db"),
        add_history_to_messages=True,  # Adds recent chat history when generating a reply
        num_history_responses=3,
        tools=[
            note_utils.list_directory,
            note_utils.search_note_file,
            note_utils.search_by_tag,
            note_utils.read_note,
        ],
        markdown=True,
        name="Vault Overview Agent",
        role="Vault Structure and Content Overview Agent",
        debug_mode=True,
        # show_tool_calls=True,
        description = VaultOverviewAgent.description,
        instructions = VaultOverviewAgent.instructions
    )
    
    main_agent: Agent = Agent(
    model=OpenAIChat(id="gpt-4.1"),
    # memory=memory,
    storage=SqliteAgentStorage(table_name="agent_sessions", db_file="agent_storage.db"),
    add_history_to_messages=True,  # Adds recent chat history when generating a reply
    num_history_responses=3,
    tools=[
        # WebsiteTools(),
        note_utils.get_daily_note,
        note_utils.search_by_tag,
        # search_content,
        note_utils.search_note_file,
        note_utils.append_to_note,
        note_utils.list_directory,
        note_utils.get_recently_modified_notes,
        note_utils.read_note,
        note_utils.create_note
    ],
    markdown=True,
    name="obsidian-cli-agent",
    role="Smart Personal Knowledge Assistant for Obsidian",
    debug_mode=True,
    show_tool_calls=True,
    description = ObsidianAgent.description,
    instructions = ObsidianAgent.instructions
)

    tagging_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4.1"),
        storage=SqliteAgentStorage(table_name="tagging_agent_sessions", db_file="tagging_agent_storage.db"),
        add_history_to_messages=True,
        num_history_responses=3,
        tools=[
            tag_utils.get_vault_tags,
            note_utils.append_to_note
        ],
        markdown=True,
        name="tagging-agent",
        role="Agent responsible for tagging notes with existing tags from the vault",
        debug_mode=True,
        show_tool_calls=True,
        description = TaggingAgent.description,
        instructions = TaggingAgent.instructions
    )

    def __init__(self, vault_path=None):
        self.vault_path = vault_path

        note_utils.vault_path = vault_path
        tag_utils.vault_path = vault_path
        note_utils.daily_path = os.path.join(vault_path, "Daily", "Journal")

        assitant_path = os.path.join(vault_path, ".assistant")
        if not os.path.exists(assitant_path):
            os.makedirs(assitant_path)

        # db_path = os.path.join(vault_path, ".assistant", "agent_storage.db")
        # memory_db = SqliteMemoryDb(table_name="memory", db_file=db_path)
        # self.memory = Memory(memory=db_path)
        from agno.memory import AgentMemory
        self.memory = AgentMemory()


        self.main_agent.memory = self.memory
        self.vault_overview_agent.memory = self.memory
        self.tagging_agent.memory = self.memory

        vault_overview_path = os.path.join(vault_path, ".assistant", OVERVIEW_FILENAME)
        if os.path.exists(vault_overview_path):
            self.vault_overview = open(vault_overview_path, "r", encoding="utf-8").read()
            self.overviewed = True

        self.vault = VaultEmbedder(vault_path)
        self.vault.sync()
        self.vault.start_monitoring(interval=1800)
        self.main_agent.knowledge = self.vault.kb

    def sync_vault(self):
        self.vault.sync()
        self.vault.start_monitoring(interval=1800)
        self.main_agent.knowledge = self.vault.kb

    def run(self, query: str) -> RunResponse:
        vault_overview_path = os.path.join(self.vault_path, ".assistant", OVERVIEW_FILENAME)
    
        logging.info(f"Running Obsidian workflow with query: {query}")

        if not query or query.strip() == "":
            logging.error("Query is empty or contains only whitespace.")
            return RunResponse(content="Error: Query cannot be empty.")

        if not self.overviewed:
            logging.info("Vault overview file does not exist, creating a new one.")
            overview = self.vault_overview_agent.run("Create an overview for the vault.").content
            
            with open(vault_overview_path, "w", encoding="utf-8") as f:
                f.write(overview)

            self.vault_overview = overview
            self.overviewed = True
        
        # self.main_agent.description = ObsidianAgent.description[0] + "\n" + self.vault_overview

        return RunResponse(content=self.main_agent.cli_app(query))
