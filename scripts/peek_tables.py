from docx import Document

docx_path = r"C:\Users\FURKAN\Desktop\tez_numerik_v8.docx"
doc = Document(docx_path)

print("Searching for Tablo 3...")
for table in doc.tables:
    first_cell_text = table.rows[0].cells[0].text
    if "Tablo 3" in first_cell_text:
        print(f"Found {first_cell_text}")
        for row in table.rows:
            print([cell.text for cell in row.cells])
        break
