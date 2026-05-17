# Agent Patterns Reference

Requires: `openai-agents>=0.0.1`, Python 3.11+

---

## Table of Contents
1. [Agents as Tools (static)](#1-agents-as-tools-static)
2. [Agents as Tools (with streaming)](#2-agents-as-tools-with-streaming)
3. [Parallelization](#3-parallelization)
4. [Deterministic Workflow](#4-deterministic-workflow)
5. [Routing / Triage Handoffs](#5-routing--triage-handoffs)
6. [Human in the Loop (HITL)](#6-human-in-the-loop-hitl)
7. [Input Guardrails](#7-input-guardrails)
8. [Output Guardrails](#8-output-guardrails)
9. [LLM as a Judge](#9-llm-as-a-judge)
10. [Dynamic System Prompt](#10-dynamic-system-prompt)
11. [Function Tools](#11-function-tools)
12. [Lifecycle Hooks](#12-lifecycle-hooks)
13. [Handoff Message Filtering](#13-handoff-message-filtering)

---

## 1. Agents as Tools (static)

Sub-agents exposed as tools to an orchestrator. The orchestrator picks which agents to call; results are synthesized.

```python
import asyncio
from agents import Agent, ItemHelpers, MessageOutputItem, Runner, trace

spanish_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
    handoff_description="An english to spanish translator",
)

french_agent = Agent(
    name="french_agent",
    instructions="You translate the user's message to French",
    handoff_description="An english to french translator",
)

italian_agent = Agent(
    name="italian_agent",
    instructions="You translate the user's message to Italian",
    handoff_description="An english to italian translator",
)

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=(
        "You are a translation agent. You use the tools given to you to translate."
        "If asked for multiple translations, you call the relevant tools in order."
        "You never translate on your own, you always use the provided tools."
    ),
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate the user's message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate the user's message to French",
        ),
        italian_agent.as_tool(
            tool_name="translate_to_italian",
            tool_description="Translate the user's message to Italian",
        ),
    ],
)

synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions="You inspect translations, correct them if needed, and produce a final concatenated response.",
)


async def main():
    with trace("Orchestrator evaluator"):
        orchestrator_result = await Runner.run(orchestrator_agent, "Translate 'Hello, world!' to French and Spanish.")

        for item in orchestrator_result.new_items:
            if isinstance(item, MessageOutputItem):
                text = ItemHelpers.text_message_output(item)
                if text:
                    print(f"  - Translation step: {text}")

        synthesizer_result = await Runner.run(
            synthesizer_agent, orchestrator_result.to_input_list()
        )

    print(f"\n\nFinal response:\n{synthesizer_result.final_output}")
```

---

## 2. Agents as Tools (with streaming)

Use `on_stream` to receive streaming events from sub-agents invoked as tools.

```python
import asyncio
from agents import Agent, AgentToolStreamEvent, ModelSettings, Runner, function_tool, trace


@function_tool(
    name_override="billing_status_checker",
    description_override="Answer questions about customer billing status.",
)
def billing_status_checker(customer_id: str | None = None, question: str = "") -> str:
    normalized = question.lower()
    if "bill" in normalized or "billing" in normalized:
        return f"This customer (ID: {customer_id})'s bill is $100"
    return "I can only answer questions about billing."


def handle_stream(event: AgentToolStreamEvent) -> None:
    stream = event["event"]
    tool_call = event.get("tool_call")
    tool_call_info = tool_call.call_id if tool_call is not None else "unknown"
    print(f"[stream] agent={event['agent'].name} call={tool_call_info} type={stream.type}")


async def main() -> None:
    with trace("Agents as tools streaming example"):
        billing_agent = Agent(
            name="Billing Agent",
            instructions="You are a billing agent that answers billing questions.",
            model_settings=ModelSettings(tool_choice="required"),
            tools=[billing_status_checker],
        )

        billing_agent_tool = billing_agent.as_tool(
            tool_name="billing_agent",
            tool_description="You are a billing agent that answers billing questions.",
            on_stream=handle_stream,
        )

        main_agent = Agent(
            name="Customer Support Agent",
            instructions=(
                "You are a customer support agent. Always call the billing agent to answer billing "
                "questions and return the billing agent response to the user."
            ),
            tools=[billing_agent_tool],
        )

        result = await Runner.run(
            main_agent,
            "Hello, my customer ID is ABC123. How much is my bill for this month?",
        )

    print(f"\nFinal response:\n{result.final_output}")
```

---

## 3. Parallelization

Run the same agent multiple times concurrently with `asyncio.gather`, then pick the best result.

```python
import asyncio
from agents import Agent, ItemHelpers, Runner, trace

spanish_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
)

translation_picker = Agent(
    name="translation_picker",
    instructions="You pick the best Spanish translation from the given options.",
)


async def main():
    msg = "Good morning!"

    with trace("Parallel translation"):
        res_1, res_2, res_3 = await asyncio.gather(
            Runner.run(spanish_agent, msg),
            Runner.run(spanish_agent, msg),
            Runner.run(spanish_agent, msg),
        )

        outputs = [
            ItemHelpers.text_message_outputs(res_1.new_items),
            ItemHelpers.text_message_outputs(res_2.new_items),
            ItemHelpers.text_message_outputs(res_3.new_items),
        ]

        translations = "\n\n".join(outputs)

        best_translation = await Runner.run(
            translation_picker,
            f"Input: {msg}\n\nTranslations:\n{translations}",
        )

    print(f"Best translation: {best_translation.final_output}")
```

---

## 4. Deterministic Workflow

Gate the pipeline on structured output from an intermediate step.

```python
import asyncio
from pydantic import BaseModel
from agents import Agent, Runner, trace

story_outline_agent = Agent(
    name="story_outline_agent",
    instructions="Generate a very short story outline based on the user's input.",
)


class OutlineCheckerOutput(BaseModel):
    good_quality: bool
    is_scifi: bool


outline_checker_agent = Agent(
    name="outline_checker_agent",
    instructions="Read the given story outline, and judge the quality. Also, determine if it is a scifi story.",
    output_type=OutlineCheckerOutput,
)

story_agent = Agent(
    name="story_agent",
    instructions="Write a short story based on the given outline.",
    output_type=str,
)


async def main():
    with trace("Deterministic story flow"):
        outline_result = await Runner.run(story_outline_agent, "Write a short sci-fi story.")
        print("Outline generated")

        outline_checker_result = await Runner.run(
            outline_checker_agent,
            outline_result.final_output,
        )

        assert isinstance(outline_checker_result.final_output, OutlineCheckerOutput)
        if not outline_checker_result.final_output.good_quality:
            print("Outline is not good quality, stopping.")
            return

        if not outline_checker_result.final_output.is_scifi:
            print("Not a scifi story, stopping.")
            return

        story_result = await Runner.run(story_agent, outline_result.final_output)
        print(f"Story: {story_result.final_output}")
```

---

## 5. Routing / Triage Handoffs

A triage agent routes to specialist agents via `handoffs`. Stream responses token by token.

```python
import asyncio
import uuid
from openai.types.responses import ResponseContentPartDoneEvent, ResponseTextDeltaEvent
from agents import Agent, RawResponsesStreamEvent, Runner, TResponseInputItem, trace

french_agent = Agent(name="french_agent", instructions="You only speak French")
spanish_agent = Agent(name="spanish_agent", instructions="You only speak Spanish")
english_agent = Agent(name="english_agent", instructions="You only speak English")

triage_agent = Agent(
    name="triage_agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[french_agent, spanish_agent, english_agent],
)


async def main():
    conversation_id = str(uuid.uuid4().hex[:16])
    inputs: list[TResponseInputItem] = [{"content": "Hello, how do I say good evening in French?", "role": "user"}]
    agent = triage_agent

    with trace("Routing example", group_id=conversation_id):
        result = Runner.run_streamed(agent, input=inputs)
        async for event in result.stream_events():
            if not isinstance(event, RawResponsesStreamEvent):
                continue
            data = event.data
            if isinstance(data, ResponseTextDeltaEvent):
                print(data.delta, end="", flush=True)
            elif isinstance(data, ResponseContentPartDoneEvent):
                print("\n")
```

---

## 6. Human in the Loop (HITL)

Tools with `needs_approval=True` pause execution. Serialize state, approve/reject, then resume.

```python
import asyncio
import json
from pathlib import Path
from agents import Agent, Runner, RunState, function_tool


@function_tool
async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is sunny"


async def _needs_temperature_approval(_ctx, params, _call_id) -> bool:
    return "Oakland" in params.get("city", "")


@function_tool(needs_approval=_needs_temperature_approval)
async def get_temperature(city: str) -> str:
    """Get the temperature for a given city."""
    return f"The temperature in {city} is 20° Celsius"


agent = Agent(
    name="Weather Assistant",
    instructions="Answer questions about weather and temperature using the available tools.",
    tools=[get_weather, get_temperature],
)

RESULT_PATH = Path(".cache/hitl_result.json")


async def main():
    result = await Runner.run(agent, "What is the weather and temperature in Oakland?")

    while result.interruptions:
        print(f"\n{len(result.interruptions)} tool(s) need approval")

        # Serialize state (can be sent across processes/network)
        state = result.to_state()
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with RESULT_PATH.open("w") as f:
            json.dump(state.to_json(), f)

        # Reload and process approvals
        with RESULT_PATH.open() as f:
            stored = json.load(f)
        state = await RunState.from_json(agent, stored)

        for interruption in result.interruptions:
            print(f"  Tool: {interruption.name}, Args: {interruption.arguments}")
            confirmed = input("Approve? (y/n): ").strip().lower() == "y"
            if confirmed:
                state.approve(interruption)
            else:
                state.reject(interruption)

        result = await Runner.run(agent, state)

    print(f"\nFinal Output:\n{result.final_output}")
```

---

## 7. Input Guardrails

Run a check in parallel with the agent. Raise `InputGuardrailTripwireTriggered` to block.

```python
import asyncio
from pydantic import BaseModel
from agents import (
    Agent, GuardrailFunctionOutput, InputGuardrailTripwireTriggered,
    RunContextWrapper, Runner, TResponseInputItem, input_guardrail,
)


class MathHomeworkOutput(BaseModel):
    reasoning: str
    is_math_homework: bool


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking you to do their math homework.",
    output_type=MathHomeworkOutput,
)


@input_guardrail
async def math_guardrail(
    context: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=context.context)
    final_output = result.final_output_as(MathHomeworkOutput)
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=final_output.is_math_homework,
    )


async def main():
    agent = Agent(
        name="Customer support agent",
        instructions="You are a customer support agent.",
        input_guardrails=[math_guardrail],
    )

    input_data: list[TResponseInputItem] = []

    for user_input in ["What's the capital of California?", "Can you help me solve for x: 2x + 5 = 11"]:
        input_data.append({"role": "user", "content": user_input})
        try:
            result = await Runner.run(agent, input_data)
            print(result.final_output)
            input_data = result.to_input_list()
        except InputGuardrailTripwireTriggered:
            message = "Sorry, I can't help you with your math homework."
            print(message)
            input_data.append({"role": "assistant", "content": message})
```

---

## 8. Output Guardrails

Check the final output. Raise `OutputGuardrailTripwireTriggered` if it violates policy.

```python
import asyncio
import json
from pydantic import BaseModel, Field
from agents import (
    Agent, GuardrailFunctionOutput, OutputGuardrailTripwireTriggered,
    RunContextWrapper, Runner, output_guardrail,
)


class MessageOutput(BaseModel):
    reasoning: str = Field(description="Thoughts on how to respond to the user's message")
    response: str = Field(description="The response to the user's message")
    user_name: str | None = Field(description="The name of the user, if known")


@output_guardrail
async def sensitive_data_check(
    context: RunContextWrapper, agent: Agent, output: MessageOutput
) -> GuardrailFunctionOutput:
    phone_number_in_response = "650" in output.response
    phone_number_in_reasoning = "650" in output.reasoning
    return GuardrailFunctionOutput(
        output_info={
            "phone_number_in_response": phone_number_in_response,
            "phone_number_in_reasoning": phone_number_in_reasoning,
        },
        tripwire_triggered=phone_number_in_response or phone_number_in_reasoning,
    )


agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
    output_type=MessageOutput,
    output_guardrails=[sensitive_data_check],
)


async def main():
    await Runner.run(agent, "What's the capital of California?")
    print("First message passed")

    try:
        result = await Runner.run(agent, "My phone number is 650-123-4567. Where do you think I live?")
        print(f"Guardrail didn't trip - output: {json.dumps(result.final_output.model_dump(), indent=2)}")
    except OutputGuardrailTripwireTriggered as e:
        print(f"Guardrail tripped. Info: {e.guardrail_result.output.output_info}")
```

---

## 9. LLM as a Judge

Iterative refinement loop: generate → evaluate → regenerate with feedback until the judge passes.

```python
import asyncio
from dataclasses import dataclass
from typing import Literal
from agents import Agent, ItemHelpers, Runner, TResponseInputItem, trace

story_outline_generator = Agent(
    name="story_outline_generator",
    instructions=(
        "You generate a very short story outline based on the user's input. "
        "If there is any feedback provided, use it to improve the outline."
    ),
)


@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "needs_improvement", "fail"]


evaluator = Agent[None](
    name="evaluator",
    instructions=(
        "You evaluate a story outline and decide if it's good enough. "
        "If not, provide feedback. Never give a pass on the first try. "
        "After 5 attempts, you can give it a pass if good enough."
    ),
    output_type=EvaluationFeedback,
)


async def main() -> None:
    input_items: list[TResponseInputItem] = [{"content": "A detective story in space.", "role": "user"}]
    latest_outline: str | None = None

    with trace("LLM as a judge"):
        while True:
            story_outline_result = await Runner.run(story_outline_generator, input_items)
            input_items = story_outline_result.to_input_list()
            latest_outline = ItemHelpers.text_message_outputs(story_outline_result.new_items)
            print("Story outline generated")

            evaluator_result = await Runner.run(evaluator, input_items)
            result: EvaluationFeedback = evaluator_result.final_output

            print(f"Evaluator score: {result.score}")
            if result.score == "pass":
                print("Story outline approved.")
                break

            input_items.append({"content": f"Feedback: {result.feedback}", "role": "user"})

    print(f"Final story outline: {latest_outline}")
```

---

## 10. Dynamic System Prompt

Pass a callable as `instructions` — it receives the run context and returns the prompt string.

```python
import asyncio
import random
from dataclasses import dataclass
from typing import Literal
from agents import Agent, RunContextWrapper, Runner


@dataclass
class CustomContext:
    style: Literal["haiku", "pirate", "robot"]


def custom_instructions(run_context: RunContextWrapper[CustomContext], agent: Agent[CustomContext]) -> str:
    context = run_context.context
    if context.style == "haiku":
        return "Only respond in haikus."
    elif context.style == "pirate":
        return "Respond as a pirate."
    else:
        return "Respond as a robot and say 'beep boop' a lot."


agent = Agent(name="Chat agent", instructions=custom_instructions)


async def main():
    context = CustomContext(style=random.choice(["haiku", "pirate", "robot"]))
    print(f"Using style: {context.style}\n")
    result = await Runner.run(agent, "Tell me a joke.", context=context)
    print(f"Assistant: {result.final_output}")
```

---

## 11. Function Tools

Use `@function_tool` to expose Python functions. Type annotations → JSON schema automatically.

```python
import asyncio
from typing import Annotated
from pydantic import BaseModel, Field
from agents import Agent, Runner, function_tool


class Weather(BaseModel):
    city: str = Field(description="The city name")
    temperature_range: str = Field(description="The temperature range in Celsius")
    conditions: str = Field(description="The weather conditions")


@function_tool
def get_weather(city: Annotated[str, "The city to get the weather for"]) -> Weather:
    """Get the current weather information for a specified city."""
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")


agent = Agent(name="Hello world", instructions="You are a helpful agent.", tools=[get_weather])


async def main():
    result = await Runner.run(agent, input="What's the weather in Tokyo?")
    print(result.final_output)
```

---

## 12. Lifecycle Hooks

`RunHooks` gives callbacks at every stage of execution. `AgentHooks` scopes callbacks to a specific agent.

```python
import asyncio
import random
from typing import Any, Optional, cast
from pydantic import BaseModel
from agents import (
    Agent, AgentHookContext, AgentHooks, RunContextWrapper, RunHooks, Runner, Tool, Usage, function_tool,
)
from agents.items import ModelResponse, TResponseInputItem
from agents.tool_context import ToolContext


class ExampleHooks(RunHooks):
    def __init__(self):
        self.event_counter = 0

    async def on_agent_start(self, context: AgentHookContext, agent: Agent) -> None:
        self.event_counter += 1
        print(f"### {self.event_counter}: Agent {agent.name} started. Usage: {context.usage.total_tokens} tokens")

    async def on_llm_end(self, context: RunContextWrapper, agent: Agent, response: ModelResponse) -> None:
        self.event_counter += 1
        print(f"### {self.event_counter}: LLM ended. Usage: {context.usage.total_tokens} tokens")

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        self.event_counter += 1
        tool_context = cast(ToolContext[Any], context)
        print(f"### {self.event_counter}: Tool {tool.name} started. args={tool_context.tool_arguments}")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        self.event_counter += 1
        print(f"### {self.event_counter}: Tool {tool.name} finished. result={result}")

    async def on_handoff(self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent) -> None:
        self.event_counter += 1
        print(f"### {self.event_counter}: Handoff from {from_agent.name} to {to_agent.name}")


hooks = ExampleHooks()


@function_tool
def random_number(max: int) -> int:
    """Generate a random number from 0 to max."""
    return random.randint(0, max)


@function_tool
def multiply_by_two(x: int) -> int:
    """Return x times two."""
    return x * 2


class FinalResult(BaseModel):
    number: int


multiply_agent = Agent(
    name="Multiply Agent",
    instructions="Multiply the number by 2 and then return the final result.",
    tools=[multiply_by_two],
    output_type=FinalResult,
)

start_agent = Agent(
    name="Start Agent",
    instructions="Generate a random number. If it's even, stop. If it's odd, hand off to the multiplier agent.",
    tools=[random_number],
    output_type=FinalResult,
    handoffs=[multiply_agent],
)


async def main() -> None:
    await Runner.run(start_agent, hooks=hooks, input="Generate a random number between 0 and 50.")
    print("Done!")
```

---

## 13. Handoff Message Filtering

Use `input_filter` on `handoff()` to strip or reshape history before the receiving agent sees it.

```python
import asyncio
import json
from agents import Agent, HandoffInputData, Runner, function_tool, handoff, trace
from agents.extensions import handoff_filters


@function_tool
def random_number_tool(max: int) -> int:
    """Return a random integer between 0 and the given maximum."""
    import random
    return random.randint(0, max)


def spanish_handoff_message_filter(handoff_message_data: HandoffInputData) -> HandoffInputData:
    # Remove tool-related messages from history
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)

    # Also strip the first two items for demonstration
    history = (
        tuple(handoff_message_data.input_history[2:])
        if isinstance(handoff_message_data.input_history, tuple)
        else handoff_message_data.input_history
    )

    return HandoffInputData(
        input_history=history,
        pre_handoff_items=tuple(handoff_message_data.pre_handoff_items),
        new_items=tuple(handoff_message_data.new_items),
    )


first_agent = Agent(
    name="Assistant",
    instructions="Be extremely concise.",
    tools=[random_number_tool],
)

spanish_agent = Agent(
    name="Spanish Assistant",
    instructions="You only speak Spanish and are extremely concise.",
    handoff_description="A Spanish-speaking assistant.",
)

second_agent = Agent(
    name="Assistant",
    instructions="Be helpful. If the user speaks Spanish, handoff to the Spanish assistant.",
    handoffs=[handoff(spanish_agent, input_filter=spanish_handoff_message_filter)],
)
```
