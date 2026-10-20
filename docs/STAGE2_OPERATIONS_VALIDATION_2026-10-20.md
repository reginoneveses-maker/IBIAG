# Painel operacional e percurso integrado — evidências

20/10/2026 UTC. PR51, base PR50; repositório reginoneveses-maker/IBIAG. Candidatobed8008ced775f236b27d0e8c69f2c920e0dd7a3, árvore4b2b31474b06d6ee05d4b3c1bc0d92ce622c62da. Nenhuma integração na main ou publicação no Railway.

## O que foi implementado

Painel administrativo em Gestão →Operação do dia, consulta GET /api/gestao/operations. Filtros por situação, país exato e período inclusivo do pedido; pendência e paginação da lista. Cartões de recebimento vencido, previsão logística vencida, documentação a conferir, embarque ausente/cancelado e dados/vínculos a revisar. Datas de vencimento usam America/Fortaleza. Vence hoje não significa atraso. Estado recebido vem da operação financeira vinculada, sem somar moedas, inferir câmbio ou considerar invoice como recebimento.

Documentos aprovados só contam como prontos se a memória ainda corresponder ao pedido; rascunho, cancelado, ambíguo e desatualizado não são prontos. Estados/datas antigos inconsistentes pedem revisão. Lista não inclui preços/custos/fornecedores/notas/históricos. Links levam aos fluxos privados existentes; painel não grava nada, aprova, paga, envia mensagens ou ativa provedor.

Limites explícitos:1000 pedidos por conjunto de filtros,100 por página,2000 documentos ativos por coleção; acima disso,413 e filtro/refinamento, sem totais truncados. IDs de pedidos inválidos/duplicados:409. Autorização administrativa antes da leitura, incluindo proprietários comuns de empresas no CRM. Não usa lock de escrita, credencial, migração, serviço pago ou backup. Consulta de coleções separadas não equivale a snapshot transacional; decisões continuam usando versão e conferência próprias.

## Testes locais

361 testes backend +48 subtestes passaram;171 skips discriminados por falta local de MongoDB/Docker.328 testes de interface em20 suítes e build passaram. Oito cenários HTTP do painel +um percurso completo se repetem com MongoDB local descartável na CI; sete testes UI novos. Nenhuma execução usa base de produção.

Cobertura: acesso401/403/admin, leitura sem escrita/vazamento, filtros literais/calendário/limites, paginação e resumo completo, revisão documental, IDs/quantidades acima do limite, legado/datas/financeiro inválidos, atraso logístico e recebimento pela rota financeira. Teste de1hUTC comprova que em Fortaleza ainda é o dia anterior e que vencimento do dia não gera atraso. UI cobre erro/repetição sem zero fictício, filtros explícitos, respostas tardias, navegação e paginação.

## Um único processo, do CRM ao recebimento

O cenário test_stage2_end_to_end.py usa CRM/cálculo existentes →cotação com condições aprovadas →pedido único em rascunho sem conta →confirmação →Invoice/Packing List aprovadas →planned/booked/in_transit/arrived/delivered →recebimento pela rota real. Repete o recebimento e preserva paid_date. Em todas as etapas, permanece uma conta para esse pedido; estoque próprio sai10→8 uma única vez e reserva final fica0. PDFs aprovados permanecem byte a byte iguais após logística/pagamento. A cotação não pode gerar outro pedido. Painel final reconhece documentos atuais, entrega e recebimento sem pendências por essas regras. Todo registro é sintético e descartável.

## Pipeline e navegador

Execução39353860272 (245), SHAbed8008ced775f236b27d0e8c69f2c920e0dd7a3: **sucesso nos dois jobs**.532 testes backend +56 subtestes sem skips;328 testes UI em20 suítes, build e Chromium aprovados. Backend118404054923; frontend118404054802. Browser estende o percurso existente: documentação atual no painel →filtro entregue →lista de pendência vazia →reset →volta à Packing List, mais desktop/móvel sem overflow. A execução anterior39353381362 também passou; após inspeção visual, foram corrigidos rótulos de embarque em português e contagem singular. A versão final passou novamente, incluindo assert de “Embarque: Entregue”. Imagens desktop/móvel inspecionadas, sem overflow.

Artefato12233982734: headbed8008ced775f236b27d0e8c69f2c920e0dd7a3 confirmado, ZIP3103093 bytes com digestSHA25687952c5f0adb57af31474073693e89331ff1f8fa8b05a3a076ca7ea577f2af9d conferido antes de ler apenas os dois PNG esperados, com limite de tamanho. Desktop293404 bytes, SHA2569f82c04bcc84f356efb9404369ce8397eee6f51a0ec161df610d8b8ac1bfb3ed. Móvel158743 bytes, SHA25675d7954164c34f0fe9a325825867c5951e2e689a0440d6e892131c677dfab92a. Arquivos em operations-review-2026-10-20/.

## Limites de aceite

Não comprova produção, treinamento/aceite da equipe, envio/aceite do comprador, importação de dados reais, tracking externo, embarque parcial/devolução ou auditoria permanente. Históricos atuais de documento/embarque são limitados e exigem desenho de arquivo durável separado, condicionado à validação de persistência da etapa1. Contrato: OPERATIONS_DASHBOARD.md na branch do PR51.
