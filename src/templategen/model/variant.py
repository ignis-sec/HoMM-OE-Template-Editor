"""Variant — one of the alternative zone graphs a template can pick from."""

from pydantic import BaseModel


class Orientation(BaseModel): ...


class Border(BaseModel): ...


class Variant(BaseModel): ...
