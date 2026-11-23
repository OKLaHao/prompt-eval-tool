#!/usr/bin/env python3
"""Prompt 评测小工具。

批量跑一组测试用例（prompt + 期望关键词），给模型回答打分，输出 Markdown 报告。
评分规则（全部写死在代码里，不藏着掖着）：
- 得分 = 命中关键词数 / 期望关键词总数（0~1）。
- 通过 = 得分 >= --min-score（默认 0.6）且回答不为空。
- 另外记录三类标记：空回答、疑似拒绝、回答过长（>2000 字）。

用法：
    python3 eval.py                                  # 用 mock 模型跑演示用例
    python3 eval.py --model ollama                   # 用本地 Ollama 模型跑
    python3 eval.py --model ollama --ollama-model qwen2.5:7b
    python3 eval.py --cases my_cases.json --out my_report.md
"""
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from model_client import MockClient, OllamaClient

REFUSAL_WORDS = ["不知道", "无法回答", "作为 AI", "抱歉，我不能", "我无法提供"]
MAX_LEN = 2000


def score_case(case, response):
    """给一条回答打分，返回评分细节。"""
    keywords = case.get("expected_keywords", [])
    hits = [kw for kw in keywords if kw in response]
    misses = [kw for kw in keywords if kw not in hits]
    hit_rate = len(hits) / len(keywords) if keywords else 0.0
    flags = []
    if not response.strip():
        flags.append("空回答")
    if any(w in response for w in REFUSAL_WORDS):
        flags.append("疑似拒绝")
    if len(response) > MAX_LEN:
        flags.append("回答过长")
    return {
        "score": round(hit_rate, 3),
        "hits": hits,
        "misses": misses,
        "flags": flags,
    }


def run(cases, client, min_score):
    """跑完全部用例，返回每条结果。"""
    results = []
    for case in cases:
        start = time.time()
        try:
            response = client.generate(case["prompt"], case.get("id", ""))
            error = ""
        except Exception as e:  # noqa: BLE001 - 评测不能因为一条用例失败就停
            response = ""
            error = str(e)
        elapsed = time.time() - start
        detail = score_case(case, response)
        detail.update({
            "id": case.get("id", ""),
            "category": case.get("category", "未分类"),
            "prompt": case.get("prompt", ""),
            "response": response,
            "latency_s": round(elapsed, 2),
            "error": error,
            "passed": detail["score"] >= min_score and bool(response.strip()),
        })
        results.append(detail)
    return results


def build_report(results, model_name, min_score):
    """把结果拼成 Markdown 报告。"""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_score = sum(r["score"] for r in results) / total if total else 0.0
    avg_latency = sum(r["latency_s"] for r in results) / total if total else 0.0

    lines = [
        "# Prompt 评测报告",
        "",
        f"- 模型：{model_name}",
        f"- 用例总数：{total}，通过：{passed}，通过率：{passed / total * 100:.1f}%",
        f"- 平均分：{avg_score:.3f}，平均耗时：{avg_latency:.2f} 秒",
        f"- 通过标准：得分 >= {min_score} 且回答不为空",
        "",
        "## 按分类",
        "",
        "| 分类 | 总数 | 通过 | 平均分 |",
        "| --- | --- | --- | --- |",
    ]
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        cat_pass = sum(1 for r in rows if r["passed"])
        cat_avg = sum(r["score"] for r in rows) / len(rows)
        lines.append(f"| {cat} | {len(rows)} | {cat_pass} | {cat_avg:.3f} |")
    lines += [
        "",
        "## 明细",
        "",
        "| 用例 | 分类 | 得分 | 命中 | 耗时(秒) | 标记 | 回答摘要 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        excerpt = r["response"].replace("\n", " ")[:40]
        if len(r["response"]) > 40:
            excerpt += "…"
        if r["error"]:
            excerpt = f"调用失败：{r['error'][:30]}"
        flags = "、".join(r["flags"]) if r["flags"] else "-"
        lines.append(
            f"| {r['id']} | {r['category']} | {r['score']} | "
            f"{len(r['hits'])}/{len(r['hits']) + len(r['misses'])} | "
            f"{r['latency_s']} | {flags} | {excerpt} |"
        )
    lines += [
        "",
        "## 评分规则",
        "",
        "- 得分 = 命中关键词数 / 期望关键词总数。",
        "- 标记说明：空回答（模型没返回内容）、疑似拒绝（回答里出现不知道/无法回答等）、"
        "回答过长（超过 2000 字）。",
        "- 关键词是人工写的期望要点，不是模型自己评自己，分数只反映“要点覆盖了多少”。",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Prompt 评测小工具")
    parser.add_argument("--cases", default="cases.json", help="测试用例 JSON 文件")
    parser.add_argument("--model", choices=["mock", "ollama"], default="mock",
                        help="mock=演示假模型，ollama=本地 Ollama 模型")
    parser.add_argument("--ollama-model", default="qwen2.5:1.5b",
                        help="Ollama 模型名，如 qwen2.5:1.5b")
    parser.add_argument("--ollama-host", default="http://localhost:11434",
                        help="Ollama 服务地址")
    parser.add_argument("--min-score", type=float, default=0.6,
                        help="通过分数线，默认 0.6")
    parser.add_argument("--out", default="report.md", help="报告输出路径")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if args.model == "ollama":
        client = OllamaClient(model=args.ollama_model, host=args.ollama_host)
    else:
        client = MockClient()

    results = run(cases, client, args.min_score)
    report = build_report(results, client.name, args.min_score)
    Path(args.out).write_text(report, encoding="utf-8")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg = sum(r["score"] for r in results) / total if total else 0.0
    print(f"模型：{client.name}，用例：{total}，通过：{passed}，"
          f"通过率：{passed / total * 100:.1f}%，平均分：{avg:.3f}")
    print(f"报告已保存到 {args.out}")


if __name__ == "__main__":
    main()
