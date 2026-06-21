from dataclasses import dataclass, field
import hashlib


@dataclass
class Pouzivatel:
    meno: str
    heslo: str
    rola: str = "obsluha"  # "admin" alebo "obsluha"
    id: int = field(default=None)

    ROLES = ("admin", "obsluha")

    def __post_init__(self):
        if not self.meno.strip():
            raise ValueError("Meno používateľa nemôže byť prázdne")
        if self.rola not in self.ROLES:
            raise ValueError(f"Neplatná rola: {self.rola}. Povolené: {self.ROLES}")
        if len(self.heslo) < 4:
            raise ValueError("Heslo musí mať aspoň 4 znaky")

    def hash_heslo(self) -> str:
        return hashlib.sha256(self.heslo.encode()).hexdigest()

    def is_admin(self) -> bool:
        return self.rola == "admin"

    def __str__(self) -> str:
        return f"{self.meno} | {self.rola}"