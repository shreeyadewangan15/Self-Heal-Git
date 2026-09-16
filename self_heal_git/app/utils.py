import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks
from sqlmodel import Session
from .config import settings, engine
from .models import PRRecord
from .agent import diagnose_and_heal, verify_patch_syntax, HealingReport, PatchAction, CodeIssue

logger = logging.getLogger(__name__)


def verify_signature(secret: str, body: bytes, signature_header: Optional[str]) -> bool:
    """Verify GitHub webhook HMAC SHA-256 signature.

    GitHub sends the signature in the ``X-Hub-Signature-256`` header in the form
    ``sha256=...``. This function computes the HMAC using the provided secret and
    compares it with the header value using ``hmac.compare_digest`` for constant-time
    safety on the exact raw request body bytes.
    """
    if not signature_header or not secret:
        return False
    try:
        if "=" in signature_header:
            sha_name, signature = signature_header.split("=", 1)
            if sha_name.strip() != "sha256":
                return False
            expected_sig = signature.strip()
        else:
            expected_sig = signature_header.strip()

        mac = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
        return hmac.compare_digest(mac.hexdigest(), expected_sig)
    except Exception as e:
        logger.exception("Error verifying signature: %s", e)
        return False


def extract_pr_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract required PR metadata from a GitHub pull_request webhook payload.

    Expected keys are present when the event is a pull request action (opened,
    synchronize, reopened). The function returns a dictionary containing:
    ``repo``, ``pr_number``, ``title``, ``head_branch``, ``base_branch``, and
    ``head_sha``.
    """
    repository = payload.get("repository", {})
    pull = payload.get("pull_request", {})
    return {
        "repo": repository.get("full_name"),
        "pr_number": pull.get("number"),
        "title": pull.get("title"),
        "head_branch": pull.get("head", {}).get("ref"),
        "base_branch": pull.get("base", {}).get("ref"),
        "head_sha": pull.get("head", {}).get("sha"),
    }


def process_pr(metadata: Dict[str, Any]) -> None:
    """Background task that processes a PR end‑to‑end.

    1️⃣ Set status to ANALYZING.
    2️⃣ Fetch PR diff & file contents via ``github_service``.
    3️⃣ Run ``diagnose_and_heal`` to obtain a ``HealingReport``.
    4️⃣ Verify each patch with ``verify_patch_syntax``.
    5️⃣ If all patches valid, apply them as a commit on the PR head branch.
    6️⃣ Post a structured review comment.
    7️⃣ Update DB status to **HEALED** (or **FAILED** on any error).
    """
    logger.info("Processing PR: %s", metadata)
    # ---------------------------------------------------
    # 1. Update status to ANALYZING
    # ---------------------------------------------------
    with Session(engine) as session:
        record = session.query(PRRecord).filter(
            PRRecord.repo == metadata["repo"],
            PRRecord.pr_number == metadata["pr_number"]
        ).first()
        if record:
            record.status = "ANALYZING"
            session.add(record)
            session.commit()
            logger.info("PR %s status set to ANALYZING", metadata["pr_number"])
        else:
            logger.warning("PR record not found for %s#%s", metadata["repo"], metadata["pr_number"])
            return

    # ---------------------------------------------------
    # 2. Fetch diff & files from GitHub (mock if token missing)
    # ---------------------------------------------------
    from .github_service import fetch_pr_diff_and_files, apply_healing_commit, post_pr_comment
    try:
        diff, files = fetch_pr_diff_and_files(metadata["repo"], metadata["pr_number"])
    except Exception as exc:
        logger.exception("Failed to fetch diff/files: %s", exc)
        final_status = "FAILED"
        # update status and exit
        with Session(engine) as session:
            rec = session.query(PRRecord).filter(
                PRRecord.repo == metadata["repo"], PRRecord.pr_number == metadata["pr_number"]
            ).first()
            if rec:
                rec.status = final_status
                session.add(rec)
                session.commit()
        return

    # ---------------------------------------------------
    # 3. Diagnose and heal via LLM
    # ---------------------------------------------------
    try:
        report: HealingReport = diagnose_and_heal(
            repo_name=metadata["repo"],
            pr_number=metadata["pr_number"],
            git_diff=diff,
            file_contents=files,
        )
        logger.info("Healing report generated: %s", report.summary)
    except Exception as exc:
        logger.exception("LLM diagnostic failed: %s", exc)
        final_status = "FAILED"
        with Session(engine) as session:
            rec = session.query(PRRecord).filter(
                PRRecord.repo == metadata["repo"], PRRecord.pr_number == metadata["pr_number"]
            ).first()
            if rec:
                rec.status = final_status
                session.add(rec)
                session.commit()
        return

    # ---------------------------------------------------
    # 4. Verify patches syntactically
    # ---------------------------------------------------
    all_valid = True
    for patch in report.patches:
        original = files.get(patch.file_path, "")
        valid, details = verify_patch_syntax(patch.file_path, original, patch)
        if not valid:
            all_valid = False
            logger.error("Patch syntax invalid for %s: %s", patch.file_path, details)

    if not all_valid:
        final_status = "FAILED"
        post_pr_comment(metadata["repo"], metadata["pr_number"], report, commit_sha=None)
        with Session(engine) as session:
            rec = session.query(PRRecord).filter(
                PRRecord.repo == metadata["repo"], PRRecord.pr_number == metadata["pr_number"]
            ).first()
            if rec:
                rec.status = final_status
                rec.summary = report.summary
                rec.confidence = report.confidence_score
                rec.issues_json = json.dumps([i.model_dump() for i in report.issues])
                rec.patches_json = json.dumps([p.model_dump() for p in report.patches])
                session.add(rec)
                session.commit()
        return

    # ---------------------------------------------------
    # 5. Apply patches as a commit on the PR head branch
    # ---------------------------------------------------
    try:
        commit_sha = apply_healing_commit(
            repo_name=metadata["repo"],
            pr_number=metadata["pr_number"],
            patches=report.patches,
        )
        logger.info("Healing commit created: %s", commit_sha)
    except Exception as exc:
        logger.exception("Failed to apply healing commit: %s", exc)
        final_status = "FAILED"
        post_pr_comment(metadata["repo"], metadata["pr_number"], report, commit_sha=None)
        with Session(engine) as session:
            rec = session.query(PRRecord).filter(
                PRRecord.repo == metadata["repo"], PRRecord.pr_number == metadata["pr_number"]
            ).first()
            if rec:
                rec.status = final_status
                rec.summary = report.summary
                rec.confidence = report.confidence_score
                rec.issues_json = json.dumps([i.model_dump() for i in report.issues])
                rec.patches_json = json.dumps([p.model_dump() for p in report.patches])
                session.add(rec)
                session.commit()
        return

    # ---------------------------------------------------
    # 6. Post PR comment with a nice markdown table
    # ---------------------------------------------------
    post_pr_comment(metadata["repo"], metadata["pr_number"], report, commit_sha=commit_sha)

    # ---------------------------------------------------
    # 7. Update final status to HEALED
    # ---------------------------------------------------
    final_status = "HEALED"
    with Session(engine) as session:
        rec = session.query(PRRecord).filter(
            PRRecord.repo == metadata["repo"], PRRecord.pr_number == metadata["pr_number"]
        ).first()
        if rec:
            rec.status = final_status
            rec.summary = report.summary
            rec.confidence = report.confidence_score
            rec.issues_json = json.dumps([i.model_dump() for i in report.issues])
            rec.patches_json = json.dumps([p.model_dump() for p in report.patches])
            rec.commit_sha = commit_sha
            session.add(rec)
            session.commit()
            logger.info("PR %s final status set to %s with commit %s", metadata["pr_number"], final_status, commit_sha)
