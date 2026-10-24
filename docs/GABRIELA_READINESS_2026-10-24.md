# Prontidão para apresentação à Gabriela

Candidato isolado: PR #60, base #59 → #58 → composição do Claude. Não é uma liberação de produção. Código anterior e checkout com alterações locais preservados. O ambiente Linux anterior não está disponível; a reconstrução atual tem seus próprios commits e evidências.

## Implementado nesta etapa

- IBIAG: exportação privada de 1–25 empresas explicitamente selecionadas, somente por administrador, sem valores/notas/responsáveis ou gravação na origem. Botão no detalhe do Pipeline, proteção contra cliques duplicados e preservação da tela em erro.
- ExportHub: prévia anterior mantida, mais importação controlada de empresas/contatos. Proprietário, mesma origem, JSON limitado, confirmação literal, hash e revisão atual; empresas existentes precisam de confirmação explícita. Não sobrescreve campos. Reenvio idempotente, concorrência guardada, falha parcial sem commit e reconciliação de resposta perdida.
- Proveniência incorporada atomicamente à coleção comercial e à exportação/restauração manual. Endpoints genéricos não removem/modificam origens nem apagam entidades vinculadas. Alterações normais de campos e arquivamento continuam possíveis.
- Navegação IBIAG: Gestão → Da empresa ao embarque, com dez etapas e links para CRM, fornecedor, produto, calculadora, cotação, pedido, Commercial Invoice, Packing List, embarque e conferência. Marcação transitória não muda status dos registros.
- Ensaio comercial usando o motor de preços existente: 1.000/1.500 kg, custos, margem e câmbio fictícios, valores reconciliados e pesos/volumes. Sem salvar ou gerar documentos reais.
- Roteiro completo e arquivo fictício de intercâmbio disponíveis no repositório.

## Evidências e limites

A primeira CI deste PR (40073368388, commit dda1f55) aprovou backend, frontend/build/percurso Chromium e ExportHub/build/D1/R2/recuperação/regressões de documentos. A navegação e os testes adicionais foram acrescentados depois; seus resultados finais devem ser consultados no head do PR, sem atribuir aprovação de um commit anterior a um novo estado.

Verificação local da reconstrução: nove testes HTTP/SQLite de importação, 13 de saúde/integridade, 17 de PDFs/prévia, TypeScript, importação concorrente D1/R2 e restauração manual passaram. CI inclui testes reais MongoDB descartáveis, todos os testes de interface, builds, o percurso comercial completo Chromium e importação em tela de 390px. Não confundir fixtures com dados reais.

Análise de dependências: 25 PRs anteriores revisados; merge-tree sem conflitos na composição #28/#44–#59 e Claude. #19–#27 se sobrepõem à composição, com conflitos ao reaplicar individualmente. #53 continua separado e não executado. Snapshot: CRM_INTEGRATION_CONFLICT_REVIEW.json. Nenhum merge foi feito.

## O que impede utilização real

| Item | Situação |
|---|---|
| Avaliação da interface por Gabriela | Pendente; usar roteiro e dados fictícios |
| Instalação e dados do computador | Não alterados nem homologados por esta etapa |
| Migração documental #59 | Preparada, não aplicada em ambiente real |
| Importação empresas/contatos | Código/testes prontos; flag desativada no ambiente real |
| Integração de autenticação MongoDB/D1 | Pendente; contas e permissões continuam separadas |
| Transferência entre apps de fornecedores/produtos/preços/cotações/pedidos/PDFs/embarques | Pendente; não há sincronização automática nem equivalência de IDs/revisões |
| Fluxo comercial nativo IBIAG | Módulos preservados e exercitados pelo teste integrado; requer homologação de negócio |
| Fluxo comercial nativo ExportHub | Módulos do Claude preservados e regressões existentes mantidas; requer homologação |
| Conciliação dos dados históricos | Não executada; sem exclusão ou fusão automática |
| Pesquisa Trade Intelligence com credenciais reais | Não executada; provedores pagos permanecem bloqueados conforme configuração existente |
| Produção, despesas e backups automáticos | Não autorizados, não acionados |

A demonstração guiada não é uma sincronização completa dos dois sistemas. Antes do uso diário, será necessário escolher uma fonte de verdade para catálogo, custos, moedas, identidades e versões comerciais; validar a migração/recuperação e obter a autorização de liberação. O presente trabalho não presume que essa escolha já foi feita.
