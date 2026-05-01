"""
cikmis_ekle.py  — DUS Çıkmış Soru Pipeline
============================================
Kullanım:
  python scripts/cikmis_ekle.py --pdf "DUS 2026 1. Dönem.pdf" --yil 2026 --donem 1
  python scripts/cikmis_ekle.py --audit dus_jsonlari/2026-1-dus.json
  python scripts/cikmis_ekle.py --patch-md "DUS 2026 1.md" --json dus_jsonlari/2026-1-dus.json
"""

import fitz, re, json, os, argparse, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Sabit Yollar ──────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "scripts"))
PDF_DIR  = r"C:\Users\FURKAN\Desktop\DUS\Çıkmış\dus çıkmış\dus eski"
JSON_DIR = os.path.join(PROJECT_DIR, "dus_jsonlari")

# ── Ders / Bölüm Tablosu ─────────────────────────────────────
DERS_MAP = [
    (1,  6,   "Temel Bilimler", "Anatomi"),
    (7,  10,  "Temel Bilimler", "Histoloji ve Embriyoloji"),
    (11, 16,  "Temel Bilimler", "Fizyoloji"),
    (17, 22,  "Temel Bilimler", "Tıbbi Biyokimya"),
    (23, 28,  "Temel Bilimler", "Tıbbi Mikrobiyoloji"),
    (29, 32,  "Temel Bilimler", "Tıbbi Patoloji"),
    (33, 36,  "Temel Bilimler", "Tıbbi Farmakoloji"),
    (37, 40,  "Temel Bilimler", "Tıbbi Biyoloji ve Genetik"),
    (41, 50,  "Klinik Bilimler", "Restoratif Diş Tedavisi"),
    (51, 60,  "Klinik Bilimler", "Protetik Diş Tedavisi"),
    (61, 70,  "Klinik Bilimler", "Ağız, Diş ve Çene Cerrahisi"),
    (71, 80,  "Klinik Bilimler", "Ağız, Diş ve Çene Radyolojisi"),
    (81, 90,  "Klinik Bilimler", "Periodontoloji"),
    (91, 100, "Klinik Bilimler", "Ortodonti"),
    (101,110, "Klinik Bilimler", "Endodonti"),
    (111,120, "Klinik Bilimler", "Pedodonti"),
]

DONEM_LABELS = {1: "Bahar", 2: "Sonbahar", 3: "Kış"}

def get_meta(q):
    for lo, hi, bolum, ders in DERS_MAP:
        if lo <= q <= hi:
            return bolum, ders
    return "Bilinmeyen", "Bilinmeyen"

def make_id(yil, donem_no, no):
    return f"dus_{yil}-{donem_no}_q{no:03d}"

def make_yil_str(yil, donem_no):
    return f"{yil}-{donem_no}"

def make_donem_str(yil, donem_no):
    label = DONEM_LABELS.get(donem_no, f"{donem_no}. Dönem")
    return f"{label} {yil}"

# ── Regex ─────────────────────────────────────────────────────
NOISE_RE    = re.compile(r'^\s*(\s*DUS|TEMEL\s+B[İI]|KL[İI]N[İI]K\s+B[İI]|SINAV\s+KODU|----------------|CamScanner)\b', re.I)
TRAILING_RE = re.compile(r'\s*(?:ÖSYM|DUS|TBT|KBT|Bu kitap|Adı|Soyadı|T\.C\.|CamScanner).*$', re.I)
CEVAP_RE    = re.compile(r'CEVAP\s+ANAHTARI', re.I)
Q_NUM_RE    = re.compile(r'^(?:Soru\s+No:\s*)?(\d{1,3})[\.\s:]*(.*)', re.DOTALL | re.I)
OPT_RE      = re.compile(r'\b([A-E])\)\s*(.+?)(?=\s+[A-E]\)|$)', re.DOTALL)

def is_answer_key_page(page):
    # DUS 2026 formatında her sayfa bir soru, atlama yapmıyoruz.
    return False

def parse_opts(text):
    """Metinden A) B) C) D) E) şıklarını ayır. OCR hatalarına (A}, A.) toleranslı."""
    # A), A}, A. formatlarını yakala
    opts = {}
    pattern = re.compile(r'\b([A-E])[\)\}\.]\s*(.+?)(?=\s+[A-E][\)\}\.]|$)', re.DOTALL)
    for m in pattern.finditer(text):
        opts[m.group(1)] = re.sub(r'\s+', ' ', m.group(2)).strip()
    return opts

def parse_column(blocks):
    """Tek sütun bloklarını soru listesine dönüştür."""
    questions = {}
    cur_q, cur_text = None, []

    def flush():
        nonlocal cur_q, cur_text
        if cur_q is None: return
        full = re.sub(r'\s+', ' ', " ".join(cur_text)).strip()
        full = TRAILING_RE.sub('', full)
        fp   = re.search(r'\b[A-E]\)', full)
        if fp:
            soru_metni = full[:fp.start()].strip()
            secenekler = parse_opts(full[fp.start():])
        else:
            soru_metni = full
            secenekler = {}
        for k in "ABCDE": secenekler.setdefault(k, "")
        questions[cur_q] = {"soru_metni": soru_metni, "secenekler": secenekler}
        cur_q = None; cur_text = []

    for _, txt in blocks:
        if NOISE_RE.match(txt): continue
        for line in (l.strip() for l in txt.split('\n') if l.strip()):
            if NOISE_RE.match(line): continue
            m = Q_NUM_RE.match(line)
            if m:
                raw_no = int(m.group(1))
                if 1 <= raw_no <= 120:
                    flush(); cur_q = raw_no
                    cur_text = [m.group(2).strip()] if m.group(2).strip() else []
                    continue
            if cur_q is not None:
                cur_text.append(line)
    flush()
    return questions

def parse_pdf(pdf_path):
    """PDF'yi parse et. DUS formatına (1-40, 1-80) duyarlı."""
    doc = fitz.open(pdf_path)
    all_q = {}
    current_offset = 0
    last_raw_no = 0

    for pno, page in enumerate(doc):
        if is_answer_key_page(page):
            # print(f"  [ATLA] Sayfa {pno+1} = cevap anahtarı") # Gürültüyü azaltmak için kapattım
            continue
        
        text = page.get_text().strip()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        found_q_no = None
        q_text_start = 0
        
        # DUS beklenen numara (1-40, 1-80)
        expected_raw_no = (pno + 1) if pno < 40 else (pno - 39)
        if pno >= 40: current_offset = 40

        # Soru numarası bul
        for i, line in enumerate(lines):
            if NOISE_RE.match(line): continue
            m = Q_NUM_RE.match(line)
            if m:
                val = int(m.group(1))
                # OCR güvenirlik kontrolü: Soru 1 sadece pno=0 veya pno ~40 civarında güvenilirdir
                is_valid_1 = (val == 1 and (pno < 5 or (35 < pno < 45)))
                
                if abs(val - expected_raw_no) > 5 and not is_valid_1:
                    found_q_no = expected_raw_no
                else:
                    found_q_no = val
                
                # Soru 1 reset tespiti
                if found_q_no == 1 and pno > 35 and pno < 45:
                    current_offset = 40
                
                last_raw_no = found_q_no
                q_text_start = i
                lines[i] = m.group(2).strip()
                break
        
        if found_q_no is None:
            found_q_no = expected_raw_no
            # print(f"  [UYARI] Sayfa {pno+1} tahmin: {found_q_no + current_offset}")

        final_no = found_q_no + current_offset
        full_content = " ".join(lines[q_text_start:]).strip()
        full_content = TRAILING_RE.sub('', full_content)
        
        fp = re.search(r'\b[A-E]\)', full_content)
        if fp:
            soru_metni = full_content[:fp.start()].strip()
            secenekler = parse_opts(full_content[fp.start():])
        else:
            soru_metni = full_content
            secenekler = {k: "" for k in "ABCDE"}
        
        for k in "ABCDE": secenekler.setdefault(k, "")
        all_q[final_no] = {"soru_metni": soru_metni, "secenekler": secenekler}

    doc.close()
    return all_q

# ── MD Patch ──────────────────────────────────────────────────
def extract_opts_inline(text):
    positions = [(m.start(), m.group(1)) for m in re.finditer(r'\b([A-E])\)', text)]
    if len(positions) < 2: return {}
    opts = {}
    for i, (pos, letter) in enumerate(positions):
        s = pos + 2
        e = positions[i+1][0] if i+1 < len(positions) else len(text)
        opts[letter] = re.sub(r'\s+', ' ', text[s:e]).strip()
    return opts

def parse_md_for_opts(md_path):
    """MD'den {soru_no: secenekler} döndür."""
    TEMEL_RE  = re.compile(r'TEMEL[\t ]+B[İI]L[İI]MLER', re.I)
    KLINIK_RE = re.compile(r'KL[İI]N[İI]K[\t ]+B[İI]L[İI]MLER', re.I)
    Q_T_RE    = re.compile(r'^-\s+(\d{1,2})\.\s+(.*)')
    Q_K_RE    = re.compile(r'^#{1,4}\s+(\d{1,3})\.\s*(.*)')
    OPT_D_RE  = re.compile(r'^-\s+([A-E])\)\s*(.*)')
    IMG_RE    = re.compile(r'!\[.*?\]\(.*?\)')

    with open(md_path, encoding="utf-8") as f:
        lines = f.readlines()

    results  = {}
    section  = None
    cur_q    = None
    cur_opts = {}
    in_opts  = False

    def save():
        nonlocal cur_q, cur_opts, in_opts
        if cur_q and cur_opts:
            se = {k: cur_opts.get(k, "") for k in "ABCDE"}
            results[cur_q] = se
        cur_q = None; cur_opts = {}; in_opts = False

    for raw in lines:
        line = raw.rstrip('\n')
        if TEMEL_RE.search(line):  save(); section = "temel"; continue
        if KLINIK_RE.search(line): save(); section = "klinik"; continue
        if section is None: continue
        if IMG_RE.search(line): continue
        stripped = line.strip()
        if not stripped: continue

        mo = OPT_D_RE.match(line)
        if mo and cur_q:
            in_opts = True; cur_opts[mo.group(1)] = mo.group(2).strip(); continue

        mt = Q_T_RE.match(line)
        if mt and section == "temel" and 1 <= int(mt.group(1)) <= 40:
            save(); cur_q = int(mt.group(1)); continue

        mk = Q_K_RE.match(line)
        if mk:
            no = int(mk.group(1)); rest = mk.group(2).strip()
            if 1 <= no <= 120:
                save(); cur_q = no
                if re.search(r'\b[A-E]\)', rest):
                    cur_opts.update(extract_opts_inline(rest)); in_opts = True
                continue

        if re.match(r'\b[A-E]\)', stripped) and cur_q:
            opts = extract_opts_inline(stripped)
            if len(opts) >= 2: cur_opts.update(opts); in_opts = True; continue
            m2 = re.match(r'^([A-E])\)\s*(.*)', stripped)
            if m2: cur_opts[m2.group(1)] = m2.group(2).strip(); in_opts = True

    save()
    return results

# ── JSON Oluştur ──────────────────────────────────────────────
def build_record(no, meta, yil_no, donem_no, pdf_name):
    bolum, ders = get_meta(no)
    yil_str     = make_yil_str(yil_no, donem_no)
    donem_str   = make_donem_str(yil_no, donem_no)
    base = {
        "id": make_id(yil_no, donem_no, no), "soru_no": no,
        "yil": yil_str, "donem": donem_str,
        "bolum": bolum, "ders": ders, "kaynak_pdf": pdf_name,
    }
    if meta is None:
        return {**base, "iptal": True, "soru_metni": "",
                "secenekler": {k: "" for k in "ABCDE"},
                "raw_text": "İptal edilmiş soru"}
    sm = meta["soru_metni"]
    se = meta["secenekler"]
    return {**base, "iptal": False, "soru_metni": sm, "secenekler": se,
            "raw_text": (sm + " " + " ".join(f"{k}) {v}" for k,v in se.items() if v)).strip()}

# ── Komut Satırı ──────────────────────────────────────────────
def cmd_parse(args):
    pdf_name = args.pdf
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    yil_str  = make_yil_str(args.yil, args.donem)
    out_name = args.out or f"{yil_str}-dus.json"
    if not os.path.isabs(out_name):
        if out_name.startswith("dus_jsonlari"):
             out_path = os.path.join(PROJECT_DIR, out_name)
        else:
             out_path = os.path.join(JSON_DIR, out_name)
    else:
        out_path = out_name

    if not os.path.exists(pdf_path):
        print(f"[HATA] PDF bulunamadı: {pdf_path}"); return

    print(f"Parse ediliyor: {pdf_name}")
    questions = parse_pdf(pdf_path)
    parsed    = set(questions.keys())
    missing   = sorted(set(range(1,121)) - parsed)
    ok        = sum(1 for m in questions.values()
                    if sum(1 for v in m["secenekler"].values() if v) >= 4)
    print(f"  Soru: {len(questions)}/120  |  Tam şıklı: {ok}/120")
    if missing: print(f"  Eksik numara: {missing}")

    records = [build_record(no, questions.get(no), args.yil, args.donem, pdf_name)
               for no in range(1,121)]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  → {out_path}")

def cmd_audit(args):
    path = args.audit
    if not os.path.isabs(path): path = os.path.join(JSON_DIR, path)
    data = json.load(open(path, encoding="utf-8"))
    ok   = sum(1 for r in data if not r.get("iptal")
               and sum(1 for v in r["secenekler"].values() if v) >= 4)
    bad  = [(r["soru_no"], r["soru_metni"][:50]) for r in data
            if not r.get("iptal")
            and sum(1 for v in r["secenekler"].values() if v) < 4]
    print(f"Audit: {path}")
    print(f"  Tam: {ok}/120")
    if bad:
        print(f"  Eksik şıklı ({len(bad)}):")
        for no, txt in bad: print(f"    Q{no:3d}: {txt}")

def cmd_patch(args):
    md_path   = os.path.join(PDF_DIR.replace("dus eski","").rstrip("\\"), args.patch_md) \
                if not os.path.isabs(args.patch_md) else args.patch_md
    # MD'yi aynı klasörde ara
    md_dir    = r"C:\Users\FURKAN\Desktop\DUS\Çıkmış\dus çıkmış\dus eski"
    md_path   = os.path.join(md_dir, args.patch_md)
    json_path = args.json
    if not os.path.isabs(json_path): json_path = os.path.join(JSON_DIR, json_path)

    records  = json.load(open(json_path, encoding="utf-8"))
    md_opts  = parse_md_for_opts(md_path)
    patched  = 0
    for r in records:
        no = r["soru_no"]
        if r.get("iptal"): continue
        cur_ok = sum(1 for v in r["secenekler"].values() if v)
        if cur_ok >= 4: continue
        se = md_opts.get(no)
        if se and sum(1 for v in se.values() if v) >= 4:
            r["secenekler"] = se
            sm = r["soru_metni"]
            r["raw_text"] = (sm + " " + " ".join(f"{k}) {v}" for k,v in se.items() if v)).strip()
            patched += 1
            print(f"  PATCH Q{no}")
    print(f"Toplam patch: {patched}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  → {json_path} güncellendi.")

MYPPDFS_HOST = os.environ.get("MYPPDFS_HOST", "myppdfs-0crkhvy.svc.aped-4627-b74a.pinecone.io")
UPLOAD_BATCH = 96  # Pinecone upsert batch boyutu

def cmd_upload(args):
    """JSON dosyasını myppdfs/cikmis namespace'ine yükle."""
    from pinecone import Pinecone
    from embedding_utils import get_local_embedder

    json_path = args.upload
    if not os.path.isabs(json_path):
        json_path = os.path.join(JSON_DIR, json_path)

    if not os.path.exists(json_path):
        print(f"[HATA] JSON bulunamadı: {json_path}")
        return

    api_key = os.environ.get("PINECONE_API_KEY", "")
    if not api_key:
        print("[HATA] PINECONE_API_KEY ortam değişkeni ayarlanmamış.")
        return

    records = json.load(open(json_path, encoding="utf-8"))
    active  = [r for r in records if not r.get("iptal") and r.get("raw_text", "").strip()]
    print(f"Upload: {json_path}")
    print(f"  Aktif kayıt: {len(active)}/{len(records)}")

    embedder = get_local_embedder()
    pc       = Pinecone(api_key=api_key)
    index    = pc.Index(host=MYPPDFS_HOST)

    vectors  = []
    for r in active:
        vec = embedder.embed_text(r["raw_text"], is_query=False)
        vectors.append({
            "id": r["id"],
            "values": vec,
            "metadata": {
                "text":    r["raw_text"],
                "soru_no": r["soru_no"],
                "yil":     r["yil"],
                "donem":   r["donem"],
                "bolum":   r["bolum"],
                "ders":    r["ders"],
            }
        })

    batches = [vectors[i:i + UPLOAD_BATCH] for i in range(0, len(vectors), UPLOAD_BATCH)]
    for i, batch in enumerate(batches, 1):
        index.upsert(vectors=batch, namespace="cikmis")
        print(f"  Batch {i}/{len(batches)} → {len(batch)} vektör")

    print(f"  Toplam yüklendi: {len(vectors)} vektör → myppdfs/cikmis")


def main():
    p = argparse.ArgumentParser(description="DUS Çıkmış Soru Pipeline")
    p.add_argument("--pdf",       help="PDF dosya adı (PDF_DIR içinde)")
    p.add_argument("--yil",       type=int, help="Sınav yılı (ör: 2026)")
    p.add_argument("--donem",     type=int, help="Dönem numarası (1=Bahar, 2=Sonbahar)")
    p.add_argument("--out",       help="Çıktı JSON dosyası (opsiyonel)")
    p.add_argument("--audit",     help="JSON dosyasını denetle")
    p.add_argument("--patch-md",  dest="patch_md", help="MD dosya adı (patch için)")
    p.add_argument("--json",      help="Patch uygulanacak JSON dosyası")
    p.add_argument("--upload",    help="JSON dosyasını myppdfs/cikmis namespace'ine yükle")
    args = p.parse_args()

    if args.audit:
        cmd_audit(args)
    elif args.patch_md:
        cmd_patch(args)
    elif args.upload:
        cmd_upload(args)
    elif args.pdf:
        cmd_parse(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()
