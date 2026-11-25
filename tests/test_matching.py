import pytest

from ps5watch.matching import classify, match_model
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


@pytest.mark.parametrize(
    "title",
    [
        "Leitor de Disco para Console PS5 Slim Digital",
        "Skin Adesivo Console PS5 Slim Digital",
        "Base de Carregamento DualSense PS5 Slim Console Digital",
        "Console PS5 Slim Digital Recondicionado",
        "Console PS5 Slim Digital Vitrine",
        "Console PS5 Slim Digital Versao Japonesa",
    ],
)
def test_match_model_excludes_accessories_refurbished_and_imports(title):
    assert match_model(title, assume_slim=True) is None


def test_match_model_accepts_included_controller_after_plus():
    title = "Console Playstation 5 Slim Disk + Controle DualSense lacrado"
    assert classify(title) == (ModelKey.SLIM_DISC, False)


@pytest.mark.parametrize(
    "title, assume_slim, expected",
    [
        ("Console Playstation 5 Slim Disk + 2 Jogos", False, (ModelKey.SLIM_DISC, True)),
        ("PS5 Slim Disco + 2 Jogos", False, (ModelKey.SLIM_DISC, True)),
        ("PlayStation®5 Slim Digital 825GB – Pacote ASTRO BOT e Gran Turismo 7", False, (ModelKey.SLIM_DIGITAL, True)),
        ("PlayStation®5 Slim Disk - Pacote ASTRO BOT e Gran Turismo 7", False, (ModelKey.SLIM_DISC, True)),
        (
            "Console Sony PlayStation 5, Com Leitor de Discos, SSD 1TB, Controle Sem Fio DualSense + 2 Jogos",
            True,
            (ModelKey.SLIM_DISC, True),
        ),
        (
            "Console Sony PlayStation 5, SSD 825GB, Controle Sem Fio DualSense + 2 Jogos Digitais, Edição Digital",
            True,
            (ModelKey.SLIM_DIGITAL, True),
        ),
    ],
)
def test_classify_marks_console_with_games_as_combo(title, assume_slim, expected):
    assert classify(title, assume_slim=assume_slim) == expected


@pytest.mark.parametrize(
    "title",
    [
        "Jogo Astro Bot PS5 Slim",
        "Jogos PS5 Slim Gran Turismo 7 + Astro Bot",
    ],
)
def test_classify_rejects_games_sold_alone(title):
    assert classify(title, assume_slim=True) is None


def test_classify_plain_console_is_not_combo():
    assert classify("Console PlayStation 5 Slim Disk 1TB Físico") == (ModelKey.SLIM_DISC, False)


def test_match_model_assume_slim_for_slim_pages():
    title = "Console Sony PlayStation 5, Com Leitor de Discos, SSD 1TB, Controle Sem Fio DualSense"
    assert match_model(title) is None
    assert match_model(title, assume_slim=True) == ModelKey.SLIM_DISC


@pytest.mark.parametrize(
    "title",
    [
        "Sony PlayStation 5 Slim Disc Edition DualSense Wireless Controller Double Pack PS5 - KSA Version",
        "PlayStation 5 Disc Console (New 2023 Slim Model)- UAE Version, 1 Year Manufacturer Warranty",
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
        "Console PS5 Slim Usado",
        "Capa para PS5 Slim",
    ],
)
def test_match_model_excludes(title):
    assert match_model(title) is None
