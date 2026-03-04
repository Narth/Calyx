"""Task handlers: repo_readonly_review, test_run_safe, patch_small."""

from __future__ import annotations

from .repo_readonly_review import execute_repo_readonly_review
from .test_run_safe import execute_test_run_safe
from .patch_small import execute_patch_small

HANDLERS = {
    "repo_readonly_review": execute_repo_readonly_review,
    "test_run_safe": execute_test_run_safe,
    "patch_small": execute_patch_small,
}
