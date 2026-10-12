#!/usr/bin/env python3
"""Atualiza EMS, Biolab, Nova Química e Sandoz por planilhas Excel."""
import base64, gzip, json, math, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "catalog-input"
INDEX = ROOT / "index.html"
EXTRA = ROOT / "extra-products.txt"
BRANDS = [
    ("EMS", "EMS", "EMS.xlsx"),
    ("BIOLAB", "BIOLAB GENERICOS", "BIOLAB.xlsx"),
    ("NOVA QUIMICA", "NOVA QUIMICA GENERICO", "NOVA_QUIMICA.xlsx"),
    ("SANDOZ", "SANDOZ", "SANDOZ.xlsx"),
]

def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()

def num(value):
    try:
        if value is None or pd.isna(value):
            return None
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def products_from_excel(path, brand, default_line):
    df = pd.read_excel(path, dtype={"EAN": "string", "COD_PROD_ORIENTE": "string", "COD_PROD_FORNECEDOR": "string"})
    required = {"DESCRICAO", "COD_PROD_ORIENTE", "PV_OL", "ESTOQUE", "EM_TRANSITO"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: faltam colunas obrigatórias: {sorted(missing)}")
    df = df.dropna(subset=["COD_PROD_ORIENTE"])
    df["COD_PROD_ORIENTE"] = df["COD_PROD_ORIENTE"].map(clean)
    df = df[df["COD_PROD_ORIENTE"] != ""]
    result = []
    for code, group in df.groupby("COD_PROD_ORIENTE", sort=False):
        row = group.iloc[0]
        line = clean(row.get("LINHA")) or default_line
        result.append({
            "linha": line,
            "descricao": clean(row.get("DESCRICAO")),
            "ean": clean(row.get("EAN")),
            "codigo": code,
            "codFornecedor": clean(row.get("COD_PROD_FORNECEDOR")),
            "ol": num(row.get("PV_OL")),
            "ol_st": None,
            "lote": clean(row.get("LOTE")),
            "validade": clean(row.get("VALIDADE")),
            "estoque": max([int(num(v) or 0) for v in group["ESTOQUE"]], default=0),
            "transito": sum([int(num(v) or 0) for v in group["EM_TRANSITO"]]),
            "brand": brand,
        })
    return result

def main():
    required_files = [INPUT / name for _, _, name in BRANDS]
    missing = [p.name for p in required_files if not p.exists()]
    if missing:
        raise FileNotFoundError("Envie as quatro planilhas em catalog-input/: " + ", ".join(missing))

    new_by_brand = {}
    for brand, line, filename in BRANDS:
        products = products_from_excel(INPUT / filename, brand, line)
        if not products:
            raise ValueError(f"{filename}: nenhum produto foi lido; publicação cancelada.")
        new_by_brand[brand] = products
        print(f"{brand}: {len(products)} produtos válidos")

    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"const PRODUCTS = (\[.*?\]);", html, flags=re.S)
    if not match:
        raise RuntimeError("Não foi possível localizar o array PRODUCTS em index.html.")
    current = json.loads(match.group(1))
    keep = [p for p in current if str(p.get("brand", "")).upper() not in {"EMS", "BIOLAB"}]
    merged = keep + new_by_brand["EMS"] + new_by_brand["BIOLAB"]
    encoded = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
    html = html[:match.start(1)] + encoded + html[match.end(1):]

    html = re.sub(r'extra-products\.txt\?rev=\d+', 'extra-products.txt?rev=9', html)
    old_loader = 'const normalized=additions.map((p,i)=>({...p,brand:i<185?"NOVA QUIMICA":"SANDOZ"}));'
    new_loader = 'const normalized=additions.map(p=>({...p,brand:/SANDOZ|SZG/i.test(String(p.brand||"")+" "+String(p.linha||"")+" "+String(p.descricao||""))?"SANDOZ":"NOVA QUIMICA"}));'
    if old_loader in html:
        html = html.replace(old_loader, new_loader)
    old_count = 'if(normalized.length!==329)throw new Error("Foram lidos "+normalized.length+" produtos; esperado 329")'
    html = html.replace(old_count, 'if(!normalized.length)throw new Error("Nenhum produto extra foi carregado")')

    raw = EXTRA.read_text(encoding="utf-8").strip()
    old_products = json.loads(gzip.decompress(base64.b64decode(raw)).decode("utf-8"))
    if isinstance(old_products, dict):
        old_products = old_products.get("products", old_products.get("items", []))
    nova = new_by_brand["NOVA QUIMICA"]
    sandoz = new_by_brand["SANDOZ"]
    extras = nova + sandoz
    payload = json.dumps(extras, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # Write all output only after every input was validated.
    INDEX.write_text(html, encoding="utf-8")
    EXTRA.write_text(base64.b64encode(gzip.compress(payload, mtime=0)).decode("ascii") + "\n", encoding="utf-8")
    print(f"Nova Química: {len(nova)} | Sandoz: {len(sandoz)} | Extras: {len(extras)}")
    print(f"Array principal: {len(merged)}; Merck Marcas e Medley preservadas.")

if __name__ == "__main__":
    main()
