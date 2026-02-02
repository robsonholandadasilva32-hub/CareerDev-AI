@router.post("/api/actions/create-pr")
async def create_pr(payload: dict, user: User = Depends(get_current_user_secure)):
    pr_data = payload.get("suggested_pr")

    # Aqui entra sua Action ChatGPT → GitHub
    response = github_client.create_pull_request(
        token=user.github_token,
        repo=pr_data["repo"],
        title=pr_data["title"],
        body=pr_data["description"],
        base="main",
        head=f"user-{user.id}-practice"
    )

    return response
