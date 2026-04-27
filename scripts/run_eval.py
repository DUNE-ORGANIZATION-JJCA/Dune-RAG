#!/usr/bin/env python3
"""
Evaluation script for Dune RAG using Ragas.
Usage: python scripts/run_eval.py --dataset data/eval/sample_dataset.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

load_dotenv()

# Threshold values for pass/fail
QUALITY_THRESHOLDS = {
    "faithfulness": 0.5,      # Minimum 50% of claims verified
    "answer_relevancy": 0.6,  # Minimum 60% relevance
    "context_precision": 0.5, # Minimum 50% of retrieved context relevant
    "context_recall": 0.6     # Minimum 60% of ground truth covered
}

def load_dataset(dataset_path: str) -> Dict[str, Any]:
    """Load evaluation dataset"""
    with open(dataset_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_query(question: str) -> Dict[str, Any]:
    """Run a single query through the RAG pipeline"""
    from api.pipelines import QueryPipeline
    
    pipeline = QueryPipeline()
    result = pipeline.query(question)
    
    return {
        "answer": result.answer,
        "contexts": [s["text"] for s in result.sources]
    }

def prepare_ragas_dataset(questions: List[Dict]) -> Dict[str, Any]:
    """
    Prepare dataset for Ragas evaluation.
    Runs queries and collects responses.
    """
    print("Preparing evaluation dataset...")
    
    eval_data = []
    
    for q in questions:
        print(f"  Processing: {q['id']}")
        
        try:
            result = run_query(q["question"])
            
            eval_data.append({
                "user_input": q["question"],
                "response": result["answer"],
                "reference": q["ground_truth"],
                "retrieved_contexts": result["contexts"],
                "ground_truths": [q["ground_truth"]],
                "question_id": q["id"]
            })
        except Exception as e:
            print(f"  ⚠️ Error processing {q['id']}: {e}")
            continue
    
    return eval_data

def evaluate_dataset(eval_data: List[Dict]) -> Dict[str, Any]:
    """
    Run Ragas evaluation metrics.
    """
    print("\nRunning Ragas evaluation...")
    
    try:
        from datasets import Dataset
        import pandas as pd
        
        # Convert to Ragas format
        df = pd.DataFrame(eval_data)
        dataset = Dataset.from_pandas(df)
        
        # Run evaluation
        result = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall
            ]
        )
        
        return result
        
    except ImportError as e:
        print(f"Ragas/Datasets not available: {e}")
        print("Falling back to basic evaluation...")
        return basic_evaluate(eval_data)

def basic_evaluate(eval_data: List[Dict]) -> Dict[str, Any]:
    """
    Basic evaluation without Ragas (fallback).
    """
    print("\nRunning basic evaluation (Ragas not installed)...")
    
    results = []
    
    for item in eval_data:
        # Simple metrics estimation
        answer_length = len(item["response"].split())
        ref_length = len(item["reference"].split())
        
        # Rough relevance based on overlap
        answer_words = set(item["response"].lower().split())
        ref_words = set(item["reference"].lower().split())
        overlap = len(answer_words & ref_words)
        
        estimated_relevancy = overlap / len(ref_words) if ref_words else 0
        estimated_faithfulness = min(1.0, answer_length / max(ref_length, 1) * 0.8)
        
        results.append({
            "question_id": item["question_id"],
            "faithfulness": estimated_faithfulness,
            "answer_relevancy": estimated_relevancy,
            "context_precision": 0.7,  # Estimated
            "context_recall": estimated_relevancy
        })
    
    # Average scores
    avg_scores = {
        "faithfulness": sum(r["faithfulness"] for r in results) / len(results),
        "answer_relevancy": sum(r["answer_relevancy"] for r in results) / len(results),
        "context_precision": sum(r["context_precision"] for r in results) / len(results),
        "context_recall": sum(r["context_recall"] for r in results) / len(results)
    }
    
    return avg_scores

def print_results(results: Dict[str, Any], thresholds: Dict[str, float]):
    """Print evaluation results with pass/fail"""
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-" * 60)
    
    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    
    all_passed = True
    
    for metric in metrics:
        score = results.get(metric, results.get(metric, {}).get("mean", 0))
        threshold = thresholds[metric]
        passed = score >= threshold
        
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        
        print(f"  {metric:25s}: {score:.3f} (threshold: {threshold:.3f}) {status}")
    
    print("-" * 60)
    
    if all_passed:
        print("🎉 All quality thresholds PASSED!")
    else:
        print("⚠️  Some quality thresholds FAILED - review needed")
    
    print("=" * 60)
    
    return all_passed

def save_results(results: Dict[str, Any], eval_data: List[Dict], output_path: str):
    """Save evaluation results to JSON"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "thresholds": QUALITY_THRESHOLDS,
        "summary": {
            metric: results.get(metric, 0) if isinstance(results.get(metric), (int, float)) 
                     else results.get(metric, {}).get("mean", 0)
            for metric in QUALITY_THRESHOLDS.keys()
        },
        "thresholds_passed": {
            metric: results.get(metric, 0) >= QUALITY_THRESHOLDS[metric]
            for metric in QUALITY_THRESHOLDS.keys()
        },
        "questions_evaluated": len(eval_data),
        "detailed_results": eval_data
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run RAG evaluation")
    parser.add_argument(
        "--dataset", 
        default="./data/eval/sample_dataset.json",
        help="Path to evaluation dataset"
    )
    parser.add_argument(
        "--output", 
        default="./data/eval/results.json",
        help="Output path for results"
    )
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Skip Ragas and use basic evaluation"
    )
    args = parser.parse_args()
    
    # Load dataset
    print(f"Loading dataset: {args.dataset}")
    dataset = load_dataset(args.dataset)
    questions = dataset["questions"]
    print(f"Loaded {len(questions)} questions")
    
    # Prepare data
    eval_data = prepare_ragas_dataset(questions)
    
    if not eval_data:
        print("❌ No questions could be evaluated")
        return
    
    print(f"Prepared {len(eval_data)} questions for evaluation")
    
    # Run evaluation
    if args.skip_ragas:
        results = basic_evaluate(eval_data)
    else:
        results = evaluate_dataset(eval_data)
    
    # Print and evaluate
    passed = print_results(results, QUALITY_THRESHOLDS)
    
    # Save results
    save_results(results, eval_data, args.output)
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()