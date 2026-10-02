# Importação do acervo IBIAG — 2 de outubro de 2026

## Estado confirmado em produção

- Portfólio: 136 produtos, 24 fornecedores e 145 ofertas da tabela oficial. Preços textuais e comissões preservados.
- CRM: 1.233 contatos novos e quatro registros atualizados. Interesse de compra e atualidade ainda não validados.
- Quatro ZIPs recebidos, incluindo o ZIP 4 reenviado. Expansão dos ZIPs internos: 991 entradas, 860 conteúdos únicos por SHA256 e 131 repetições exatas. 106 entradas internas. Um RAR não extraído.
- Central de Documentos: 657 PDFs cadastrados e conferidos pela interface autenticada. 236 anteriores, 37 do ZIP 4, 377 dos lotes complementares, cinco confirmados pelo conteúdo e duas apresentações maiores pelo cadastro individual.
- 141 documentos vinculados a fornecedores. 74 fichas específicas vinculadas a 70 ofertas. Não foram aplicados vínculos ambíguos.
- Visualização de PDF verificada na Central e nas ofertas.
- Índice mestre Excel entregue com todas as 991 entradas, origem, SHA256, duplicatas, categoria, situação e vínculos confirmados.
- Originais preservados. Conforme orientação do usuário, conteúdos sem relação com IBIAG desconsiderados.

## Situações dos 860 conteúdos únicos

- 657 PDFs importados.
- 110 conteúdos a revisar, incluindo nove PDFs digitalizados sem identificação confirmada e um RAR.
- 62 fontes de dados preservadas, sem presumir novas importações de registros.
- 16 arquivos compactados de origem.
- 15 conteúdos desconsiderados por não terem relação com IBIAG.

## Importação retomável

`POST /api/documents/import-batch`: administrador, ZIP com manifest.json e PDFs em files/<número>.pdf, limites de 40 MB de upload, 30 MB por entrada, 80 MB descomprimidos e 100 documentos. Validação integral antes da gravação, deduplicação SHA256. Categorias: Produtos, Fornecedores, Clientes & Comercial, Qualidade & Compliance, Financeiro & Fiscal, Societário, Exportação & Logística.

`POST /api/documents/link-batch`: administrador, SHA256, fornecedor e produto opcionais, tipo spec ou other. Plano validado antes de alterações, adição sem substituir anexos anteriores.

As duas apresentações maiores entraram pelo cadastro individual com SHA256 nas observações. Não possuem a chave source_sha256 do importador em lote; consultar o índice antes de reenviá-las.

Não repetir importação geral do portfólio com replace=true: substitui produtos e ofertas. Atualizações de comissões usam o endpoint específico não destrutivo.

## Próximos trabalhos da Gestão

- Conferir os 110 conteúdos incertos, especialmente os PDFs digitalizados e o RAR.
- Reconciliar as fontes de dados e formatos Office antes de importar novos registros.
- Completar vínculos de produto/fornecedor dos novos documentos somente com evidência específica.
- Comparar possíveis versões e conferir emissão, vigência e cobertura de certificados. Certificado armazenado não prova vigência nem cobertura de toda a oferta.
- Finalizar os testes da Gestão IBIAG antes de ampliar Tropical Prospects.
