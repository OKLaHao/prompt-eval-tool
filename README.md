# Prompt 评测小工具

批量跑一组测试用例，给大模型回答打分，输出一份 Markdown 评测报告。

## 为什么做这个

AI 产品、AI 运营每天都要干的一件事，就是评测模型回答得好不好：收集一批问题，
看模型答对了多少、哪里答错了、哪些问题要反馈给算法。这个工具就是把这件事自动化：
准备好用例，一条命令跑完，出报告。

## 它能做什么

- 批量调用模型回答测试用例（支持本地 Ollama 模型，或自带 mock 演示模型）。
- 按人工写的期望关键词打分：得分 = 命中关键词数 / 期望关键词总数。
- 记录三类问题标记：空回答、疑似拒绝、回答过长。
- 输出 Markdown 报告：总通过率、平均分、按分类统计、每条用例明细。

## 快速开始

只需要 Python 3.9 以上，不需要装任何第三方包。

```bash
# 1. 用自带的 mock 模型跑演示用例（不用装任何模型）
python3 eval.py

# 2. 用本地 Ollama 模型跑（需要先装 Ollama，见下）
python3 eval.py --model ollama
python3 eval.py --model ollama --ollama-model qwen2.5:7b
```

跑完会在当前目录生成 `report.md`，终端也会打印一行汇总。

## 用本地 Ollama 模型

1. 安装 Ollama：https://ollama.com
2. 拉一个模型（免费，跑在自己电脑上，不花钱）：
   ```bash
   ollama pull qwen2.5:1.5b
   ```
3. 跑评测：
   ```bash
   python3 eval.py --model ollama --ollama-model qwen2.5:1.5b
   ```

## 自己写用例

`cases.json` 是一个 JSON 数组，每条用例三个字段：

```json
{"id": "qa-01", "category": "问答", "prompt": "中国的首都是哪里？", "expected_keywords": ["北京"]}
```

- `id`：用例编号，报告里按它展示。
- `category`：分类，报告里会按分类汇总。
- `prompt`：发给模型的提示词。
- `expected_keywords`：期望要点，回答里出现就算命中。

写自己的用例文件，然后：

```bash
python3 eval.py --cases my_cases.json --out my_report.md
```

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--cases` | cases.json | 测试用例文件 |
| `--model` | mock | mock=演示假模型，ollama=本地 Ollama 模型 |
| `--ollama-model` | qwen2.5:1.5b | Ollama 模型名 |
| `--ollama-host` | http://localhost:11434 | Ollama 服务地址 |
| `--min-score` | 0.6 | 通过分数线 |
| `--out` | report.md | 报告输出路径 |

## 评分规则（写在代码里，不藏着掖着）

- 得分 = 命中关键词数 / 期望关键词总数，0~1。
- 通过 = 得分 >= 通过分数线，且回答不为空。
- 关键词是人工写的期望要点，不是模型自己评自己，分数只反映“要点覆盖了多少”。

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `eval.py` | 主程序：跑用例、打分、生成报告 |
| `model_client.py` | 模型客户端：MockClient（演示用）、OllamaClient（本地模型） |
| `cases.json` | 演示用例：9 条，问答 / 摘要 / 分类各 3 条 |
| `report.md` | 跑完生成的报告（示例） |
