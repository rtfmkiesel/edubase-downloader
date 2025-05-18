# Edubase Downloader
Backup/Download your (bought!) Edubase books to PDFs, because nobody likes proprietary ebook readers. 

## Setup
```bash
git clone https://github.com/rtfmkiesel/edubase-downloader
# a venv is recommended
pip install -r requirements.txt
```

## Usage
```
usage: edubasedl.py [OPTIONS]

Required:
-u, --username           Username (Email) of Edubase account

Options:
-p, --password           Password (can be left empty, script will ask)
-c, --chrome-path        Path to the chrome/chromium binary
-a, --all                Will download all found books
-s, --show               Show the action/open browser in front
-h, --help               Prints this text
-d, --disable-css-patch  Disable print.css modification to prevent shifted backgrounds
```

## OCR
The PDFs that this code produces are just images and thus not searchable. There are many OCR solutions, but for me, [github.com/ocrmypdf/OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) worked perfectly fine. 

## Legal
This code does not "crack" any copy protection. It simply makes automated screenshots of every single site of a **bought** document/book. Since Edubase cannot guarantee the existence/support for their reader app if they go out of business, this repo was created to save, backup and preserve **bought** Edubase documents as the widely adapted and well documented PDF format.
