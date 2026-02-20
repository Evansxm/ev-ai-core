from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import re
import json
import os


class InjectionType(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    CONTEXT = "context"
    TOOL = "tool"


@dataclass
class PromptTemplate:
    name: str
    template: str
    variables: List[str]
    injection_type: InjectionType
    description: str = ""


class PromptInjector:
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.injection_chain: List[PromptTemplate] = []
        self.context: Dict[str, Any] = {}

    def register_template(self, template: PromptTemplate):
        self.templates[template.name] = template

    def add_to_chain(self, template_name: str):
        if template_name in self.templates:
            self.injection_chain.append(self.templates[template_name])

    def remove_from_chain(self, template_name: str):
        if template_name in self.injection_chain:
            self.injection_chain.remove(self.templates[template_name])

    def set_context(self, key: str, value: Any):
        self.context[key] = value

    def inject(self, prompt: str, additional_templates: List[str] = None) -> str:
        templates = self.injection_chain.copy()

        if additional_templates:
            for name in additional_templates:
                if name in self.templates:
                    templates.append(self.templates[name])

        result = []

        for tmpl in templates:
            if tmpl.injection_type == InjectionType.SYSTEM:
                result.append(f"System: {tmpl.template}")
            elif tmpl.injection_type == InjectionType.CONTEXT:
                result.append(f"Context: {tmpl.template}")
            elif tmpl.injection_type == InjectionType.TOOL:
                result.append(f"Tool Instructions: {tmpl.template}")

        result.append(prompt)

        return "\n\n".join(result)

    def create_template(
        self,
        name: str,
        template: str,
        injection_type: InjectionType = InjectionType.CONTEXT,
        description: str = "",
    ) -> PromptTemplate:
        variables = re.findall(r"\{(\w+)\}", template)
        tmpl = PromptTemplate(
            name=name,
            template=template,
            variables=variables,
            injection_type=injection_type,
            description=description,
        )
        self.register_template(tmpl)
        return tmpl


class PromptManager:
    def __init__(self):
        self.injector = PromptInjector()
        self._setup_default_templates()

    def _setup_default_templates(self):
        self.injector.create_template(
            "memory_access",
            "You have access to a persistent memory system. Use {{memory_recall}} to retrieve stored information and {{remember}} to store important facts.",
            InjectionType.SYSTEM,
            "Enable memory access",
        )

        self.injector.create_template(
            "tool_use",
            "Available tools: {{tools}}. Use appropriate tools to complete tasks. Call tools with: TOOL_NAME arg1=value1 arg2=value2",
            InjectionType.SYSTEM,
            "Tool usage instructions",
        )

        self.injector.create_template(
            "proactive",
            "Be proactive. Anticipate user needs, suggest improvements, and take action when appropriate without waiting for explicit instructions.",
            InjectionType.CONTEXT,
            "Proactive behavior",
        )

        self.injector.create_template(
            "learning",
            "Learn from interactions. Store important patterns and preferences using the memory system for future reference.",
            InjectionType.CONTEXT,
            "Learning instructions",
        )

        self.injector.create_template(
            "safety",
            "Refuse harmful requests. Do not execute commands that could damage systems, leak sensitive information, or harm users.",
            InjectionType.SYSTEM,
            "Safety guidelines",
        )

    def build_prompt(self, user_prompt: str, template_names: List[str] = None) -> str:
        return self.injector.inject(user_prompt, template_names)

    def enable_all(self):
        for name in self.injector.templates:
            self.injector.add_to_chain(name)

    def disable_all(self):
        self.injector.injection_chain.clear()


prompt_manager = PromptManager()


def inject_system(template_name: str, **kwargs) -> str:
    if template_name in prompt_manager.injector.templates:
        tmpl = prompt_manager.injector.templates[template_name]
        return tmpl.template.format(**kwargs)
    return ""


def build_prompt(user_input: str, templates: List[str] = None) -> str:
    return prompt_manager.build_prompt(user_input, templates)


def add_context(key: str, value: Any):
    prompt_manager.injector.set_context(key, value)


def get_context(key: str) -> Any:
    return prompt_manager.injector.context.get(key)
