Em Configurações > Fiscal:

- Engine de OCR: "Somente texto nativo do PDF" (sem dependências),
  "Tesseract" (padrão; requer tesseract-ocr e tesseract-ocr-por instalados
  no servidor e o pacote python pytesseract).
- Destino da importação: somente Documento Fiscal, ou Documento Fiscal +
  Fatura de fornecedor.
- Operação fiscal padrão para serviços tomados.

Dependências de servidor (doodba): pip.txt: pymupdf, pytesseract;
apt.txt: tesseract-ocr, tesseract-ocr-por.
