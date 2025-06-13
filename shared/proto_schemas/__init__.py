"""Loom Shared Schema Models.

This package contains Pydantic models auto-generated from JSON/Avro schemas.
Models are namespaced mirroring the Kafka topic hierarchy.
"""

__all__ = [
    "get_model",
]

from importlib import import_module
from typing import Type

from pydantic import BaseModel


_CACHE: dict[str, Type[BaseModel]] = {}


def get_model(topic: str) -> Type[BaseModel]:
    """Dynamically import and return the Pydantic model class for a Kafka topic.
    The module path is derived by replacing dots with underscores.
    """
    if topic in _CACHE:
        return _CACHE[topic]

    module_path = topic.replace(".", "_")
    try:
        module = import_module(f"shared.proto_schemas.{module_path}")
    except ModuleNotFoundError as e:
        raise RuntimeError(f"No model found for topic '{topic}'") from e

    model_cls = getattr(module, "Model", None)
    if model_cls is None:
        raise RuntimeError(f"Model class missing in module '{module_path}'")

    _CACHE[topic] = model_cls  # type: ignore[assignment]
    return model_cls 