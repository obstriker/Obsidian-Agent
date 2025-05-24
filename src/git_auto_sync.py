import time
import logging
from datetime import datetime
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

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
            handlers=[logging.StreamHandler()]
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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info("Starting sync cycle...")

        try:
            origin = self.repo.remotes.origin

            logging.info("Pulling latest changes...")
            origin.pull(self.branch)

            if self.repo.is_dirty(untracked_files=True):
                logging.info("Changes detected. Committing...")
                self.repo.git.add(A=True)
                self.repo.index.commit(f"Auto commit at {timestamp}")
                origin.push(self.branch)
                logging.info("Changes pushed successfully.")
            else:
                logging.info("No changes to commit.")

        except GitCommandError as e:
            logging.error(f"Git command failed: {e}")

    def run_forever(self):
        """
        Continuously sync the repository every `self.interval` seconds.
        """
        logging.info(f"Starting auto-sync every {self.interval} seconds...")
        while True:
            self.sync()
            time.sleep(self.interval)


# g = GitAutoSync(repo_path="..\..\Vaults\Obsidian-DB", branch="main", interval=3)
# g.run_forever()