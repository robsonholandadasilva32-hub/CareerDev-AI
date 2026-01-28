from datetime import datetime, timedelta

class GitHubCommitVerifier:

    def verify(self, commits: list, language: str, days: int = 7) -> bool:
        ext_map = {
            "rust": ".rs",
            "python": ".py",
            "go": ".go"
        }

        cutoff = datetime.utcnow() - timedelta(days=days)
        ext = ext_map.get(language.lower())

        for commit in commits:
            commit_date = datetime.fromisoformat(commit["date"])
            if commit_date < cutoff:
                continue

            for file in commit.get("files", []):
                if file.endswith(ext):
                    return True

        return False


github_verifier = GitHubCommitVerifier()
