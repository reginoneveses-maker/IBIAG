# Packing List — validação da entrega

Registro em20/10/2026 UTC. Código em revisão no PR50; nenhuma alteração publicada no Railway ou integrada à main. Base: PR49, Commercial Invoice. Repositório reginoneveses-maker/IBIAG.

## Implementação

Documento vinculado ao pedido operacional confirmado/embarcado/entregue. Preparação só leitura, uma Packing List ativa por pedido, referências históricas não reutilizáveis. Grupos manuais de volumes com marcas distintas, embalagem, pesos líquido/bruto em kg, cubagem opcional e distribuição explícita por item. Todos os valores são totais do grupo, sem multiplicação pelo número de volumes. Quantidades em Decimal até12 casas; aprovação exige que cada item do pedido completo esteja exatamente alocado. Não infere país, embalagem, peso, lote, dimensão ou classificação. Peso/cubagem ausentes permanecem desconhecidos no rascunho, sem zero presumido.

Rascunho editável, aprovação interna explícita, documento aprovado imutável, cancelamento terminal. Motivo/versão/autor/histórico do servidor, trava de negócio/CAS, proteção de alterações da origem e resposta tardia. Não duplica estoque/conta/pedido e não envia ou assina documentos. Não executa migração, índice, backup, crédito ou serviço pago.

PDF privado, marca real IBIAG, DRAFT/CANCELLED em todas as páginas, fontes locais, dados selecionados e escapados. Sem preço, custo ou fornecedor. Limites:100 grupos/100 alocações por grupo,100000 volumes por grupo,50 eventos,256KiB por registro,30 páginas/2MiB por PDF. Glyphs indisponíveis recusados antes de aprovar. Verifica versão novamente depois da renderização; cópias já baixadas não são revogáveis. Histórico atingindo limite requer revisão administrativa.

## Testes locais

352 testes backend +48 subtestes passaram;162 casos exigindo MongoDB/Docker ficaram sem execução local. 321 testes de interface em19 suítes passaram na CI final, incluindo14 cenários específicos. Build passou e Chromium concluiu o fluxo integrado. Testes não acessam DB, arquivos ou dados reais de produção.

19 cenários HTTP se repetem no MongoDB descartável na pipeline: todas as rotas administrativas/anonymous/owner, whitelist/forgery, origem, datas/versões, conferência manual do país, quantidades precisas, distribuição por item, pesos/cubagem, imutabilidade/cancelamento, concorrência, integridade do pedido/financeiro, drift externo, PDF privado/determinístico/escapado, cancelamento durante geração, limites/falhas/glyphs e documento multipágina.

14 cenários UI: preparação sem gravação, payload mínimo, reaproveitamento de rascunho, grupos, confirmação, dirty state, conflitos, paginação/repetição, readonly, blob/revogação, respostas tardias, país ausente e pesos desconhecidos.

## Inspeção visual do PDF

Gerador tools/render_packing_list_review.py não importa servidor/env/DB e não usa rede. Documento sintético aprovado tem1 página; teste DRAFT com25 grupos/endereço longo/notas ocupa4 páginas. Todas as5 páginas foram renderizadas com Poppler e inspecionadas, sem corte/sobreposição. Totais e cabeçalhos presentes, marca de rascunho em todas as páginas. Normal/stress completos conservam o mesmo PDF após ajuste dos pesos ausentes.

Arquivo packing-review-2026-10-20/packing-list-synthetic.pdf: SHA256 f1bbd7d84244b9663fdf786393e423fc5267e91d59a126954ea7b74aae207b34. Exemplo marcado TEST DOCUMENT/TEST ONLY/NOT FOR COMMERCIAL USE. Não é documento comercial real.

## Pipeline

Primeira39351548333: backend512 +56 subtestes, UI319 e build passaram. Chromium recusou aprovação por país do comprador ausente no fixture. Corrigido para conferência/preenchimento manual do país quando ausente, com assert do motivo exato da recusa por249/250kg.

Segunda39352021907, SHA f8e2bd5ab8aa1259cdea11ef1a7ff47e2fe6d9bb: Mongo real, UI320, build e Chromium passaram. Depois foi ajustada a apresentação de pesos ausentes, exigindo nova execução. Terceira39352232495 incluiu teste UI cujo seletor atravessava spans do instrumentador; seletor substituído por rótulo acessível dos totais e passou localmente. Validação final no SHA7a102fb44f59731b8acf34783c2b3afd01bfc52d, árvorec4d3e321c0da1b8906139b5a9290739de9e4fb38, execução39352304799: **sucesso nos dois jobs**. Backend118399057129:514 testes +56 subtestes, sem skips, MongoDB real descartável e Docker. Frontend118399056846:321 testes/19 suítes, build e Chromium aprovados.

## Evidências do navegador

Artefato12233876589 da execução39352304799; head SHA confirmado7a102fb44f59731b8acf34783c2b3afd01bfc52d. ZIP2649076 bytes, SHA25610b57aa550b8e7afae3621e4b359d2d4803ff0141b1d9f5270d6b323bdc4716f, digest verificado antes de ler somente as duas imagens esperadas, com limite de tamanho e sem extração irrestrita. Desktop158044 bytes, SHA2566b61990383515b135c2d807dd6f6d150544e58dfbc518981d50c9e25e71b82a7; móvel57890 bytes, SHA25650e905ebdfaa32b71ef00dec3e7a9ab7173bc20862c28ce1fb9ff13ad0073ac2. Ambas inspecionadas, sem overflow; formulário aprovado readonly, dados sintéticos e estilo IBIAG.

## Pendências

Homologação pela equipe com contas/dados autorizados, integração e publicação condicionadas à etapa1 (persistência/storage e proxy/banco). Embarques parciais/devoluções/envio/assinatura não incluídos. Indicadores/gestão diária e validação do percurso integrado continuam na sequência. Não foi possível recuperar os critérios históricos completos das duas conversas citadas; contrato atual registrado em STAGE2_OPERATIONS.md e PACKING_LISTS.md, sem afirmar aceite integral do projeto original.
