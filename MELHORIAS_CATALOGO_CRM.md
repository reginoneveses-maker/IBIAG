# Melhorias do catálogo e CRM local

Base: 2b838091a115555012c7ac7950d2c4ef9ebb3758.

- Pipeline: ordem A–Z por empresa, desempate por ID, 15 registros por página com opções 30/50/100 e seleção de página. Os contadores das colunas continuam representando todos os resultados filtrados. Busca e troca de quantidade reiniciam a página. A paginação é de apresentação: a carga dos registros ainda usa a API paginada existente.
- Portfólio de Produtos: um card por oferta já cadastrada (forma e fornecedor), mantendo produto e oferta originais. Exclusão no card de oferta atua sobre a oferta, com as proteções existentes do servidor. Não divide automaticamente textos que agrupem várias concentrações em uma única oferta; esses cadastros precisam de variantes confirmadas com atributos e fichas correspondentes.
- Ficha IBIAG: visualizar e baixar diretamente no card usando exclusivamente ibiag_file_path das specs explicitamente vinculadas à oferta por spec_ids. Não escolhe documento por semelhança de nome nem substitui pela versão original. Quando falta vínculo/arquivo, exibe pendência. O conteúdo da ficha deve ser revisado pelo responsável antes de ser cadastrado como versão IBIAG.
- E-mail e WhatsApp: botões desativados com Integração pendente. Não há envio nem integração implantada.
- Área de specs por fornecedor identificada como Specs originais. Os grupos por fornecedor e a separação dos arquivos original/IBIAG existentes foram mantidos. O atalho do card abre o fornecedor correspondente.

Não altera backend, Docker, Mongo, configuração, credenciais ou registros de negócio. Não converte os 635 documentos nem cria vínculos automaticamente. A captura do painel instalado indicou zero specs estruturadas: se persistir, cadastrar/revisar as versões IBIAG e vinculá-las às ofertas é necessário para ativar os botões nos cards.

Validação: 356 testes de interface em 27 suítes passaram, incluindo 7 verificações direcionadas; build de produção passou. Não instalado no computador do usuário nesta etapa.

Instalação: seguir ATUALIZACAO_LOCAL.md com esta pasta como fonte, mantendo volume ibiag-local_mongo_data e .env.local originais e atualizando apenas api e web. Preservar backup e instalação anterior.
