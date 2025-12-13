"""Manifest System - Single source of truth for execution, prevents double-dispatch"""

from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ManifestSystem:
    """Manages execution manifests to prevent duplicate dispatch"""
    
    def __init__(self, root: Path):
        self.root = root
        self.manifest_dir = root / "outgoing" / "coordinator"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.claimed_manifests: Dict[str, float] = {}  # manifest_id -> claim_time
    
    def create_manifest(self, intent_id: str, content: Dict[str, Any]) -> str:
        """Create a manifest for an intent execution
        
        Returns manifest_id (stable hash of content)
        """
        # Create stable hash from content
        content_str = json.dumps(content, sort_keys=True)
        manifest_id = hashlib.sha256(content_str.encode()).hexdigest()[:12]
        
        # Write manifest
        manifest_file = self.manifest_dir / f"{manifest_id}.json"
        manifest_data = {
            "manifest_id": manifest_id,
            "intent_id": intent_id,
            "created_at": datetime.now().isoformat(),
            "content": content,
            "status": "created"
        }
        
        try:
            manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding='utf-8')
        except Exception:
            pass
        
        return manifest_id
    
    def claim_manifest(self, manifest_id: str) -> bool:
        """Claim a manifest (check if available and mark as claimed)
        
        Returns True if manifest was successfully claimed
        """
        manifest_file = self.manifest_dir / f"{manifest_id}.json"
        
        if not manifest_file.exists():
            return False
        
        # Check if already claimed recently (within last 5 minutes)
        now = time.time()
        if manifest_id in self.claimed_manifests:
            claim_time = self.claimed_manifests[manifest_id]
            if (now - claim_time) < 300:  # 5 minutes
                return False
        
        # Claim it
        self.claimed_manifests[manifest_id] = now
        
        # Update manifest status
        try:
            data = json.loads(manifest_file.read_text(encoding='utf-8'))
            data["status"] = "claimed"
            data["claimed_at"] = datetime.now().isoformat()
            manifest_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass
        
        return True
    
    def mark_complete(self, manifest_id: str, result: Dict[str, Any]):
        """Mark manifest as complete with result"""
        manifest_file = self.manifest_dir / f"{manifest_id}.json"
        
        if not manifest_file.exists():
            return
        
        try:
            data = json.loads(manifest_file.read_text(encoding='utf-8'))
            data["status"] = "complete"
            data["completed_at"] = datetime.now().isoformat()
            data["result"] = result
            manifest_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass
    
    def mark_failed(self, manifest_id: str, error: str):
        """Mark manifest as failed"""
        manifest_file = self.manifest_dir / f"{manifest_id}.json"
        
        if not manifest_file.exists():
            return
        
        try:
            data = json.loads(manifest_file.read_text(encoding='utf-8'))
            data["status"] = "failed"
            data["failed_at"] = datetime.now().isoformat()
            data["error"] = error
            manifest_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass
    
    def get_manifest(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """Get manifest data"""
        manifest_file = self.manifest_dir / f"{manifest_id}.json"
        
        if not manifest_file.exists():
            return None
        
        try:
            return json.loads(manifest_file.read_text(encoding='utf-8'))
        except Exception:
            return None

