import re
import json
import os
from typing import Any, Callable, Dict, List, Optional, Pattern
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import time


class TriggerType(Enum):
    KEYWORD = "keyword"
    PATTERN = "pattern"
    TIME = "time"
    CONTEXT = "context"
    ACTION = "action"


class ActionPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Trigger:
    type: TriggerType
    pattern: str
    regex: Pattern = field(init=False)

    def __post_init__(self):
        if self.type in [TriggerType.KEYWORD, TriggerType.PATTERN]:
            self.regex = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, text: str) -> bool:
        if self.type == TriggerType.KEYWORD:
            return self.pattern.lower() in text.lower()
        elif self.type == TriggerType.PATTERN:
            return bool(self.regex.search(text))
        return False


@dataclass
class Action:
    name: str
    handler: Callable
    description: str
    priority: ActionPriority = ActionPriority.NORMAL
    enabled: bool = True
    cooldown: int = 0
    _last_run: float = field(default=0, init=False)


class ProactiveEngine:
    def __init__(self):
        self.triggers: List[Trigger] = []
        self.actions: Dict[str, Action] = {}
        self.action_triggers: Dict[str, List[Trigger]] = {}
        self.learned_patterns: Dict[str, List[str]] = {}
        self.context: Dict[str, Any] = {}
        self._monitoring = False
        self._monitor_thread = None

    def add_trigger(self, trigger: Trigger, action_name: str):
        self.triggers.append(trigger)
        if action_name not in self.action_triggers:
            self.action_triggers[action_name] = []
        self.action_triggers[action_name].append(trigger)

    def register_action(self, action: Action):
        self.actions[action.name] = action

    def on_keyword(self, keyword: str, action_name: str):
        trigger = Trigger(TriggerType.KEYWORD, keyword)
        self.add_trigger(trigger, action_name)

    def on_pattern(self, pattern: str, action_name: str):
        trigger = Trigger(TriggerType.PATTERN, pattern)
        self.add_trigger(trigger, action_name)

    def on_time_interval(self, interval_seconds: int, action_name: str):
        trigger = Trigger(TriggerType.TIME, str(interval_seconds))
        self.add_trigger(trigger, action_name)

    def trigger(
        self,
        name: str,
        description: str = "",
        priority: ActionPriority = ActionPriority.NORMAL,
    ):
        def decorator(func: Callable):
            action = Action(
                name=name, handler=func, description=description, priority=priority
            )
            self.register_action(action)
            return func

        return decorator

    def analyze_input(self, text: str) -> List[Action]:
        triggered = []

        for action_name, triggers in self.action_triggers.items():
            action = self.actions.get(action_name)
            if not action or not action.enabled:
                continue

            for trigger in triggers:
                if trigger.matches(text):
                    if action.cooldown > 0:
                        now = time.time()
                        if now - action._last_run < action.cooldown:
                            continue
                        action._last_run = now
                    triggered.append(action)
                    break

        triggered.sort(key=lambda a: a.priority.value, reverse=True)
        return triggered

    def execute_actions(self, actions: List[Action], context: Dict = None) -> List[Any]:
        results = []
        for action in actions:
            try:
                ctx = {**self.context, **(context or {})}
                result = action.handler(ctx)
                results.append({"action": action.name, "result": result})
            except Exception as e:
                results.append({"action": action.name, "error": str(e)})
        return results

    def learn_pattern(self, pattern: str, context: str):
        if context not in self.learned_patterns:
            self.learned_patterns[context] = []
        if pattern not in self.learned_patterns[context]:
            self.learned_patterns[context].append(pattern)

    def get_learned_patterns(self, context: str = None) -> Dict:
        if context:
            return {context: self.learned_patterns.get(context, [])}
        return self.learned_patterns

    def set_context(self, key: str, value: Any):
        self.context[key] = value

    def get_context(self, key: str = None) -> Any:
        if key:
            return self.context.get(key)
        return self.context

    def enable_action(self, name: str):
        if name in self.actions:
            self.actions[name].enabled = True

    def disable_action(self, name: str):
        if name in self.actions:
            self.actions[name].enabled = False

    def list_actions(self) -> List[Dict]:
        return [
            {
                "name": a.name,
                "description": a.description,
                "priority": a.priority.name,
                "enabled": a.enabled,
            }
            for a in self.actions.values()
        ]

    def start_monitoring(self, callback: Callable):
        self._monitoring = True

        def monitor():
            while self._monitoring:
                actions = self.analyze_input("")
                if actions:
                    callback(actions)
                time.sleep(1)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._monitoring = False


proactive_engine = ProactiveEngine()


@proactive_engine.trigger("auto_save", "Auto-save important data", ActionPriority.HIGH)
def auto_save(context: Dict) -> str:
    return "Auto-save triggered"


@proactive_engine.trigger(
    "suggest_improvements", "Suggest improvements proactively", ActionPriority.NORMAL
)
def suggest_improvements(context: Dict) -> str:
    return "Suggestions ready"


def trigger_action(action_name: str, **context) -> Any:
    if action_name in proactive_engine.actions:
        action = proactive_engine.actions[action_name]
        return action.handler(context)
    return None


def analyze_and_act(text: str, context: Dict = None) -> List[Dict]:
    actions = proactive_engine.analyze_input(text)
    return proactive_engine.execute_actions(actions, context)


def learn_user_behavior(input_text: str, action_taken: str):
    proactive_engine.learn_pattern(input_text, "user_inputs")
    proactive_engine.learn_pattern(action_taken, "actions_taken")


def set_user_context(**kwargs):
    for k, v in kwargs.items():
        proactive_engine.set_context(k, v)
