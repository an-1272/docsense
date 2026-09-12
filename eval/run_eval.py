# eval/run_eval.py
# Lightweight RAG evaluation using LLM-as-judge — no RAGAS dependency needed
from openai import OpenAI
from pipeline import ask
from eval.eval_dataset import EVAL_QUESTIONS, FALLBACK
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def score_answer(question: str, answer: str, ground_truth: str, context: str) -> dict:
    """Use GPT-4o-mini as judge to score faithfulness and relevancy."""
    prompt = f"""You are evaluating a RAG system. Score the following answer on two metrics.

Question: {question}
Retrieved Context: {context[:3000]}
Generated Answer: {answer}
Expected Answer: {ground_truth}

Score each metric from 0.0 to 1.0:

1. Faithfulness: Is every claim in the answer supported by the retrieved context? (1.0 = fully grounded, 0.0 = hallucinated)
2. Answer Relevancy: Does the answer actually address the question asked? (1.0 = directly answers, 0.0 = completely off-topic)

Respond in JSON only:
{{"faithfulness": 0.0, "answer_relevancy": 0.0}}"""

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=100,
        messages=[{'role': 'user', 'content': prompt}]
    )
    import re
    text = response.choices[0].message.content.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {'faithfulness': 0.0, 'answer_relevancy': 0.0}


def run_evaluation():
    print("Running DocSense evaluation (LLM-as-judge)...")
    print(f"Total questions: {len(EVAL_QUESTIONS)}\n")

    results = []
    total_faithfulness = 0.0
    total_relevancy = 0.0

    for i, item in enumerate(EVAL_QUESTIONS, 1):
        print(f"[{i}/{len(EVAL_QUESTIONS)}] {item['question'][:60]}...")
        result = ask(item['question'], rerank_enabled=True)

        context = result.get('context', '')

        scores = score_answer(
            item['question'],
            result['answer'],
            item['ground_truth'],
            context
        )

        total_faithfulness += scores['faithfulness']
        total_relevancy += scores['answer_relevancy']

        results.append({
            'question': item['question'],
            'answer': result['answer'],
            'ground_truth': item['ground_truth'],
            'confidence': result['confidence'],
            'faithfulness': scores['faithfulness'],
            'answer_relevancy': scores['answer_relevancy'],
        })

        print(f"  Faithfulness: {scores['faithfulness']:.2f} | Relevancy: {scores['answer_relevancy']:.2f}")

        if i < len(EVAL_QUESTIONS):
            time.sleep(7)  # Cohere free tier: 10 calls/minute

    n = len(EVAL_QUESTIONS)
    avg_faithfulness = total_faithfulness / n
    avg_relevancy = total_relevancy / n

    print(f"\n=== DocSense Evaluation Results ===")
    print(f"Faithfulness:     {avg_faithfulness:.2f} (target > 0.80)")
    print(f"Answer Relevancy: {avg_relevancy:.2f} (target > 0.70)")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "timestamp": timestamp,
        "summary": {
            "faithfulness": round(avg_faithfulness, 3),
            "answer_relevancy": round(avg_relevancy, 3),
            "total_questions": n,
        },
        "details": results
    }
    with open(f"eval/results_{timestamp}.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nDetailed results saved to eval/results_{timestamp}.json")

    return output


if __name__ == "__main__":
    run_evaluation()