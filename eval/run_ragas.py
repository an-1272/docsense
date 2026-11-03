# eval/run_ragas.py
"""
RAGAS evaluation of DocSense, on the same 15-question set as eval/run_eval.py.

Run from repo root:   python -m eval.run_ragas
Re-score saved answers without re-running the pipeline:
                      python -m eval.run_ragas --reuse eval/ragas_answers_<timestamp>.json

How the 15 questions are split (RAGAS metrics assume an answerable question, so a
correct refusal would otherwise be scored as a failure):
  - 12 in-scope questions
      retrieval quality  -> Context Precision (with reference) + Context Recall, on ALL 12,
                            using the passages retrieval returned even when the confidence
                            gate then blocked the answer (so retrieval is measured separately
                            from the gate)
      answer quality     -> Faithfulness + Response (answer) Relevancy, on the questions
                            the system actually answered
      fallbacks          -> reported as a count (answer blocked by the 0.1 relevance gate)
  - 3 out-of-scope questions -> refusal accuracy (did it decline instead of answering?)

Judge: OpenAI gpt-4o-mini + text-embedding-3-small, the same fixed judge as run_eval.py,
so scores are comparable across backends. The system under test is whatever .env selects
(USE_AZURE / USE_AZURE_SEARCH / USE_PINECONE).
"""
import sys
import types

# --- Compatibility shim (eval only, never imported by the app) ----------------------------
# ragas 0.4.x imports langchain_community.chat_models.vertexai.ChatVertexAI, a module removed
# in langchain-community 0.4. ragas only uses the class in an isinstance() check deciding
# whether an LLM supports n>1 completions. We judge with OpenAI, so a placeholder class is
# safe: nothing is ever an instance of it.
_vertex_mod = 'langchain_community.chat_models.vertexai'
if _vertex_mod not in sys.modules:
    try:
        __import__(_vertex_mod)
    except ModuleNotFoundError:
        _shim = types.ModuleType(_vertex_mod)

        class ChatVertexAI:  # placeholder, see comment above
            pass

        _shim.ChatVertexAI = ChatVertexAI
        sys.modules[_vertex_mod] = _shim
# -------------------------------------------------------------------------------------------

import argparse
import json
import math
import os
import time
import warnings
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings('ignore')

from eval.eval_dataset import EVAL_QUESTIONS, FALLBACK

SOURCE = 'demo_corpus/sample.pdf'   # the corpus the 15 questions were written for
JUDGE_MODEL = 'gpt-4o-mini'
JUDGE_EMBEDDINGS = 'text-embedding-3-small'


def is_refusal(question: str, answer: str) -> bool:
    """
    Did the system decline because the documents don't contain the answer?
    The gate's fixed fallback message is an obvious refusal. But the system prompt also lets
    the model decline conversationally ("The document doesn't seem to mention ..."), which a
    phrase match misses (it scored a correct refusal as a failure on the first run), so any
    other answer is classified by the judge model with a strict yes/no question.
    """
    if 'could not find a reliable answer' in answer.lower():
        return True
    from openai import OpenAI
    verdict = OpenAI().chat.completions.create(
        model=JUDGE_MODEL, temperature=0, max_tokens=3,
        messages=[{'role': 'user', 'content': (
            'A document Q&A assistant was asked a question. Does its answer DECLINE to answer '
            'because the information is not in its documents (rather than providing an answer)? '
            f'Reply with only YES or NO.\n\nQuestion: {question}\nAnswer: {answer}'
        )}],
    ).choices[0].message.content.strip().upper()
    return verdict.startswith('YES')


def collect_answers() -> list[dict]:
    """Run every question through the real pipeline (ask()) and keep what RAGAS needs."""
    from pipeline import ask
    from azure_client import CHAT_MODEL
    rows = []
    for i, item in enumerate(EVAL_QUESTIONS, 1):
        print(f'[{i}/{len(EVAL_QUESTIONS)}] {item["question"][:60]}')
        result = ask(item['question'], rerank_enabled=True, source_filter=[SOURCE])
        rows.append({
            'question': item['question'],
            'answer': result['answer'],
            'contexts': result.get('contexts', []),
            'reference': item['ground_truth'],
            'in_scope': item['ground_truth'] != FALLBACK,
            'refused': is_refusal(item['question'], result['answer']),
            'confidence': result['confidence'],
            'answer_model': CHAT_MODEL,
        })
        if i < len(EVAL_QUESTIONS):
            time.sleep(7)   # Cohere free tier: 10 calls/minute
    return rows


def ragas_score(rows: list[dict], metrics: list) -> list[dict]:
    """Score rows with the given RAGAS metrics; returns one dict of scores per row."""
    if not rows:
        return []
    from ragas import evaluate, EvaluationDataset, RunConfig
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    dataset = EvaluationDataset.from_list([{
        'user_input': r['question'],
        'response': r['answer'],
        'retrieved_contexts': r['contexts'] or [''],
        'reference': r['reference'],
    } for r in rows])
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=LangchainLLMWrapper(ChatOpenAI(model=JUDGE_MODEL, temperature=0)),
        embeddings=LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=JUDGE_EMBEDDINGS)),
        # The default 16 parallel workers produced timeouts -> NaN scores for 5/12 context
        # precision rows on the first run. Fewer workers + more retries trades speed for
        # complete results.
        run_config=RunConfig(max_workers=4, timeout=240, max_retries=8, max_wait=60),
        raise_exceptions=False,
        show_progress=False,
    )
    df = result.to_pandas()
    score_cols = [c for c in df.columns if c not in ('user_input', 'response', 'retrieved_contexts', 'reference')]
    return [{c: (None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), 4))
             for c, v in row.items() if c in score_cols} for row in df.to_dict('records')]


def mean(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def main():
    from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextPrecisionWithReference, LLMContextRecall

    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse', help='saved answers JSON to score instead of re-running the pipeline')
    args = parser.parse_args()
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.reuse:
        rows = json.load(open(args.reuse, encoding='utf-8'))
        print(f'Re-scoring {len(rows)} saved answers from {args.reuse}')
        for r in rows:   # re-classify with the current refusal logic
            r['refused'] = is_refusal(r['question'], r['answer'])
    else:
        print(f'Collecting answers from the pipeline ({len(EVAL_QUESTIONS)} questions)...')
        rows = collect_answers()
        path = f'eval/ragas_answers_{stamp}.json'
        json.dump(rows, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        print(f'Answers saved to {path}')

    in_scope = [r for r in rows if r['in_scope']]
    answered = [r for r in in_scope if not r['refused']]
    out_scope = [r for r in rows if not r['in_scope']]

    print(f'\nScoring with RAGAS (judge: {JUDGE_MODEL})...')
    retrieval = ragas_score(in_scope, [LLMContextPrecisionWithReference(), LLMContextRecall()])
    generation = ragas_score(answered, [Faithfulness(), ResponseRelevancy()])

    for r, s in zip(in_scope, retrieval):
        r.update(s)
    for r, s in zip(answered, generation):
        r.update(s)

    summary = {
        'timestamp': stamp,
        'answer_model': rows[0].get('answer_model') if rows else None,
        'judge': JUDGE_MODEL,
        'context_precision': mean([r.get('llm_context_precision_with_reference') for r in in_scope]),
        'context_recall': mean([r.get('context_recall') for r in in_scope]),
        'faithfulness': mean([r.get('faithfulness') for r in answered]),
        'answer_relevancy': mean([r.get('answer_relevancy') for r in answered]),
        'in_scope_questions': len(in_scope),
        'in_scope_answered': len(answered),
        'in_scope_fallbacks': len(in_scope) - len(answered),
        'refusal_accuracy': (f'{sum(r["refused"] for r in out_scope)}/{len(out_scope)}' if out_scope else None),
    }

    print('\n=== DocSense RAGAS Results ===')
    print(f'Answer model: {summary["answer_model"]} | Judge: {JUDGE_MODEL}')
    print(f'Retrieval (all {len(in_scope)} in-scope questions)')
    print(f'  Context precision: {summary["context_precision"]}')
    print(f'  Context recall:    {summary["context_recall"]}')
    print(f'Answers ({len(answered)} answered; {summary["in_scope_fallbacks"]} blocked by the confidence gate)')
    print(f'  Faithfulness:      {summary["faithfulness"]}')
    print(f'  Answer relevancy:  {summary["answer_relevancy"]}')
    print(f'Out-of-scope refusals: {summary["refusal_accuracy"]}')
    print('\nPer question:')
    for r in rows:
        tag = 'OOS ' if not r['in_scope'] else ('FALLBACK' if r['refused'] else 'ANSWER  ')
        print(f'  [{tag}] {r["question"][:48]:48} | prec={r.get("llm_context_precision_with_reference")} '
              f'rec={r.get("context_recall")} faith={r.get("faithfulness")} rel={r.get("answer_relevancy")}')

    out = f'eval/ragas_results_{stamp}.json'
    json.dump({'summary': summary, 'rows': rows}, open(out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f'\nSaved to {out}')


if __name__ == '__main__':
    main()
