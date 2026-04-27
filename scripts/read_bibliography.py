from docx import Document

doc = Document(r"C:\Users\FURKAN\Desktop\tez_numerik_v8.docx")
print("--- End of Document (last 100 paragraphs) ---")
paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
for p in paragraphs[-100:]:
    print(p)
