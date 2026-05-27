"""Smoke tests para core.wheel."""
from __future__ import annotations
import pytest
from core.wheel import EUROPEAN, AMERICAN, color_of, get_wheel


def test_european_has_37_pockets():
    assert EUROPEAN.pockets == 37
    assert len(EUROPEAN.order) == 37
    assert "0" in EUROPEAN.order
    assert "00" not in EUROPEAN.order


def test_american_has_38_pockets():
    assert AMERICAN.pockets == 38
    assert "0" in AMERICAN.order
    assert "00" in AMERICAN.order


def test_european_expected_prob():
    assert abs(EUROPEAN.expected_prob - 1 / 37) < 1e-9


def test_colors():
    assert color_of("1") == "red"
    assert color_of("2") == "black"
    assert color_of("0") == "green"
    assert color_of("00") == "green"
    assert color_of("36") == "red"


def test_sector_around_zero_european():
    # vizinhos fisicos do 0 na roda europeia
    sector = EUROPEAN.sector("0", 5)
    assert sector == ["3", "26", "0", "32", "15"]


def test_sector_wraps_around():
    # ultimo numero da ordem + 2 deve enrolar pro inicio
    last = EUROPEAN.order[-1]
    sector = EUROPEAN.sector(last, 5)
    assert len(sector) == 5
    # garante que primeira posicao da volta no array
    assert EUROPEAN.order[0] in sector or EUROPEAN.order[1] in sector


def test_dozen_column():
    assert EUROPEAN.dozen("7") == 1
    assert EUROPEAN.dozen("17") == 2
    assert EUROPEAN.dozen("27") == 3
    assert EUROPEAN.dozen("0") is None
    assert EUROPEAN.column("1") == 1
    assert EUROPEAN.column("2") == 2
    assert EUROPEAN.column("3") == 3


def test_high_low():
    assert EUROPEAN.high_low("1") == "low"
    assert EUROPEAN.high_low("18") == "low"
    assert EUROPEAN.high_low("19") == "high"
    assert EUROPEAN.high_low("0") is None


def test_validate_spins_rejects_invalid():
    with pytest.raises(ValueError):
        EUROPEAN.validate_spins(["7", "37", "12"])  # 37 nao existe
    with pytest.raises(ValueError):
        EUROPEAN.validate_spins(["00"])  # 00 nao existe na europeia


def test_get_wheel_aliases():
    assert get_wheel("european") is EUROPEAN
    assert get_wheel("eu") is EUROPEAN
    assert get_wheel("american") is AMERICAN
    assert get_wheel("us") is AMERICAN
    with pytest.raises(ValueError):
        get_wheel("brazilian")  # nao existe
