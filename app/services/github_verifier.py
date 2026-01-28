from datetime import datetime, timedelta
from typing import List, Dict

class GitHubCommitVerifier:
    """
    Verifica se commits recentes atendem aos critérios de uma tarefa de código.
    """

    EXTENSIONS = {
        "rust": ".rs",
        "python": ".py",
        "go": ".go",
        "javascript": ".js",
        "typescript": ".ts"
    }

    def verify(self, commits: List[Dict], language: str, days: int = 7) -> bool:
        """
        Retorna True se encontrar commits recentes com arquivos compatíveis
        com a linguagem esperada.
        """
        if not commits or not language:
            return False

        ext = self.EXTENSIONS.get(language.lower())
        if not ext:
            return False

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        for commit in commits:
            try:
                commit_date = datetime.fromisoformat(commit["date"])
            except Exception:
                continue

            if commit_date < cutoff_date:
                continue

            for file_path in commit.get("files", []):
                if file_path.endswith(ext):
                    return True

        return False


# Instância reutilizável
github_verifier = GitHubCommitVerifier()
