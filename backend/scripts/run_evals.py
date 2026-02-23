import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Ensure backend imports work
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))

from backend.app.rag import LegalRAG, analyze_query_for_filters, LLM_MODEL
from openai import AsyncOpenAI

dataset_path = ROOT_DIR / "backend" / "tests" / "eval_dataset.json"
reports_dir = ROOT_DIR / "backend" / "logs" / "eval_reports"
reports_dir.mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "backend" / "tests").mkdir(parents=True, exist_ok=True)

async def evaluate():
    print("Loading test cases...")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    print("Initializing LegalRAG...")
    rag = LegalRAG()
    
    results = []
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: OPENROUTER_API_KEY NOT FOUND!")
        return

    llm_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    total_faithfulness = 0.0
    total_relevance = 0.0
    total_retrieval = 0.0
    
    print("\n--- Starting Evaluation Loop ---")
    for item in dataset:
        question = item["question"]
        ground_truth = item["ground_truth"]
        expected_act = item["expected_act"]
        
        print(f"\nEvaluating: {question}")
        
        # 1. Expand query using the router (Optional but matches real pipeline)
        try:
            filters = await analyze_query_for_filters(question, rag.async_client, LLM_MODEL)
            search_query = filters.get("expanded_query", question)
        except Exception:
            search_query = question
        print(f"  > Expanded Query: {search_query}")
        
        # 2. Invoke RAG
        # Note: rag.query is synchronous. It retrieves, builds context, and generates answer.
        try:
            rag_response = rag.query(question)
        except Exception as e:
            print(f"  > RAG execution failed: {e}")
            continue

        answer = rag_response.get("answer", "")
        # Extract context from debug_metadata
        context_str = rag_response.get("debug_metadata", {}).get("context_used", "")
        
        # Extract retrieved acts from citations list
        citations = rag_response.get("citations", [])
        retrieved_acts = list(set([c.get("act", "") for c in citations]))
        
        # 3. Use LLM as Judge
        judge_prompt = f"""You are an expert legal evaluator. Your task is to mathematically grade the AI's answer strictly on a scale of 0.0 or 1.0 against three metrics based on the provided inputs.

Question: {question}
Ground Truth: {ground_truth}
Retrieved Context used by AI: 
{context_str}

AI Answer to Evaluate: 
{answer}

Expected Act to retrieve from: {expected_act}
Retrieved Acts: {retrieved_acts}

Metrics to grade:
1. "faithfulness": 1.0 if the AI Answer is entirely and strictly supported by the Retrieved Context. 0.0 if the AI hallucinated or included facts not present in the context.
2. "relevance": 1.0 if the AI Answer directly addresses the Question while matching the semantic meaning of the Ground Truth. 0.0 if irrelevant.
3. "retrieval_success": 1.0 if the expected legal Act ('{expected_act}') or an obvious acronym of it is clearly present within the Retrieved Acts list. 0.0 otherwise.

Output ONLY a valid JSON object with the keys "faithfulness", "relevance", and "retrieval_success". Do not include markdown block formatting.
Example Output:
{{
    "faithfulness": 1.0,
    "relevance": 1.0,
    "retrieval_success": 1.0
}}
"""
        try:
            response = await llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.0,
                max_tokens=150
            )
            content = response.choices[0].message.content
            clean_content = content.replace("```json", "").replace("```", "").strip()
            if "{" in clean_content and "}" in clean_content:
                clean_content = clean_content[clean_content.find("{"):clean_content.rfind("}")+1]
            scores = json.loads(clean_content)
        except Exception as e:
            print(f"  > Judge logic failed: {e}")
            scores = {"faithfulness": 0.0, "relevance": 0.0, "retrieval_success": 0.0}
            
        faithfulness = float(scores.get("faithfulness", 0.0))
        relevance = float(scores.get("relevance", 0.0))
        retrieval_success = float(scores.get("retrieval_success", 0.0))
        
        print(f"  > Faithfulness: {faithfulness} | Relevance: {relevance} | Retrieval: {retrieval_success}")
        
        total_faithfulness += faithfulness
        total_relevance += relevance
        total_retrieval += retrieval_success
        
        results.append({
            "question": question,
            "faithfulness": faithfulness,
            "relevance": relevance,
            "retrieval_success": retrieval_success,
            "answer": answer,
            "expected_act": expected_act,
            "retrieved_acts": retrieved_acts,
            "context_used": context_str
        })
        
    num_qs = len(dataset)
    if num_qs == 0:
        return
        
    avg_faithfulness = total_faithfulness / num_qs
    avg_relevance = total_relevance / num_qs
    avg_retrieval = total_retrieval / num_qs
    
    print("\n========================================")
    print(f"System Faithfulness Score: {avg_faithfulness * 100:.2f}%")
    print(f"System Relevance Score:  {avg_relevance * 100:.2f}%")
    print(f"System Retrieval Score:  {avg_retrieval * 100:.2f}%")
    print("========================================")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "aggregate_scores": {
            "faithfulness": avg_faithfulness,
            "relevance": avg_relevance,
            "retrieval_success": avg_retrieval
        },
        "details": results
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = reports_dir / f"eval_report_{timestamp}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    print(f"\n[SUCCESS] CI/CD Report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(evaluate())
