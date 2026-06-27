# backend/app/jobs/registry.py

from dataclasses import dataclass
from typing import Any


@dataclass
class JobDefinition:
    name: str
    display_name: str
    description: str
    group: str
    task: Any
    parameters_schema: type | None = None


_registry: dict[str, JobDefinition] = {}


def register(defn: JobDefinition) -> None:
    _registry[defn.name] = defn


def get(name: str) -> JobDefinition | None:
    return _registry.get(name)


def all_jobs() -> list[JobDefinition]:
    return list(_registry.values())
