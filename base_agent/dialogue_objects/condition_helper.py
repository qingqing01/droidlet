"""
Copyright (c) Facebook, Inc. and its affiliates.
"""
from typing import Optional, Union
from word2number.w2n import word_to_num
from base_util import ErrorWithResponse
from condition import Condition, NeverCondition, AndCondition, OrCondition, TimeCondition
from memory_values import MemoryColumnValue, FixedValue
from comparator_helper import interpret_comparator


class ConditionInterpreter:
    def __init__(self):
        # extra layer of indirection to allow easier split into base_agent and specialized agent conditions...
        self.condition_types = {
            "NEVER": self.interpret_never,
            "AND": self.interpret_and,
            "OR": self.interpret_or,
            "TIME": self.interpret_time,
            "COMPARATOR": interpret_comparator,
        }
        # to avoid having to redefine interpret_comparator in agents if necessary ...
        # TODO distance between
        self.value_extractors = {
            "filters": MemoryColumnValue,
            "span": FixedValue,
            "distance_between": None,
        }

    def __call__(self, interpreter, speaker, d) -> Optional[Condition]:
        """subinterpreter for Conditions
        args:
        interpreter:  root interpreter.
        speaker (str): The name of the player/human/agent who uttered 
            the chat resulting in this interpreter
        d: logical form from semantic parser
        """
        ct = d.get("condition_type")
        if ct:
            if self.condition_types.get(ct):
                # condition_type NEVER doesn't have a "condition" sibling
                if ct == "NEVER":
                    return self.condition_types[ct](interpreter, speaker, d)
                if not d.get("condition"):
                    raise ErrorWithResponse(
                        "I thought there was a condition but I don't understand it"
                    )
                return self.condition_types[ct](interpreter, speaker, d["condition"])
            else:
                raise ErrorWithResponse("I don't understand that condition")
        else:
            return None

    def interpret_never(self, interpreter, speaker, d) -> Optional[Condition]:
        return NeverCondition(interpreter.agent)

    def interpret_or(self, interpreter, speaker, d) -> Optional[Condition]:
        orlist = d["or_condition"]
        conds = []
        for c in orlist:
            new_condition = self(interpreter, speaker, d)
            if new_condition:
                conds.append(new_condition)
        return OrCondition(interpreter.agent, conds)

    def interpret_and(self, interpreter, speaker, d) -> Optional[Condition]:
        orlist = d["and_condition"]
        conds = []
        for c in orlist:
            new_condition = self(interpreter, speaker, d)
            if new_condition:
                conds.append(new_condition)
        return AndCondition(interpreter.agent, conds)

    def interpret_time(self, interpreter, speaker, d):
        event = None

        if d.get("special_time_event"):
            return TimeCondition(interpreter.agent, d["special_time_event"])
        else:
            if not d.get("comparator"):
                raise ErrorWithResponse("I don't know how to interpret this time condition")
            dc = d["comparator"]
            dc["input_left"] = {"value_extractor": "NULL"}
            comparator = interpret_comparator(interpreter, speaker, dc)

        if d.get("event"):
            event = self(interpreter, speaker, d["event"])

        return TimeCondition(interpreter.agent, comparator, event=event)


def get_repeat_num(d) -> Union[int, str]:
    if "repeat" in d:
        repeat_dict = d["repeat"]
        if repeat_dict["repeat_key"] == "FOR":
            try:
                return word_to_num(repeat_dict["repeat_count"])
            except:
                return 2  # TODO: dialogue instead of default?
        if repeat_dict["repeat_key"] == "ALL":
            return "ALL"
    return 1
