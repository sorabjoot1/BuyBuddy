# AI Shopping Assistant - CrewAI

A terminal shopping assistant that asks for your budget and purpose (Gaming / Programming / Office work /
University studies), has a crew of agents search the web for laptops, compare at least three options and
recommend the best one, then offers more recommendations with updated requirements.

## Workflow
```
START -> Get Requirements (CLI) -> Crew [ Research -> Compare -> Recommend ]
      -> User satisfied? --no--> Update requirements -> Crew (new search, excludes already-shown laptops)
                         \-yes-> END
```

## Agents / tasks (`shopping_assistant/crew/crew.py`)
| Agent | Tools | Task |
|---|---|---|
| Laptop Research Specialist | Web Search Tool | Finds laptops + specs (structured `LaptopList`). A task **guardrail** forces re-search until >= 3 valid, in-budget, new laptops are found (bounded by `MAX_SEARCH_ATTEMPTS`) |
| Product Comparison Analyst | Product Comparison Tool, Calculator Tool | Compares RAM, processor, storage, price, discounts |
| Personal Shopping Advisor | Calculator Tool | Recommends the single best option |

Tools: `shopping_assistant/crew/crew_tools.py` (wrapping `shopping_assistant/tools/`).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then fill in OPENAI_API_KEY and TAVILY_API_KEY
python main.py
```
Python 3.10-3.13 required.

## Tests (no API keys needed)
```bash
pytest -q
```

## Layout
```
main.py
shopping_assistant/
  config.py  schemas.py  utils.py  cli.py
  tools/   (web_search, calculator, comparison)
  crew/    (crew_tools, crew)
tests/
```

## Notes
- Budgets accept `1200`, `$1,200`, `PKR 250k`, etc.
- Product data comes from web search excerpts, so specs/prices can be stale; verify before buying.
- CrewAI may send anonymous telemetry; set `CREWAI_DISABLE_TELEMETRY=true` in `.env` to opt out.
