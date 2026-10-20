Importa documentos fiscais brasileiros que chegam SEM XML: NFS-e recebidas
(PDF de qualquer município) e faturas não-eletrônicas (serviços, contas de
energia, telecom, aluguel), a partir de PDF ou imagem.

Pipeline em camadas: texto nativo do PDF (sem OCR, maioria das NFS-e) com
OCR opcional para documentos escaneados (Tesseract local por padrão; backends
RapidOCR e HTTP/VLM planejados). Os campos brasileiros (CNPJ, número da nota,
código de verificação, datas, valores, ISS e retenções) são extraídos com
validação de dígito verificador e o resultado abre num assistente de
conferência antes de criar o documento fiscal e/ou a fatura de fornecedor.

O produto é um pré-preenchimento auditável: o usuário sempre confere o
preview antes de confirmar.
