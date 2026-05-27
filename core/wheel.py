"""
Definicao fisica das rodas de roleta europeia e americana.

A ORDEM dos numeros no PANO (mesa) e diferente da ordem na RODA FISICA.
Para detectar vies por SETOR (vizinhos no rotor), precisamos da ordem fisica —
caso contrario um vies localizado em uma regiao da roda fica invisivel.

Fonte: layout padrao de cassinos. Referencias cruzadas em
https://www.roulettephysics.com/roulette-wheel-bias/
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

# Layout fisico da roda EUROPEIA (zero unico), no sentido horario a partir do 0
EUROPEAN_WHEEL_ORDER: List[str] = [
    "0", "32", "15", "19", "4", "21", "2", "25", "17", "34", "6", "27", "13",
    "36", "11", "30", "8", "23", "10", "5", "24", "16", "33", "1", "20", "14",
    "31", "9", "22", "18", "29", "7", "28", "12", "35", "3", "26",
]

# Layout fisico da roda AMERICANA (zero duplo "00")
AMERICAN_WHEEL_ORDER: List[str] = [
    "0", "28", "9", "26", "30", "11", "7", "20", "32", "17", "5", "22", "34",
    "15", "3", "24", "36", "13", "1", "00", "27", "10", "25", "29", "12", "8",
    "19", "31", "18", "6", "21", "33", "16", "4", "23", "35", "14", "2",
]

# Cores (validas para ambas as rodas — o 0/00 sao verdes)
REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACKS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}


def color_of(num: str) -> str:
    """Retorna 'red', 'black' ou 'green'."""
    if num in ("0", "00"):
        return "green"
    n = int(num)
    if n in REDS:
        return "red"
    if n in BLACKS:
        return "black"
    raise ValueError(f"Numero invalido: {num}")


@dataclass
class Wheel:
    """Representa uma roda de roleta com seu layout fisico."""
    name: str
    order: List[str]
    pockets: int = field(init=False)
    position: Dict[str, int] = field(init=False)
    expected_prob: float = field(init=False)

    def __post_init__(self) -> None:
        self.pockets = len(self.order)
        self.position = {num: i for i, num in enumerate(self.order)}
        self.expected_prob = 1.0 / self.pockets

    def sector(self, num: str, size: int = 5) -> List[str]:
        """Retorna o setor fisico de `size` numeros centrado em `num`."""
        idx = self.position[num]
        half = size // 2
        return [
            self.order[(idx - half + k) % self.pockets]
            for k in range(size)
        ]

    def all_sectors(self, size: int = 5) -> List[List[str]]:
        """Retorna todos os setores (janela deslizante de tamanho `size`)."""
        return [self.sector(self.order[i], size) for i in range(self.pockets)]

    def is_red(self, num: str) -> bool:
        return color_of(num) == "red"

    def is_black(self, num: str) -> bool:
        return color_of(num) == "black"

    def is_green(self, num: str) -> bool:
        return color_of(num) == "green"

    def dozen(self, num: str) -> Optional[int]:
        """Retorna 1, 2, 3 (duzia) ou None para 0/00."""
        if num in ("0", "00"):
            return None
        n = int(num)
        return (n - 1) // 12 + 1

    def column(self, num: str) -> Optional[int]:
        """Retorna 1, 2, 3 (coluna) ou None para 0/00."""
        if num in ("0", "00"):
            return None
        n = int(num)
        return ((n - 1) % 3) + 1

    def high_low(self, num: str) -> Optional[str]:
        """'low' (1-18), 'high' (19-36), None para 0/00."""
        if num in ("0", "00"):
            return None
        n = int(num)
        return "low" if n <= 18 else "high"

    def validate_spins(self, spins: Sequence[str]) -> List[str]:
        """Garante que cada giro existe na roda. Levanta ValueError caso contrario."""
        valid = set(self.order)
        bad = [s for s in spins if s not in valid]
        if bad:
            raise ValueError(
                f"Giros invalidos para roda {self.name}: {bad[:5]}..."
            )
        return list(spins)


EUROPEAN = Wheel("european", EUROPEAN_WHEEL_ORDER)
AMERICAN = Wheel("american", AMERICAN_WHEEL_ORDER)


def get_wheel(name: str) -> Wheel:
    name = name.strip().lower()
    if name in ("european", "eu", "single-zero", "single_zero"):
        return EUROPEAN
    if name in ("american", "us", "double-zero", "double_zero"):
        return AMERICAN
    raise ValueError(f"Roda desconhecida: {name}")
