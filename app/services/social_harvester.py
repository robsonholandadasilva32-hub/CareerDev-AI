import httpx
import logging
import asyncio
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models.user import User
from app.db.models.career import CareerProfile

logger = logging.getLogger(__name__)

class SocialHarvester:
    """
    Service responsible for fetching raw data from Social APIs (GitHub, LinkedIn)
    and transforming it into actionable Dashboard metrics.
    """

    def __init__(self):
        self.market_high_demand_skills = ["Rust", "Go", "Python", "AI/ML", "React", "System Design", "Cloud Architecture"]

    async def harvest_github_data(self, db: Session, user: User, token: str) -> bool:
        """
        Fetches GitHub Repos, analyzes language distribution, and calculates commit velocity.
        Updates user.career_profile with the results.
        """
        if not user.career_profile:
            # Create profile if missing (sanity check)
            logger.warning(f"Profile missing for user {user.id}, creating one.")
            profile = CareerProfile(user_id=user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CareerDev-AI-Harvester"
        }

        try:
            async with httpx.AsyncClient() as client:
                # 1. Fetch User Info (for username)
                user_resp = await client.get("https://api.github.com/user", headers=headers)
                if user_resp.status_code != 200:
                    logger.error(f"GitHub User Fetch Failed: {user_resp.text}")
                    return False

                gh_user = user_resp.json()
                username = gh_user.get("login")

                # 2. Fetch Repos (Top 15 recently updated to save bandwidth/time)
                # We analyze these for language composition
                repos_url = f"https://api.github.com/user/repos?sort=updated&per_page=15&type=owner"
                repos_resp = await client.get(repos_url, headers=headers)
                repos = repos_resp.json() if repos_resp.status_code == 200 else []

                language_bytes = {}
                total_bytes = 0

                # 3. Analyze Languages (Parallel Requests)
                # We use a semaphore to limit concurrency if needed, but for 15 it's fine.
                async def fetch_languages(repo):
                    lang_url = repo.get("languages_url")
                    if lang_url:
                        r = await client.get(lang_url, headers=headers)
                        if r.status_code == 200:
                            return r.json()
                    return {}

                tasks = [fetch_languages(repo) for repo in repos]
                results = await asyncio.gather(*tasks)

                for lang_map in results:
                    for lang, bytes_count in lang_map.items():
                        language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count
                        total_bytes += bytes_count

                # Calculate Percentages for Doughnut Chart
                # Format: {"labels": ["Python", "Rust"], "data": [80, 20]}
                sorted_langs = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:6] # Top 6

                chart_labels = [l[0] for l in sorted_langs]
                chart_data = []
                for l in sorted_langs:
                    percentage = int((l[1] / total_bytes) * 100) if total_bytes > 0 else 0
                    chart_data.append(percentage)

                skills_graph_data = {
                    "labels": chart_labels,
                    "datasets": [{
                        "data": chart_data,
                        "backgroundColor": ["#00f3ff", "#bd00ff", "#00ff88", "#ffff00", "#ff0055", "#ffffff"]
                    }]
                }

                # 4. Activity Pulse (Commit Velocity)
                # Heuristic: Count PushEvents in the last 30 days from Events API
                events_url = f"https://api.github.com/users/{username}/events?per_page=50"
                events_resp = await client.get(events_url, headers=headers)
                commit_count = 0
                if events_resp.status_code == 200:
                    events = events_resp.json()
                    cutoff = datetime.utcnow() - timedelta(days=30)
                    for e in events:
                        if e.get("type") == "PushEvent":
                            created_at = datetime.strptime(e["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                            if created_at > cutoff:
                                # A PushEvent can have multiple commits
                                payload = e.get("payload", {})
                                commit_count += payload.get("size", 1)

                # 5. Update Database
                profile = user.career_profile

                # Update existing stats
                current_stats = profile.github_stats or {}
                current_stats.update({
                    "commit_velocity_30d": commit_count,
                    "top_languages_raw": {k: v for k, v in sorted_langs},
                    "last_harvest": datetime.utcnow().isoformat()
                })
                profile.github_stats = current_stats

                # Update new Visualization Field
                profile.skills_graph_data = skills_graph_data

                # Update Market Alignment Score
                # Extract skills from chart labels for comparison
                user_skills = {l[0] for l in sorted_langs}
                profile.market_alignment_score = self.calculate_alignment_score(user_skills)

                db.commit()
                logger.info(f"✅ GitHub Harvest Complete for {username}. Score: {profile.market_alignment_score}")
                return True

        except Exception as e:
            logger.error(f"GitHub Harvest Error: {e}", exc_info=True)
            return False

    async def harvest_linkedin_data(self, db: Session, user: User, token: str) -> bool:
        """
        Attempts to fetch LinkedIn Profile. Fallback to simulation if scopes are restricted.
        """
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.linkedin.com/v2/me", headers=headers)

                profile = user.career_profile
                if not profile:
                    # Should be handled by now, but just in case
                    return False

                if resp.status_code == 200:
                    data = resp.json()
                    # Real Data Extraction
                    # Note: vanilla r_liteprofile doesn't give 'headline' (role), just name/id.
                    # We might get lucky if the app has openid profile scopes that map to more.
                    # Assuming we might not get role, we'll try standard fields.

                    # If we can't find role, we might use a fallback or user input in future.
                    # For now, let's just log what we have and maybe set a flag.

                    # Fallback Simulation Logic for "Role" if missing
                    # The prompt says: "Action: Extract current Role and Industry."
                    # If API fails to give this, we use the "Simulated Data" fallback as per decision matrix.

                    profile.linkedin_stats = {
                        "id": data.get("id"),
                        "harvest_status": "success",
                        "last_harvest": datetime.utcnow().isoformat()
                    }
                    # We don't overwrite bio/role if we don't have better data from API
                else:
                    logger.warning(f"LinkedIn Harvest Restricted ({resp.status_code}). Using Simulation Fallback.")
                    # Simulation Fallback (as requested)
                    profile.linkedin_stats = {
                        "harvest_status": "simulated",
                        "connection_count": "500+",
                        "last_harvest": datetime.utcnow().isoformat()
                    }
                    if not profile.target_role or profile.target_role == "Senior Developer":
                         # Inject a clearer role if default
                         profile.target_role = "Senior Full Stack Engineer"

                db.commit()
                return True

        except Exception as e:
            logger.error(f"LinkedIn Harvest Error: {e}", exc_info=True)
            return False

    def calculate_alignment_score(self, user_skills: set) -> int:
        """
        Matches = Intersection(UserSkills, MarketHighDemandSkills)
        Score = (Count(Matches) / Count(MarketHighDemandSkills)) * 100
        """
        market_set = set(self.market_high_demand_skills)
        # Normalize to title case for comparison
        user_norm = {s.title() for s in user_skills}
        market_norm = {s.title() for s in market_set}

        matches = user_norm.intersection(market_norm)

        if not market_norm:
            return 0

        score = int((len(matches) / len(market_norm)) * 100)

        # Cap at 100
        return min(score, 100)

social_harvester = SocialHarvester()
