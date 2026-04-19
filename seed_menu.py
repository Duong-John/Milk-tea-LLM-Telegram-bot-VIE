import PyPDF2
import os

def extract_to_db():
    reader = PyPDF2.PdfReader('menu/menu.pdf')
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    with open('parsed_menu.txt', 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    extract_to_db()
