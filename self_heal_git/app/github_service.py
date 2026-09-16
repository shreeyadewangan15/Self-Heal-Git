import os
import logging
from typing import Tuple, Dict, List, Union, Optional, Any

from pydantic import BaseModel

# Conditional import for GitHub client
try:
    from github import Github, GithubException, Repository, PullRequest, ContentFile
except ImportError:
    Github = None  # type: ignore

logger = logging.getLogger(__name__)

class PatchAction(BaseModel):
    """Patch action model matching the one defined in app.agent._PatchAction.
    Duplicate definition here to avoid circular imports in this module.
    """
    file_path: str
    original_snippet: str
    replacement_snippet: str
    explanation: str

def _get_github_client():
    """Initialize Github client or return None for mock mode.

    Returns:
        Github | None: Authenticated Github client if a valid token is present, otherwise None.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token or token.startswith("dummy_"):
        logger.info("GitHub token missing or dummy; operating in mock mode.")
        return None
    return Github(token)

def _parse_repo_name(repo_full_name: str) -> Tuple[str, str]:
    """Split "owner/repo" into owner and repo.
    """
    if "/" not in repo_full_name:
        raise ValueError(f"Invalid repository full name: {repo_full_name}")
    owner, repo = repo_full_name.split("/", 1)
    return owner, repo

def fetch_pr_diff_and_files(repo_name: str, pr_number: int) -> Tuple[str, Dict[str, str]]:
    """Fetch the unified diff and the current contents of all modified files for a PR.

    Args:
        repo_name (str): Full repository name in the form ``owner/repo``.
        pr_number (int): Pull request number.

    Returns:
        tuple[str, dict[str, str]]: ``diff`` is a raw unified diff string.
            ``files`` maps a file path (as reported by GitHub) to its latest
            content on the head branch.
    """
    client = _get_github_client()
    if client is None:
        # Mock / Simulation behavior – return sample buggy diff and files for demonstration
        logger.debug("Mock fetch_pr_diff_and_files called for %s#%s", repo_name, pr_number)
        sample_path = "services/calculator.py"
        sample_code = (
            "from pydantic import BaseSettings\n\n"
            "def calculate_total(items, discount)\n"
            "    total = sum(items)\n"
            "    return total * (1 - discount)\n"
        )
        sample_diff = (
            "--- a/services/calculator.py\n"
            "+++ b/services/calculator.py\n"
            "@@ -1,4 +1,4 @@\n"
            "+from pydantic import BaseSettings\n"
            "+def calculate_total(items, discount)\n"
        )
        return sample_diff, {sample_path: sample_code}

    owner, repo = _parse_repo_name(repo_name)
    try:
        repository: Repository = client.get_repo(f"{owner}/{repo}")
        pull: PullRequest = repository.get_pull(pr_number)

        # Get diff via GitHub API
        import httpx
        diff_resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
            headers={
                "Accept": "application/vnd.github.v3.diff",
                "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
            },
            timeout=30,
        )
        diff_resp.raise_for_status()
        diff_text = diff_resp.text

        # Fetch modified files and their contents
        files_content: Dict[str, str] = {}
        for file in pull.get_files():
            if file.status not in {"added", "modified", "renamed", "removed"}:
                continue
            if file.status == "removed":
                continue
            raw_url = file.raw_url
            file_resp = httpx.get(
                raw_url,
                headers={"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"},
                timeout=30,
            )
            file_resp.raise_for_status()
            files_content[file.filename] = file_resp.text
        return diff_text, files_content
    except GithubException as exc:
        logger.error("GitHub API error while fetching PR data: %s", exc.data)
        raise

def apply_healing_commit(
    repo_name: str,
    pr_number: int,
    patches: List[PatchAction],
    commit_message: str = "fix(self-heal): resolve detected code issues",
) -> str:
    """Apply a series of patches to the PR head branch and push a new commit.

    Args:
        repo_name: ``owner/repo`` identifier.
        pr_number: Target pull request number.
        patches: List of :class:`PatchAction` objects describing the changes.
        commit_message: Message for the new commit.

    Returns:
        The SHA of the newly created commit.
    """
    client = _get_github_client()
    if client is None:
        logger.debug("Mock apply_healing_commit called for %s#%s", repo_name, pr_number)
        return "mock-commit-sha"

    owner, repo = _parse_repo_name(repo_name)
    repository: Repository = client.get_repo(f"{owner}/{repo}")
    pr: PullRequest = repository.get_pull(pr_number)
    head_ref = pr.head.ref
    base_sha = repository.get_branch(head_ref).commit.sha

    # Prepare a mapping of updated file contents
    updated_files: Dict[str, str] = {}
    for patch in patches:
        try:
            file_content: ContentFile = repository.get_contents(patch.file_path, ref=head_ref)
            original_text = file_content.decoded_content.decode()
        except GithubException as exc:
            logger.error("Failed to retrieve file %s: %s", patch.file_path, exc)
            raise
        if patch.original_snippet not in original_text:
            logger.warning(
                "Original snippet not found in %s; skipping patch.", patch.file_path
            )
            continue
        new_text = original_text.replace(patch.original_snippet, patch.replacement_snippet)
        updated_files[patch.file_path] = new_text

    # Create blobs and a new tree
    blob_sha_map: Dict[str, str] = {}
    for path, content in updated_files.items():
        blob = repository.create_git_blob(content, "utf-8")
        blob_sha_map[path] = blob.sha

    tree_elements = []
    for path, sha in blob_sha_map.items():
        tree_elements.append({
            "path": path,
            "mode": "100644",
            "type": "blob",
            "sha": sha,
        })

    new_tree = repository.create_git_tree(tree_elements, base_tree=base_sha)
    new_commit = repository.create_git_commit(commit_message, new_tree.sha, [base_sha])

    # Update the branch reference to point to the new commit
    ref = repository.get_git_ref(f"heads/{head_ref}")
    ref.edit(new_commit.sha)
    logger.info("Created healing commit %s on %s:%s", new_commit.sha, repo_name, head_ref)
    return new_commit.sha

def _format_healing_report(report: Any, commit_sha: Optional[str] = None) -> str:
    """Format a HealingReport into a clean GitHub PR markdown comment."""
    sha_badge = f"`{commit_sha[:7]}`" if commit_sha else "*Simulated/Dry-Run*"
    lines = [
        "## 🛠️ Self-Heal Git: Autonomous Diagnostic & Remediation Report",
        "",
        f"**Summary:** {report.summary}",
        f"**Confidence Score:** `{report.confidence_score * 100:.1f}%`",
        f"**Commit SHA:** {sha_badge}",
        "",
        "### 🔍 Detected Issues",
        "| File | Line | Type | Severity | Description |",
        "|---|---|---|---|---|",
    ]
    if hasattr(report, "issues") and report.issues:
        for issue in report.issues:
            lines.append(f"| `{issue.file_path}` | {issue.line_number} | `{issue.issue_type}` | **{issue.severity}** | {issue.description} |")
    else:
        lines.append("| - | - | - | - | No issues detected. |")

    lines.extend([
        "",
        "### 🩹 Applied AST-Validated Patches",
        "| File | Explanation |",
        "|---|---|",
    ])
    if hasattr(report, "patches") and report.patches:
        for patch in report.patches:
            lines.append(f"| `{patch.file_path}` | {patch.explanation} |")
    else:
        lines.append("| - | No patches applied. |")

    lines.append("\n---\n*Authored autonomously by **Self-Heal Git Bot** <bot@tcet-it.org>*")
    return "\n".join(lines)


def post_pr_comment(
    repo_name: str,
    pr_number: int,
    comment_body: Union[str, Any],
    commit_sha: Optional[str] = None,
) -> None:
    """Post a comment on the pull request.

    Args:
        repo_name: ``owner/repo`` identifier.
        pr_number: Pull request number.
        comment_body: Either a markdown string or a ``HealingReport`` instance.
        commit_sha: Optional commit SHA of the healing commit.
    """
    client = _get_github_client()
    if client is None:
        logger.info("Mock post_pr_comment called for %s#%s", repo_name, pr_number)
        return

    from .agent import HealingReport
    if isinstance(comment_body, HealingReport):
        comment_md = _format_healing_report(comment_body, commit_sha=commit_sha)
    else:
        comment_md = str(comment_body)

    owner, repo = _parse_repo_name(repo_name)
    repository: Repository = client.get_repo(f"{owner}/{repo}")
    pr: PullRequest = repository.get_pull(pr_number)
    pr.create_issue_comment(comment_md)
    logger.info("Posted comment to PR %s#%s", repo_name, pr_number)
