import pytest

from ps5watch.matching import match_model
from ps5watch.models import ModelKey


def test_match_model_disc():
    title = "Console PlayStation 5 Slim com Leitor de Discos 1TB"
    assert match_model(title) == ModelKey.SLIM_DISC


def test_match_model_digital():
    assert match_model("PS5 Slim Digital 1TB Edição Digital") == ModelKey.SLIM_DIGITAL


@pytest.mark.parametrize(
    "title",
    [
        "PlayStation 5 Pro 2TB",
        "Controle DualSense PS5",
        "PS5 Slim Disco + 2 Jogos",
        "Console PS5 Slim Usado",
        "Capa para PS5 Slim",
    ],
)
def test_match_model_excludes(title):
    assert match_model(title) is None
