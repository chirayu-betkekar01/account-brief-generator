"""Turn the harness response stream into one result object.

InvokeHarness returns a stream of small events (see docs/learning/phase-4-agent.md). One brief is
several model calls: the model asks for a tool, the harness runs it and streams the result, and the
cycle repeats until the model writes the answer. This module follows that stream and keeps what a
client needs: the final answer, which tools were called with what, what they returned, why each
model call stopped and how many tokens were used.
"""

import json
from dataclasses import dataclass, field

# A stop reason that means "the agent was cut off", not "the agent finished".
TRUNCATING_STOPS = frozenset(
    {"max_tokens", "max_iterations_exceeded", "timeout_exceeded", "max_output_tokens_exceeded"}
)


@dataclass
class BriefRun:
    answer: str = ""
    tool_calls: list = field(default_factory=list)  # [(tool name, arguments dict or raw text)]
    tool_results: list = field(default_factory=list)  # [result text], in call order
    stop_reasons: list = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None

    @property
    def guardrail_intervened(self):
        return "guardrail_intervened" in self.stop_reasons

    @property
    def truncated(self):
        return any(reason in TRUNCATING_STOPS for reason in self.stop_reasons)


def _parse_arguments(text):
    # Keep unparseable input as text rather than dropping it: it is evidence of what the model sent.
    try:
        return json.loads(text) if text else {}
    except ValueError:
        return text


def collect(events):
    """Consume an iterable of stream events (never raises: a failure midway is recorded in .error)."""
    run = BriefRun()
    calls = []  # [name, accumulated argument text]
    open_calls = {}  # contentBlockIndex -> index into calls, within the current message
    results = []  # accumulated result text per tool call
    open_results = {}
    assistant_texts = []  # one entry per assistant message
    in_assistant_message = False

    try:
        for event in events:
            kind = next(iter(event))
            body = event[kind]

            if kind == "messageStart":
                in_assistant_message = body.get("role") == "assistant"
                open_calls, open_results = {}, {}
                if in_assistant_message:
                    assistant_texts.append("")

            elif kind == "contentBlockStart":
                start = body.get("start", {})
                index = body.get("contentBlockIndex")
                if "toolUse" in start:
                    calls.append([start["toolUse"]["name"], ""])
                    open_calls[index] = len(calls) - 1
                elif "toolResult" in start:
                    results.append("")
                    open_results[index] = len(results) - 1

            elif kind == "contentBlockDelta":
                delta = body.get("delta", {})
                index = body.get("contentBlockIndex")
                if "text" in delta and in_assistant_message and assistant_texts:
                    assistant_texts[-1] += delta["text"]
                elif "toolUse" in delta and index in open_calls:
                    calls[open_calls[index]][1] += delta["toolUse"].get("input", "")
                elif "toolResult" in delta and index in open_results:
                    results[open_results[index]] += "".join(part.get("text", "") for part in delta["toolResult"])

            elif kind == "messageStop":
                run.stop_reasons.append(body.get("stopReason"))

            elif kind == "metadata":
                usage = body.get("usage", {})
                run.input_tokens += usage.get("inputTokens", 0)
                run.output_tokens += usage.get("outputTokens", 0)

            elif kind == "runtimeClientError":
                run.error = body.get("message", "runtime client error")
    except Exception as exc:  # noqa: BLE001 - a broken stream must not lose what already arrived
        run.error = f"{type(exc).__name__}: {exc}"

    run.tool_calls = [(name, _parse_arguments(text)) for name, text in calls]
    run.tool_results = results
    # The answer is what the model wrote in its last message; text before a tool call is not it.
    run.answer = assistant_texts[-1] if assistant_texts else ""
    return run
