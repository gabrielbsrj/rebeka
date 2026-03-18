import PyPDF2
import sys
import os

def extract_pdf_text(file_path):
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo não encontrado em {file_path}")
        return
    
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            print(text)
    except Exception as e:
        print(f"Erro ao ler PDF: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        extract_pdf_text(sys.argv[1])
    else:
        print("Uso: python read_pdf.py <caminho_do_arquivo>")
