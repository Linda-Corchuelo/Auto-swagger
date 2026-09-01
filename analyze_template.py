from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document(r"C:\Users\home\swagger-doc-generator\template\IXV10 - acuerdo de interfaz.docx")

body = doc.element.body

# Collect all body-level children (paragraphs, tables, sectPr, etc.)
elements = list(body)

print(f"Total body elements: {len(elements)}")
print("=" * 100)

# Track indices for paragraphs/tables specifically
para_idx = 0

for i, el in enumerate(elements):
    tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag

    if tag == "p":
        # It's a paragraph
        p_text = el.text or ""
        # Gather all text within runs
        from lxml import etree
        p_text = "".join(el.itertext()).strip()

        # Try to get style
        pPr = el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr")
        style_name = ""
        if pPr is not None:
            pStyle = pPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
            if pStyle is not None:
                style_name = pStyle.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")

        display_text = p_text[:120].replace("\n", "\\n")
        print(f"[{i:3d}] para #{para_idx:3d} | style='{style_name}' | text='{display_text}'")
        para_idx += 1

    elif tag == "tbl":
        # Table
        from lxml import etree
        tbl_text = "".join(el.itertext()).strip()
        display_text = tbl_text[:120].replace("\n", "\\n")
        print(f"[{i:3d}] TABLE     | rows={len(el.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'))} | text='{display_text}'")
        para_idx += 1

    elif tag == "sectPr":
        print(f"[{i:3d}] sectPr    | (section properties)")

    else:
        print(f"[{i:3d}] {tag:10s}| (other)")

print()
print("=" * 100)
print("SEARCHING FOR KEY TERMS...")
print("=" * 100)

keywords = ["Rummi", "User Administration", "Blockchain", "Trading", "Operaciones del servicio"]
for i, el in enumerate(elements):
    full_text = "".join(el.itertext()).strip()
    for kw in keywords:
        if kw.lower() in full_text.lower():
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            print(f"  [{i:3d}] ({tag}) Found '{kw}': '{full_text[:150]}'")

print()
print("=" * 100)
print("PARAGRAPHS [40] through [55] (detailed)...")
print("=" * 100)

for i in range(40, min(56, len(elements))):
    el = elements[i]
    tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
    from lxml import etree
    full_text = "".join(el.itertext()).strip()

    pPr = el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr")
    style_name = ""
    if pPr is not None:
        pStyle = pPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
        if pStyle is not None:
            style_name = pStyle.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")

    # Check if bold
    is_bold = False
    for rPr in el.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr"):
        b = rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}b")
        if b is not None:
            is_bold = True
            break

    print(f"[{i:3d}] ({tag:5s}) style='{style_name}' bold={is_bold} | text='{full_text[:200]}'")
