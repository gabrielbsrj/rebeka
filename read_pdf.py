import fitz  # PyMuPDF

def read_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

if __name__ == "__main__":
    file_path = r"C:\Users\Aridelson\Downloads\canal infanntil\Equilibrio_Neurodivergente_ed1.pdf"
    content = read_pdf(file_path)
    
    # Salvar em arquivo de texto ao invés de imprimir no terminal
    with open("pdf_content.txt", "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"PDF lido com sucesso! Total de caracteres: {len(content)}")
    print("Conteúdo salvo em: pdf_content.txt")
