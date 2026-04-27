#!/usr/bin/env python3
"""
Helper to create evaluation datasets from real Q&A pairs.
Usage: python data/eval/eval_dataset.py --add "Question" "Ground truth answer"
"""

import os
import sys
import json
import argparse
from pathlib import Path

DATASET_PATH = Path(__file__).parent / "sample_dataset.json"

def load_existing():
    """Load existing dataset"""
    if DATASET_PATH.exists():
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": "1.0", "description": "Evaluation dataset", "questions": []}

def save_dataset(data):
    """Save dataset"""
    with open(DATASET_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_question(question: str, ground_truth: str, difficulty: str = "medium"):
    """Add a new Q&A pair to the dataset"""
    data = load_existing()
    
    # Generate ID
    existing_ids = [q["id"] for q in data["questions"]]
    new_id = f"q{len(data['questions']) + 1}"
    while new_id in existing_ids:
        new_id = f"q{int(new_id[1:]) + 1}"
    
    new_question = {
        "id": new_id,
        "question": question,
        "ground_truth": ground_truth,
        "expected_sources": [],
        "difficulty": difficulty
    }
    
    data["questions"].append(new_question)
    save_dataset(data)
    
    print(f"✅ Added {new_id}: {question[:50]}...")
    print(f"   Total questions: {len(data['questions'])}")

def list_questions():
    """List all questions in the dataset"""
    data = load_existing()
    
    print(f"\n📋 Dataset: {DATASET_PATH}")
    print(f"   Questions: {len(data['questions'])}\n")
    
    for q in data["questions"]:
        print(f"  [{q['id']}] ({q['difficulty']}) {q['question'][:60]}...")

def remove_question(question_id: str):
    """Remove a question by ID"""
    data = load_existing()
    
    original_count = len(data["questions"])
    data["questions"] = [q for q in data["questions"] if q["id"] != question_id]
    
    if len(data["questions"]) < original_count:
        save_dataset(data)
        print(f"✅ Removed {question_id}")
        print(f"   Remaining questions: {len(data['questions'])}")
    else:
        print(f"❌ Question {question_id} not found")

def main():
    parser = argparse.ArgumentParser(description="Manage evaluation dataset")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new Q&A pair")
    add_parser.add_argument("question", help="The question")
    add_parser.add_argument("ground_truth", help="The ground truth answer")
    add_parser.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"])
    
    # List command
    subparsers.add_parser("list", help="List all questions")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a question")
    remove_parser.add_argument("question_id", help="Question ID to remove")
    
    args = parser.parse_args()
    
    if args.command == "add":
        add_question(args.question, args.ground_truth, args.difficulty)
    elif args.command == "list":
        list_questions()
    elif args.command == "remove":
        remove_question(args.question_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()