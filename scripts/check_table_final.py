from docx import Document

doc = Document(r"C:\Users\FURKAN\Desktop\tez_numerik_v8_final.docx")

# Table 3 is Table 1 in the document based on previous find_table.py
table = doc.tables[0] 
print("\n--- Final Table 3 Check ---")
for row in table.rows:
    row_text = [cell.text for cell in row.cells]
    print(" | ".join(row_text))
