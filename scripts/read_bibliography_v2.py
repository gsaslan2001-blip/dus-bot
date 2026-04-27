import sys
from docx import Document

# Set console output to UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

doc = Document(r"C:\Users\FURKAN\Desktop\tez_numerik_v8.docx")
paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
print(f"Total paragraphs: {len(paragraphs)}")
# Print last 100 non-empty paragraphs
for p in paragraphs[-100:]:
    print(p)
