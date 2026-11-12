"""Agents, tasks and crew assembly + the interactive shopping loop."""
from __future__ import annotations

import json
from typing import Any, Callable

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tasks.task_output import TaskOutput

from ..config import Settings, require_env
from ..schemas import USE_CASES, LaptopList, Requirements
from ..utils import parse_budget, parse_use_case, parse_yes_no
from .crew_tools import CalculatorTool, ProductComparisonTool, WebSearchTool

BUDGET_TOLERANCE = 1.05
BANNER = "=" * 64


def get_llm(settings: Settings) -> LLM:
    return LLM(model=f"openai/{settings.openai_model}", api_key=require_env("OPENAI_API_KEY", "OpenAI LLM"),
               temperature=0.2)


def make_research_guardrail(req: Requirements, excluded: list[str], settings: Settings) -> Callable:
    """Reject research output until >= MIN_OPTIONS valid, in-budget, new laptops are found."""
    state = {"fails": 0}

    def guardrail(output):  # (TaskOutput) -> (bool, Any); unannotated: CrewAI inspects the signature
        try:
            data = output.pydantic or LaptopList.model_validate_json(output.raw)
        except Exception:
            data = None
        banned = {e.lower() for e in excluded}
        valid = [l for l in (data.laptops if data else [])
                 if l.price and l.price <= req.budget * BUDGET_TOLERANCE and l.name.lower() not in banned]
        if len(valid) >= settings.min_options:
            return True, output
        state["fails"] += 1
        if state["fails"] >= settings.max_search_attempts:
            return True, output  # give up gracefully with what we have
        return False, (
            f"Only {len(valid)} valid laptop(s) found; at least {settings.min_options} are required. "
            f"Each must have a price <= {req.budget:.0f} {req.currency} and must not be one of {excluded}. "
            f"Run additional, differently-worded web searches and return a complete list.")

    return guardrail


class ShoppingCrewRunner:
    """Builds a CrewAI crew for each search round and runs the interactive loop."""

    def __init__(self, settings: Settings | None = None, llm: Any = None,
                 input_fn: Callable[[str], str] = input, print_fn: Callable[[str], None] = print):
        self.settings = settings or Settings.load()
        self.llm = llm if llm is not None else get_llm(self.settings)
        self.ask = input_fn
        self.say = print_fn

    # ---------------------------------------------------------------- crew construction
    def build_crew(self, req: Requirements, excluded: list[str]) -> Crew:
        researcher = Agent(
            role="Laptop Research Specialist",
            goal="Find current, real laptop listings with accurate specs and prices that fit the customer's need and budget.",
            backstory="You are a meticulous tech-retail researcher. You only report facts found in search results "
                      "and never invent prices or specifications.",
            tools=[WebSearchTool()], llm=self.llm, verbose=False, allow_delegation=False, max_iter=8,
        )
        analyst = Agent(
            role="Product Comparison Analyst",
            goal="Compare laptops objectively on RAM, processor, storage and price, including discounts.",
            backstory="You are a data-driven analyst who always uses the comparison and calculator tools "
                      "rather than estimating in your head.",
            tools=[ProductComparisonTool(), CalculatorTool()], llm=self.llm, verbose=False,
            allow_delegation=False, max_iter=8,
        )
        advisor = Agent(
            role="Personal Shopping Advisor",
            goal="Recommend the single best laptop for the customer and explain the decision clearly.",
            backstory="You are a friendly, honest shopping advisor who explains trade-offs in plain language.",
            tools=[CalculatorTool()], llm=self.llm, verbose=False, allow_delegation=False, max_iter=6,
        )

        ctx = (f"Customer need: {req.use_case}. Budget: {req.budget:.0f} {req.currency}. "
               f"Extra preferences: {req.notes or 'none'}. Already recommended (exclude): {excluded or 'none'}.")

        research = Task(
            description=(
                f"{ctx}\n\nUse the Web Search Tool (several differently-worded queries) to find at least "
                f"{self.settings.min_options} (ideally 5) suitable laptops. For each, extract: name, current "
                f"price (number), original price if discounted, processor, RAM (GB), storage (GB, 1TB=1000), "
                f"GPU and source URL. Only include laptops with a price within budget. Never invent data."),
            expected_output="A JSON object with a `laptops` list of laptop specs.",
            agent=researcher, output_pydantic=LaptopList,
            guardrail=make_research_guardrail(req, excluded, self.settings),
            guardrail_max_retries=self.settings.max_search_attempts,
        )
        compare = Task(
            description=(
                f"{ctx}\n\nTake the laptops found by the researcher and call the Product Comparison Tool with "
                f"them (use_case='{req.use_case}', budget={req.budget:.0f}, currency='{req.currency}'). Use the "
                f"Calculator Tool for any discount or price-difference figures. Then present the comparison "
                f"table and a short note on how the options differ in RAM, processor, storage and price."),
            expected_output="A Markdown comparison table (at least 3 laptops) with a brief analysis.",
            agent=analyst, context=[research],
        )
        recommend = Task(
            description=(
                f"{ctx}\n\nBased on the analyst's comparison, recommend the single best laptop. Include: the "
                f"pick and its price, why it suits '{req.use_case}' (RAM, processor, storage, price), how it "
                f"compares with the others, savings/discount if any (use the Calculator Tool), and any "
                f"caveat. Under 220 words, Markdown."),
            expected_output="A concise Markdown recommendation.",
            agent=advisor, context=[research, compare],
        )
        return Crew(agents=[researcher, analyst, advisor], tasks=[research, compare, recommend],
                    process=Process.sequential, verbose=False)

    # ---------------------------------------------------------------- user interaction
    def _ask_budget(self, current: tuple[float, str] | None = None) -> tuple[float, str]:
        while True:
            hint = f" [Enter = keep {current[1]} {current[0]:,.0f}]" if current else ""
            ans = self.ask(f"\nWhat is your budget? (e.g. 1200, $1,200, PKR 250k){hint}\n> ").strip()
            if not ans and current:
                return current
            parsed = parse_budget(ans, self.settings.default_currency)
            if parsed:
                return parsed
            self.say("  ! Please enter a positive number, e.g. 1000 or $1,000.")

    def _ask_use_case(self, current: str | None = None) -> str:
        options = "\n".join(f"  {i}. {u.title()}" for i, u in enumerate(USE_CASES, 1))
        while True:
            hint = f" [Enter = keep '{current}']" if current else ""
            ans = self.ask(f"\nWhat do you need the laptop for?\n{options}\nChoose 1-4 or type a name{hint}\n> ").strip()
            if not ans and current:
                return current
            uc = parse_use_case(ans)
            if uc:
                return uc
            self.say("  ! Please choose Gaming, Programming, Office work or University studies.")

    def _ask_more(self) -> bool:
        while True:
            ans = parse_yes_no(self.ask("\nWould you like more recommendations? (yes/no)\n> "))
            if ans is not None:
                return ans
            self.say("  ! Please answer yes or no.")

    def gather_requirements(self) -> Requirements:
        budget, currency = self._ask_budget()
        use_case = self._ask_use_case()
        notes = self.ask("\nAny other preferences? (brand, screen size, weight, battery...) [Enter to skip]\n> ").strip()
        return Requirements(budget=budget, currency=currency, use_case=use_case, notes=notes)

    def refine_requirements(self, req: Requirements) -> Requirements:
        self.say("\nLet's refine the search (press Enter to keep a value).")
        budget, currency = self._ask_budget((req.budget, req.currency))
        use_case = self._ask_use_case(req.use_case)
        notes = self.ask(f"\nPreferences / extra requirements? [Enter = keep '{req.notes or 'none'}']\n> ").strip()
        return Requirements(budget=budget, currency=currency, use_case=use_case, notes=notes or req.notes)

    # ---------------------------------------------------------------- main loop
    def run_round(self, req: Requirements, excluded: list[str]) -> list[str]:
        """Run one search -> compare -> recommend round. Returns names of laptops shown."""
        self.say(f"\n  Got it: {req.use_case} laptop, budget {req.currency} {req.budget:,.0f}. "
                 "My research team is searching the web...")
        crew = self.build_crew(req, excluded)
        result = crew.kickoff()
        research_out, compare_out, rec_out = (t for t in result.tasks_output)
        self.say(f"\n{BANNER}\n COMPARISON\n{BANNER}\n{compare_out.raw}")
        self.say(f"\n{BANNER}\n RECOMMENDATION\n{BANNER}\n{rec_out.raw}\n")
        found = research_out.pydantic.laptops if research_out.pydantic else []
        return [l.name for l in found]

    def run(self) -> None:
        self.say(f"{BANNER}\n AI Shopping Assistant (CrewAI)\n{BANNER}")
        req = self.gather_requirements()
        excluded: list[str] = []
        while True:
            try:
                excluded += self.run_round(req, excluded)
            except Exception as exc:
                self.say(f"\n  ! Something went wrong during this search: {exc}")
            if not self._ask_more():
                break
            req = self.refine_requirements(req)
        self.say("\nThanks for shopping with me. Goodbye!")
