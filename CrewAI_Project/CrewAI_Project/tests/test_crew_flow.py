"""Offline end-to-end test of the CrewAI pipeline using a scripted LLM and a fake search."""
import json

from crewai import BaseLLM

from shopping_assistant.config import Settings
from shopping_assistant.crew import ShoppingCrewRunner
from shopping_assistant.crew import crew_tools

LAPTOPS = {"laptops": [
    {"name": "Acer Nitro 5", "price": 950, "processor": "Intel Core i5-12500H", "ram_gb": 16, "storage_gb": 512, "gpu": "RTX 3050"},
    {"name": "Lenovo LOQ", "price": 1000, "original_price": 1200, "processor": "Ryzen 7 7840HS", "ram_gb": 16, "storage_gb": 512, "gpu": "RTX 4050"},
    {"name": "ASUS TUF A15", "price": 1100, "processor": "Ryzen 7 7735HS", "ram_gb": 16, "storage_gb": 1000, "gpu": "RTX 4060"},
]}


class ScriptedLLM(BaseLLM):
    def __init__(self):
        super().__init__(model="scripted")

    def supports_function_calling(self) -> bool:
        return False

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kw):
        text = messages if isinstance(messages, str) else "\n".join(str(m.get("content", "")) for m in messages)
        if "Observation:" in text.split("Begin!")[-1] or "Observation:" in text[-3000:]:
            observed = True
        else:
            observed = False
        if "Laptop Research Specialist" in text:
            if not observed:
                return 'Thought: search\nAction: Web Search Tool\nAction Input: {"query": "best gaming laptops"}'
            return "Thought: I now know the final answer\nFinal Answer: " + json.dumps(LAPTOPS)
        if "Product Comparison Analyst" in text:
            if not observed:
                args = {"laptops": LAPTOPS["laptops"], "use_case": "gaming", "budget": 1200, "currency": "USD"}
                return f"Thought: compare\nAction: Product Comparison Tool\nAction Input: {json.dumps(args)}"
            return "Thought: I now know the final answer\nFinal Answer: ANALYSIS TABLE"
        return "Thought: I now know the final answer\nFinal Answer: **Best pick: Lenovo LOQ**"


def test_full_round(monkeypatch, capsys):
    monkeypatch.setattr(crew_tools, "_web_search",
                        lambda q, **k: [{"title": "t", "url": "https://x", "content": "laptops"}])
    out = []
    answers = iter(["$1,200", "1", "", "no"])
    runner = ShoppingCrewRunner(Settings.load(), llm=ScriptedLLM(),
                                input_fn=lambda _: next(answers), print_fn=out.append)
    runner.run()
    text = "\n".join(out)
    assert "RECOMMENDATION" in text and "Lenovo LOQ" in text
    assert "Goodbye" in text
