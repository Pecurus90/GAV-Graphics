"""
D18 — L'EDITOR DI PALETTE. La rete di sicurezza.

Il patto non negoziabile (D2/D18): il socio compone i TOKEN DI MARCA; le 2 chiavi
ASTRONOMICHE (star_ramp, planet_colors) si INNESTANO da osservatorio e NON sono mai
editabili — «una palette puo' cambiare un blu, non puo' mentire sull'astronomia».

Questi test dimostrano che:
- una palette creata PASSA validate.py e RENDE su tutti i formati;
- le sue chiavi astronomiche sono IDENTICHE a osservatorio (innestate);
- nemmeno un client MALIZIOSO che manda star_ramp/planet_colors puo' alterarle;
- il cancello (validate) rifiuta hex non validi, nomi vuoti, e la collisione coi
  nomi di serie — SENZA scrivere nulla.
"""
import json
import os

import pytest

import validate


def _brand_osservatorio(root):
    """I soli token DI MARCA di osservatorio (com'e' fatto il payload dell'editor)."""
    d = json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                       encoding="utf-8"))
    b = {k: d[k] for k in validate.STYLE_TOKENS}
    b["bg"] = d["bg"]; b["disk"] = d["disk"]; b["status"] = d["status"]
    return b, d


@pytest.fixture
def user_dir(tmp_path, monkeypatch):
    """Isola la cartella delle palette del socio in un tmp (non l'%APPDATA% vero)."""
    monkeypatch.setenv("CIELO_PALETTE_UTENTE", str(tmp_path))
    return str(tmp_path)


def test_palette_creata_valida_e_rende_su_tutti_i_formati(eng, root, user_dir):
    brand, _ = _brand_osservatorio(root)
    brand["neon"] = "#ff3390"  # un accento diverso: e' una palette nuova, non una copia
    slug, theme, path = validate.salva_palette_utente("Rosa di Prova", "test", brand)
    assert os.path.exists(path)
    # passa il cancello (ri-validazione esplicita dal file scritto)
    salvata = validate.carica_palette(slug)
    validate.valida_tema(salvata, f"{slug}.json")   # non alza => valida
    # RENDE su OGNI formato disponibile (compresa la pagina 2 col Messier)
    import tempfile
    for fmt in validate.formati_disponibili():
        layout = json.load(open(os.path.join(root, "brand", "layouts", f"{fmt}.json"),
                                encoding="utf-8"))
        out = os.path.join(tempfile.gettempdir(), f"pe_{fmt}.svg")
        svg_path = eng.generate(2026, 8, 45.5455, 11.5353, "Vicenza", salvata, out, layout=layout)
        assert os.path.getsize(svg_path) > 1000, f"SVG vuoto per il formato {fmt}"


def test_astronomia_identica_a_osservatorio(root, user_dir):
    brand, osserv = _brand_osservatorio(root)
    _slug, theme, _p = validate.salva_palette_utente("Prova Astro", "", brand)
    assert theme["star_ramp"] == osserv["star_ramp"]
    assert theme["planet_colors"] == osserv["planet_colors"]


def test_client_malizioso_non_altera_astronomia(root, user_dir):
    """Anche se il client MANDA star_ramp/planet_colors, l'innesto li ignora: la
    garanzia di D2 e' STRUTTURALE (whitelist), non una speranza."""
    brand, osserv = _brand_osservatorio(root)
    brand["star_ramp"] = [[0.0, "#000000"], [1.0, "#ffffff"]]   # bugia
    brand["planet_colors"] = {"Marte": "#0000ff"}               # Marte azzurro: mai
    _slug, theme, _p = validate.salva_palette_utente("Iniezione", "", brand)
    assert theme["star_ramp"] == osserv["star_ramp"]
    assert theme["planet_colors"] == osserv["planet_colors"]


def test_componi_ignora_astronomia_del_client(root):
    """componi_palette_utente (usata anche dall'anteprima) non deve MAI far passare
    l'astronomia del client."""
    brand, osserv = _brand_osservatorio(root)
    brand["planet_colors"] = {"Marte": "#0000ff"}
    theme = validate.componi_palette_utente(brand, "X", "")
    assert theme["planet_colors"] == osserv["planet_colors"]
    assert theme["star_ramp"] == osserv["star_ramp"]


def test_salva_rifiuta_hex_invalido_senza_scrivere(root, user_dir):
    brand, _ = _brand_osservatorio(root)
    brand["neon"] = "rosso"   # non hex
    with pytest.raises(validate.InputError) as e:
        validate.salva_palette_utente("Palette Rotta", "", brand)
    assert "neon" in str(e.value)
    assert os.listdir(user_dir) == [], "Non deve scrivere nulla se non valida."


def test_salva_rifiuta_collisione_con_serie(root, user_dir):
    brand, _ = _brand_osservatorio(root)
    with pytest.raises(validate.InputError) as e:
        validate.salva_palette_utente("Osservatorio", "", brand)
    assert "serie" in str(e.value).lower()
    assert os.listdir(user_dir) == []


def test_salva_rifiuta_nome_vuoto(root, user_dir):
    brand, _ = _brand_osservatorio(root)
    with pytest.raises(validate.InputError):
        validate.salva_palette_utente("   ", "", brand)
    with pytest.raises(validate.InputError):
        validate.salva_palette_utente("!!!", "", brand)   # slug vuoto dopo sanitizzazione


def test_palette_utente_entra_nell_unione(root, user_dir):
    brand, _ = _brand_osservatorio(root)
    slug, _theme, _p = validate.salva_palette_utente("Nuova Vera", "", brand)
    disp = validate.palette_disponibili()
    assert slug in disp
    assert "osservatorio" in disp   # le di serie restano
    # e valida_palette (usata da CLI e web) ora la accetta
    assert validate.valida_palette(slug) == slug
    assert validate.carica_palette(slug)["name"] == "Nuova Vera"
