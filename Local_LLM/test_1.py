from pathlib import Path
from pypdf import PdfReader


print(len(PdfReader("Papers/12.pdf").pages))

