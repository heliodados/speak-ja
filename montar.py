"""Monta o index.html do Speak Já: grava os áudios que faltam e embute conteúdo e áudio no app.

Uso:  python montar.py            (grava áudios novos e monta)
      python montar.py --so-montar (não grava nada, só monta com o que já existe)
Requer: pip install edge-tts
"""
import asyncio, base64, json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / "audio"
CACHE.mkdir(exist_ok=True)
VOZ_PADRAO = "en-US-AvaNeural"      # frases, falas "A" e exemplos das dicas
VOZ_B = "en-US-AndrewNeural"        # falas "B" dos diálogos

conteudo = (HERE / "conteudo.js").read_text(encoding="utf-8")

# Lê o conteúdo avaliando o JS como JSON: o arquivo só tem literais.
def js_para_json(src: str, nome: str) -> object:
    i = src.index(f"const {nome} = ") + len(f"const {nome} = ")
    j = src.index("\n];", i) + 2
    bruto = src[i:j]
    bruto = re.sub(r"//[^\n]*", "", bruto)                       # comentários
    bruto = re.sub(r"(\{|,)\s*([A-Za-z_]\w*)\s*:", r'\1 "\2":', bruto)  # chaves sem aspas
    bruto = re.sub(r",\s*([\]\}])", r"\1", bruto)                 # vírgulas finais
    return json.loads(bruto)

trilhas = js_para_json(conteudo, "TRILHAS")
dicas = js_para_json(conteudo, "DICAS")

falas = {}   # texto -> voz
for t in trilhas:
    for l in t["licoes"]:
        for en, _pt in l["frases"]:
            falas.setdefault(en, VOZ_PADRAO)
        for quem, en, _pt in l["dialogo"]:
            falas.setdefault(en, VOZ_B if quem == "B" else VOZ_PADRAO)
for d in dicas:
    for en, _pt in d["ex"]:
        falas.setdefault(en, VOZ_PADRAO)
for m in js_para_json(conteudo, "MUSICAS"):
    for en, _pt in m["letra"]:
        falas.setdefault(en, VOZ_PADRAO)
    for en, _pt in m["vocab"]:
        falas.setdefault(en, VOZ_PADRAO)
for h in js_para_json(conteudo, "HITS"):
    for en, _pt, _nota in h["exp"]:
        falas.setdefault(en, VOZ_PADRAO)
print(f"{len(falas)} falas no conteúdo")


def nome_seguro(texto: str, voz: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")[:60] or "x"
    return f"{base}__{voz.split('-')[2][:3].lower()}.mp3"


async def gravar(texto: str, voz: str, sem: asyncio.Semaphore) -> None:
    import edge_tts
    out = CACHE / nome_seguro(texto, voz)
    if out.exists() and out.stat().st_size > 0:
        return
    async with sem:
        for tentativa in range(6):
            try:
                await edge_tts.Communicate(texto, voz, rate="-8%").save(str(out))
                print("  ok ", texto)
                return
            except Exception as e:  # noqa: BLE001
                print(f"  tentativa {tentativa + 1} falhou em '{texto}': {e}")
                await asyncio.sleep(4)
        sys.exit(f"Não consegui gravar '{texto}'")


async def gravar_tudo() -> None:
    sem = asyncio.Semaphore(2)
    await asyncio.gather(*(gravar(t, v, sem) for t, v in falas.items()))


if "--so-montar" not in sys.argv:
    asyncio.run(gravar_tudo())

audio = {}
faltando = 0
for texto, voz in falas.items():
    f = CACHE / nome_seguro(texto, voz)
    if f.exists():
        audio[texto] = "data:audio/mpeg;base64," + base64.b64encode(f.read_bytes()).decode()
    else:
        faltando += 1
if faltando:
    print(f"atenção: {faltando} falas sem áudio (o app usa a voz do navegador para elas)")

app = (HERE / "app.html").read_text(encoding="utf-8")
assert "/*CONTEUDO*/" in app and "<!--AUDIO-->" in app
saida = app.replace("/*CONTEUDO*/", conteudo, 1)
saida = saida.replace("<!--AUDIO-->", '<script id="audio-data" type="application/json">' + json.dumps(audio, ensure_ascii=False, separators=(",", ":")) + "</script>", 1)
(HERE / "index.html").write_text(saida, encoding="utf-8")
print(f"index.html montado: {len(saida) / 1024 / 1024:.1f} MB, {len(audio)} áudios embutidos")
