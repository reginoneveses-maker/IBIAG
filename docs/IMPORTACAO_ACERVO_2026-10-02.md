# Importação do acervo IBIAG — 2 de outubro de 2026

## Estado confirmado em produção

- Portfólio: 136 produtos, 24 fornecedores e 145 ofertas provenientes da tabela oficial.
- Preços textuais preservados, incluindo faixas, volume e “Sob consulta”. Comissões percentuais e os oito textos “Em negociação” restaurados sem substituir produtos, preços ou documentos.
- CRM: 1.233 contatos novos e quatro registros atualizados. São contatos de arquivos fornecidos pelo usuário; interesse de compra e atualidade dos dados ainda não foram validados.
- ZIPs 1, 2 e 3: 785 entradas de arquivo, 693 conteúdos únicos por SHA-256 e 92 repetições exatas. Esta contagem não inclui expansão dos ZIPs aninhados.
- 236 PDFs importados em 11 lotes. Arquivos originais preservados no armazenamento persistente da aplicação, com origem registrada nas observações.
- 133 documentos vinculados a fornecedores. Destes, 72 fichas específicas vinculadas a 69 ofertas de produto/fornecedor. Vínculos ambíguos de forma, fornecedor ou organicidade não foram aplicados.
- Abertura de PDF na Central de Documentos verificada visualmente usando a ficha de cacau liofilizado da Horta da Terra.

## Importação retomável

`POST /api/documents/import-batch` exige administrador e recebe um ZIP com `manifest.json` e PDFs em `files/<número>.pdf`. Cada registro contém `path`, `file_name`, `category`, `notes` e opcionalmente `title`. Limites: 40 MB de upload, 30 MB por entrada, 80 MB descomprimidos e 100 documentos. O lote inteiro é validado antes de gravar. Reenvios ignoram conteúdos já importados pelo SHA-256.

`POST /api/documents/link-batch` exige administrador e recebe JSON com `sha256`, `supplier_name`, `product_name` opcional e `kind` (`spec` ou `other`). Documento, fornecedor, produto e oferta precisam existir e os vínculos não podem conflitar com associações anteriores. O plano inteiro é validado antes de alterar dados. Os IDs são adicionados às ofertas sem substituir anexos existentes.

Comissões: `POST /api/portfolio/restore-commissions` permite simular o plano antes de atualizar exclusivamente `commission`, `commission_text` e `updated_at`. A importação geral do portfólio com substituição não deve ser usada para atualizar comissões.

## Validação realizada

- Sintaxe do backend.
- Simulação com os 236 PDFs reais: 11 lotes, reenvio sem duplicatas e rejeição de caminho indevido antes de gravar.
- Vínculos: associação de fornecedor/produto, reenvio aditivo, plano inválido sem alteração e preservação dos arquivos.
- Builds e publicações dos serviços frontend e API concluídos com sucesso.
- Contagens e associações conferidas pela interface autenticada em produção.

## Trabalho pendente

- ZIP 4: download falhou duas vezes; usuário informou que vai reenviar.
- Revisar os outros 457 conteúdos únicos dos ZIPs disponíveis. Nem todos são documentos pertinentes ao negócio; há programas de trading, imagens e arquivos de classificação incerta. Não apagar originais.
- Expandir e deduplicar ZIPs aninhados antes de fechar o índice completo.
- Completar os vínculos ainda não confirmados e revisar possíveis versões de documentos.
- Extrair e conferir emissão, validade e cobertura dos certificados. Um certificado armazenado não equivale a certificação vigente ou cobertura de toda a oferta do fornecedor.
- Consolidar índice mestre ao concluir a revisão dos quatro ZIPs.
- Concluir e testar a Gestão IBIAG antes de ampliar o trabalho no Tropical Prospects.
