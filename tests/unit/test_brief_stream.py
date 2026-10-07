"""Parsing the harness response stream into one result object.

The events below have the same shape as the ones the live harness sent on 2026-10-07 (see
docs/learning/phase-4-agent.md). Text before a tool call is not part of the answer; only the text of
the last assistant message is.
"""

import pytest

from brief_stream import collect


def _tool_round(tool_use_id, name, input_json, result_chunks):
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {"toolUseId": tool_use_id, "name": name}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": input_json}}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "tool_use"}},
        {"metadata": {"usage": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110}}},
        {"messageStart": {"role": "user"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolResult": {"toolUseId": tool_use_id, "status": "success"}}}},
        *[{"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolResult": [{"text": chunk}]}}} for chunk in result_chunks],
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "tool_result"}},
    ]


def _final_answer(chunks, stop="end_turn", output_tokens=40):
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
        *[{"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": chunk}}} for chunk in chunks],
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": stop}},
        {"metadata": {"usage": {"inputTokens": 500, "outputTokens": output_tokens, "totalTokens": 500 + output_tokens}}},
    ]


def test_collects_answer_tool_calls_and_tool_results():
    events = _tool_round("t1", "profile___get_account_profile", '{"company_name":"Northwind Logistics"}', ['{"found":', "true}"])
    events += _final_answer(["## 1. Account ", "summary"])

    run = collect(events)

    assert run.answer == "## 1. Account summary"
    assert run.tool_calls == [("profile___get_account_profile", {"company_name": "Northwind Logistics"})]
    assert run.tool_results == ['{"found":true}']  # chunks of one result are joined
    assert run.stop_reasons == ["tool_use", "tool_result", "end_turn"]
    assert run.error is None
    assert run.guardrail_intervened is False


def test_tool_input_split_across_deltas_is_joined_and_parsed():
    events = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {"toolUseId": "t1", "name": "roi___estimate_roi"}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": '{"servers":'}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": "340}"}}}},
        {"messageStop": {"stopReason": "tool_use"}},
    ]
    assert collect(events).tool_calls == [("roi___estimate_roi", {"servers": 340})]


def test_unparseable_tool_input_is_kept_as_text_not_lost():
    events = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {"toolUseId": "t1", "name": "kb___search_knowledge_base"}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": '{"query": "cut off'}}}},
        {"messageStop": {"stopReason": "tool_use"}},
    ]
    assert collect(events).tool_calls == [("kb___search_knowledge_base", '{"query": "cut off')]


def test_text_written_before_a_tool_call_is_not_part_of_the_answer():
    events = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Let me look that up."}}},
        *_tool_round("t1", "profile___get_account_profile", "{}", ["{}"])[1:],
        *_final_answer(["Final."]),
    ]
    assert collect(events).answer == "Final."


def test_token_usage_is_summed_across_model_calls():
    events = _tool_round("t1", "profile___get_account_profile", "{}", ["{}"]) + _final_answer(["x"], output_tokens=40)
    run = collect(events)
    assert run.input_tokens == 600
    assert run.output_tokens == 50


def test_guardrail_intervention_is_reported_and_answer_is_empty():
    events = _tool_round("t1", "profile___get_account_profile", "{}", ["{}"]) + [
        {"messageStart": {"role": "assistant"}},
        {"messageStop": {"stopReason": "guardrail_intervened"}},
        {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}}},
    ]
    run = collect(events)
    assert run.guardrail_intervened is True
    assert run.answer == ""


@pytest.mark.parametrize("reason", ["max_tokens", "max_iterations_exceeded", "timeout_exceeded", "max_output_tokens_exceeded"])
def test_hitting_a_cap_is_reported_as_truncated(reason):
    run = collect(_final_answer(["partial"], stop=reason))
    assert run.truncated is True
    assert run.answer == "partial"  # what arrived is kept


def test_a_normal_finish_is_not_truncated():
    assert collect(_final_answer(["ok"])).truncated is False


def test_an_error_midway_is_captured_and_partial_results_are_kept():
    def stream():
        yield from _tool_round("t1", "profile___get_account_profile", "{}", ["{}"])
        raise RuntimeError("Model stopped generating due to maximum token limit")

    run = collect(stream())
    assert "maximum token limit" in run.error
    assert run.tool_calls == [("profile___get_account_profile", {})]
