from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Tovar:
    nazov: str
    cena: float
    mnozstvo: int
    kategoria: str
    id: int = field(default=None)

    def __post_init__(self):
        if self.cena < 0:
            raise ValueError(f"Cena nemôže byť záporná: {self.cena}")
        if self.mnozstvo < 0:
            raise ValueError(f"Množstvo nemôže byť záporné: {self.mnozstvo}")
        if not self.nazov.strip():
            raise ValueError("Názov tovaru nemôže byť prázdny")

    def is_available(self) -> bool:
        return self.mnozstvo > 0

    def __str__(self) -> str:
        return f"{self.nazov} | {self.cena:.2f}€ | sklad: {self.mnozstvo} | {self.kategoria}"