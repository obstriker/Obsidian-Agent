import time
import logging
from datetime import datetime
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError
import sys

class GitAutoSync:
    def __init__(self, repo_path: str, branch: str = "main", interval: int = 300):
        """
        Initialize GitAutoSync.

        :param repo_path: Path to the local Git repository.
        :param branch: Branch to pull from and push to.
        :param interval: Time in seconds between syncs (default: 300 = 5 min).
        """
        self.repo_path = repo_path
        self.branch = branch
        self.interval = interval
        self.repo = self._load_repo()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )

    def _load_repo(self):
        try:
            repo = Repo(self.repo_path)
            if repo.bare:
                raise InvalidGitRepositoryError("The repository is bare.")
            return repo
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            logging.error(f"Failed to load Git repository: {e}")
            raise

    def sync(self):
        """
        Perform a pull → add → commit → push cycle.
        """
        # Adding detailed logging for debugging
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info("Starting sync cycle...")
        logging.info("Starting sync cycle...")

        try:
            origin = self.repo.remotes.origin

            logging.info("Pulling latest changes...")
            try:
                origin.pull(self.branch)
                logging.info("Pull successful.")
            except GitCommandError as e:
                logging.error(f"Error during pull: {e}")

            if self.repo.is_dirty(untracked_files=True):
                logging.info("Changes detected. Committing...")
                try:
                    self.repo.git.add(A=True)
                    self.repo.index.commit(f"Auto commit at {timestamp}")
                    logging.info("Commit successful.")
                except Exception as e:
                    logging.error(f"Error during commit: {e}")
                self.repo.index.commit(f"Auto commit at {timestamp}")
                try:
                    origin.push(self.branch)
                    logging.info("Changes pushed successfully.")
                except GitCommandError as e:
                    logging.error(f"Error during push: {e}")
                logging.info("Changes pushed successfully.")
            else:
                logging.info("No changes to commit.")

        except GitCommandError as e:
            logging.error(f"Git command failed: {e}")

    def run(self, interval: int = 300):
        """
        Continuously sync the repository every `self.interval` seconds.
        """
        logging.info(f"Starting auto-sync every {interval} seconds...")
        while True:
            logging.info(f"Sync cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.sync()
            time.sleep(interval)


# g = GitAutoSync(repo_path="..\..\Vaults\Obsidian-DB", branch="main", interval=3)
# g.run()