from decimal import Decimal

import pytest

from ps5watch.parsing import parse_brl


@pytest.mark.parametrize(
    "text, expected",
    [
        ("R$ 3.599,90", Decimal("3599.90")),
        ("3599,90", Decimal("3599.90")),
        ("R$ 3.599", Decimal("3599")),
        ("R$ 4.299,00 à vista", Decimal("4299.00")),
    ],
)
def test_parse_brl_formats(text, expected):
    assert parse_brl(text) == expected


@pytest.mark.parametrize("text", ["", "indisponível", "R$"])
def test_parse_brl_rejects_garbage(text):
    assert parse_brl(text) is None
