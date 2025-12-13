#!/usr/bin/env python3
"""
SVF Query System - Enable cross-agent queries and responses
Part of SVF v2.0 enhancements (implemented 2025-10-26)
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
QUERIES_DIR = OUT / "queries"
RESPONSES_DIR = OUT / "responses"
SHARED_LOGS = OUT / "shared_logs"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON file with error handling"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error writing {path}: {e}")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read JSON file with error handling"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def create_query(from_agent: str, to_agent: str, question: str, 
                 priority: str = "medium", context: str = "", 
                 timeout_minutes: int = 5) -> str:
    """
    Create a cross-agent query
    
    Args:
        from_agent: Agent creating the query
        to_agent: Target agent to answer
        question: The question being asked
        priority: low, medium, high, urgent
        context: Additional context for the question
        timeout_minutes: Max time to wait for response
        
    Returns:
        Query UUID
    """
    query_id = str(uuid.uuid4())
    
    query_data = {
        "query_id": query_id,
        "from": from_agent,
        "to": to_agent,
        "priority": priority,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "context": context,
        "timeout_minutes": timeout_minutes,
        "status": "pending",
        "resolved": False
    }
    
    query_file = QUERIES_DIR / f"{query_id}.query.json"
    _write_json(query_file, query_data)
    
    # Log query creation
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "query_created",
        "query_id": query_id,
        "from": from_agent,
        "to": to_agent,
        "question": question[:100]  # Preview
    }
    
    log_file = SHARED_LOGS / f"svf_query_{query_id}.md"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as f:
        f.write(f"# SVF Query: {query_id}\n\n")
        f.write(f"**From:** {from_agent}\n")
        f.write(f"**To:** {to_agent}\n")
        f.write(f"**Priority:** {priority}\n")
        f.write(f"**Question:** {question}\n")
        f.write(f"**Context:** {context}\n\n")
        f.write(f"**Status:** Pending response\n")
    
    return query_id


def respond_to_query(query_id: str, responder: str, answer: str, 
                     data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Respond to a query
    
    Args:
        query_id: UUID of the query
        responder: Agent responding
        answer: The answer text
        data: Optional structured data
        
    Returns:
        True if successful
    """
    query_file = QUERIES_DIR / f"{query_id}.query.json"
    query = _read_json(query_file)
    
    if not query:
        return False
    
    if query.get("to") != responder:
        print(f"Warning: Query {query_id} not addressed to {responder}")
        return False
    
    response_data = {
        "query_id": query_id,
        "responder": responder,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "answer": answer,
        "data": data or {}
    }
    
    response_file = RESPONSES_DIR / f"{query_id}.response.json"
    _write_json(response_file, response_data)
    
    # Update query status
    query["status"] = "answered"
    query["resolved"] = True
    query["response_time"] = datetime.now(timezone.utc).isoformat()
    _write_json(query_file, query)
    
    # Update log
    log_file = SHARED_LOGS / f"svf_query_{query_id}.md"
    if log_file.exists():
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n---\n\n")
            f.write(f"**Response from {responder}:**\n\n")
            f.write(f"{answer}\n\n")
            if data:
                f.write(f"**Data:**\n```json\n{json.dumps(data, indent=2)}\n```\n")
    
    return True


def get_pending_queries(agent_name: str) -> List[Dict[str, Any]]:
    """Get all pending queries for an agent"""
    queries = []
    
    if not QUERIES_DIR.exists():
        return queries
    
    for query_file in QUERIES_DIR.glob("*.query.json"):
        query = _read_json(query_file)
        if query and query.get("to") == agent_name and not query.get("resolved"):
            queries.append(query)
    
    return queries


def main():
    parser = argparse.ArgumentParser(description="SVF Query System")
    parser.add_argument("--from", dest="from_agent", required=True, help="Source agent")
    parser.add_argument("--to", dest="to_agent", required=True, help="Target agent")
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument("--priority", default="medium", choices=["low", "medium", "high", "urgent"])
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout in minutes")
    
    parser.add_argument("--respond", action="store_true", help="Respond to queries instead of creating")
    parser.add_argument("--query-id", help="Query ID for response")
    parser.add_argument("--answer", help="Answer text")
    parser.add_argument("--data", help="JSON data file for response")
    
    parser.add_argument("--check", action="store_true", help="Check for pending queries")
    
    args = parser.parse_args()
    
    if args.check:
        queries = get_pending_queries(args.from_agent)
        print(f"Found {len(queries)} pending queries")
        for q in queries:
            print(f"  [{q['priority']}] {q['question'][:60]}...")
        return
    
    if args.respond:
        data = None
        if args.data:
            data = _read_json(Path(args.data))
        
        success = respond_to_query(args.query_id, args.from_agent, args.answer, data)
        print(f"Response {'sent' if success else 'failed'}")
        return
    
    # Create query
    query_id = create_query(
        from_agent=args.from_agent,
        to_agent=args.to_agent,
        question=args.question,
        priority=args.priority,
        context=args.context,
        timeout_minutes=args.timeout
    )
    
    print(f"Query created: {query_id}")
    print(f"Waiting for response from {args.to_agent}...")


if __name__ == "__main__":
    main()

