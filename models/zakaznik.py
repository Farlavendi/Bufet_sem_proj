from dataclasses import dataclass, field


@dataclass
class Zakaznik:
    meno: str
    email: str
    telefon: str
    id: int = field(default=None)

    def __post_init__(self):
        if not self.meno.strip():
            raise ValueError("Meno zákazníka nemôže byť prázdne")
        if "@" not in self.email:
            raise ValueError(f"Neplatný email: {self.email}")

    def __str__(self) -> str:
        return f"{self.meno} | {self.email} | {self.telefon}"