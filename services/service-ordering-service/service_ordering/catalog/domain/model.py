"""Contexte Catalogue, gardé comme module séparé dans le même service que les commandes."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CharacteristicValue:
    name: str
    value_type: str
    value: int | str


@dataclass(frozen=True)
class ServiceSpecification:
    id: str
    name: str
    slice_type: str
    lifecycle_status: str
    characteristics: tuple[CharacteristicValue, ...]

    def is_orderable(self) -> bool:
        return self.lifecycle_status == "active"
