import fitz   # PyMuPDF

def parse_pdf(file_path: str) -> list[dict]:
    """
    Parse a PDF and return a list of page dicts.
    Each dict: { 'page': int, 'text': str, 'source': str }
    """
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():   # skip blank pages
            pages.append({
                "page": page_num,
                "text": text,
                "source": file_path,
            })
    return pages
