#!/usr/bin/env python3
"""模型客户端：给评测工具提供统一的调用接口。

- MockClient：内置演示答案的假模型，只用来跑通评测流程，不代表真实模型水平。
- OllamaClient：调用本地 Ollama 服务的真实模型，需要先安装 Ollama 并拉取模型。
  安装：https://ollama.com ，然后执行 `ollama pull qwen2.5:1.5b`。
"""
import json
import time
import urllib.request
import urllib.error


class MockClient:
    """演示用假模型：对内置的演示用例给出固定回答（其中 2 条是错的，
    用来验证评测工具能不能发现坏答案）。"""

    name = "mock"

    _ANSWERS = {
        "qa-01": "中国的首都是北京。",
        "qa-02": "在标准大气压下，水的沸点是 100 摄氏度。",
        "qa-03": "一年有 12 个月。",
        "sum-01": "这段话介绍了杭州和西湖，西湖是杭州的著名景点。",
        "sum-02": "中国高铁运营里程世界第一，速度很快，连接了全国主要城市。",
        "sum-03": "咖啡起源于埃塞俄比亚，是全球最受欢迎的饮品之一。",
        "cls-01": "苹果是水果。",
        "cls-02": "这句话的情感是正面的。",
        "cls-03": "3、7、11、13 都是合数。",
    }

    def generate(self, prompt, case_id=""):
        """返回演示答案。case_id 用来取内置答案，未知用例返回通用回答。"""
        time.sleep(0.01)
        return self._ANSWERS.get(case_id, "这个问题我需要再想一想。")


class OllamaClient:
    """调用本地 Ollama 模型。只用 Python 标准库，不依赖第三方包。"""

    def __init__(self, model="qwen2.5:1.5b", host="http://localhost:11434",
                 timeout=120):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama({model})"

    def generate(self, prompt, case_id=""):
        url = self.host + "/api/generate"
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(
                "连不上 Ollama 服务。请先确认：1) 已安装 Ollama；"
                "2) 已执行 ollama serve；3) 已执行 ollama pull "
                f"{self.model}。原始错误：{e}"
            ) from e
        return data.get("response", "")
