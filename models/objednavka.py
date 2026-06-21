from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Objednavka:
    id_tovaru: int
    id_zakaznika: int
    mnozstvo: int
    datum: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    id: int = field(default=None)

    def __post_init__(self):
        if self.mnozstvo <= 0:
            raise ValueError(f"Množstvo objednávky musí byť kladné: {self.mnozstvo}")

    def __str__(self) -> str:
        return f"Objednávka #{self.id} | tovar: {self.id_tovaru} | zákazník: {self.id_zakaznika} | {self.mnozstvo}ks | {self.datum}"