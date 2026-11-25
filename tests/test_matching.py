import pytest

from ps5watch.matching import match_model
from ps5watch.models import ModelKey


def test_match_model_disc():
    title = "Console PlayStation 5 Slim com Leitor de Discos 1TB"
    assert match_model(title) == ModelKey.SLIM_DISC


def test_match_model_digital():
    assert match_model("PS5 Slim Digital 1TB Edição Digital") == ModelKey.SLIM_DIGITAL


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Console PlayStation 5 Slim Disk 1TB Físico com Controle DualSense Branco", ModelKey.SLIM_DISC),
        ("PlayStation®5 Slim Edição Digital", ModelKey.SLIM_DIGITAL),
        ("Console Sony PlayStation 5 Edição Digital Slim, SSD 825GB, Controle DualSense", ModelKey.SLIM_DIGITAL),
        ("PlayStation 5 Standard (Slim)", ModelKey.SLIM_DISC),
    ],
)
def test_match_model_real_zoom_titles(title, expected):
    assert match_model(title) == expected


def test_match_model_assume_slim_for_slim_pages():
    title = "Console Sony PlayStation 5, Com Leitor de Discos, SSD 1TB, Controle Sem Fio DualSense"
    assert match_model(title) is None
    assert match_model(title, assume_slim=True) == ModelKey.SLIM_DISC


@pytest.mark.parametrize(
    "title",
    [
        "Sony PlayStation 5 Slim Disc Edition DualSense Wireless Controller Double Pack PS5 - KSA Version",
        "PlayStation 5 Disc Console (New 2023 Slim Model)- UAE Version, 1 Year Manufacturer Warranty",
        "PlayStation®5 Slim Digital 825GB – Pacote ASTRO BOT e Gran Turismo 7",
        "PS5 Digital 30th Anniversary Edition Slim",
        "Pack do console PlayStation®5 – Edição Limitada Ouro - Ghost of Yōtei",
    ],
)
def test_match_model_excludes_imports_packs_and_limited(title):
    assert match_model(title, assume_slim=True) is None


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
