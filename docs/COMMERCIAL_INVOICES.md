# Commercial Invoice vinculada ao pedido

## Uso

Em Pedidos, abra Criar / ver Commercial Invoice em uma venda confirmada, embarcada ou entregue. A conferência não grava automaticamente. Se já existir invoice ativa, abre o documento existente. A Central de Documentos e os menus administrativos têm atalho para a área privada de Commercial Invoices.

Confira valores, emitente legal, registro fiscal, endereços, comprador, destinatário, data, local do Incoterm, condições, origem/HS ou NCM por item e representante. Esses dados não são inventados. Condições de pagamento/entrega provenientes de uma cotação aprovada são preservadas, com campos somente leitura e rejeição de alteração também na API. O nome do comprador, produto, quantidade, preço, Incoterm e total vêm do pedido. País do comprador é preservado quando existe no pedido; quando está ausente, deve ser informado e conferido nesta invoice.

Salvar rascunho permite continuar a preparação. Conferir PDF e Baixar PDF usam a rota autenticada; DRAFT identifica cada página do rascunho. Depois de salvar as alterações, informe motivo, confirme a conferência cadastral/comercial/aduaneira e use Aprovar invoice internamente. O servidor verifica os campos obrigatórios, a memória do pedido e se o PDF pode ser renderizado antes de registrar a aprovação. Os valores são em USD; frete e acréscimos precisam estar no cálculo/pedido original e não são somados novamente.

Aprovação interna não envia o documento, gera assinatura manuscrita/digital, certifica classificação fiscal/origem nem valida despacho. O campo representante é nome digitado, identificado assim no PDF. Exigências específicas do destino precisam ser conferidas com os responsáveis pela operação. Não é nota fiscal brasileira e não escreve na coleção invoices existente de NF-e.

Depois da aprovação, condições e dados ficam imutáveis. Para corrigir, cancele com motivo e prepare outro número. Cancelamento é terminal, mantém histórico e referência e permite uma nova invoice no pedido. O PDF cancelado tem CANCELLED em cada página; cópias já baixadas não são modificadas retroativamente.

## Integridade e acesso

- Apenas administradores acessam a preparação, lista, detalhe, criação, edição, decisões e PDFs; o proprietário comum do CRM não ganha acesso comercial/financeiro por este vínculo.
- Coleção commercial_invoices, uma invoice draft/approved por pedido. Referência/id não são reutilizados, mesmo após cancelamento. Criação e decisões usam a trava de escrita compartilhada, versão e motivo obrigatórios, e comparação de versão na gravação.
- A memória é uma lista explícita de campos comerciais do pedido. Não copia o objeto inteiro, custos, margem, fornecedor, snapshots internos de preço/cotação, notas internas ou histórico do pedido. A renderização aplica outra lista explícita de campos externos.
- Criar exige a versão atual do pedido. Aprovar confere uma revisão SHA256 dos campos comerciais: cliente/país, referência, itens, total, Incoterm, data, vencimento e condições aprovadas de origem. Mudanças somente logísticas ou registro de pagamento não invalidam a memória comercial.
- Enquanto houver invoice draft/approved, a gravação do pedido bloqueia mudanças comerciais incompatíveis, cancelamento da venda e arquivamento. Cancelar a invoice libera a regra documental; as regras próprias de estoque, venda embarcada e financeiro continuam vigentes.
- Listas são resumidas, ordenadas por id e paginadas em até250, com filtro por situação/pedido. Detalhe inclui histórico limitado a50 eventos; cada documento tem limite adicional de256KiB.
- Entrada estrita rejeita propriedades extras, operadores/objetos, booleanos como versão, controles de texto, datas inexistentes/futuras, emissão anterior ao pedido, itens aduaneiros fora de ordem e HS/NCM com formato diferente de6/8/10 dígitos. Formato não equivale a classificação fiscal confirmada.
- PDF é gerado em memória, sem nova cópia no acervo compartilhado, bucket, serviço pago ou URL pública. Usa Cache-Control: private, no-store, nosniff e nome de arquivo controlado pelo servidor. A versão é conferida novamente depois da geração; decisão concorrente impede devolver uma versão antiga como atual.
- Todo texto é escapado antes da diagramação. Não carrega HTML, imagens, links ou fontes fornecidos pelo usuário. Fontes locais do ReportLab e logo vetorial derivado da apresentação IBIAG. Não há JavaScript, anexos ou links ativos no PDF gerado.
- Metadados usam a data da revisão armazenada, não uma data fixa de teste. O mesmo documento/versão produz os mesmos bytes. Quantidade/preço são preservados até12 casas decimais, total por item/geral segue o arredondamento de centavos do ledger existente. Limites técnicos: quantidade/preço até10^12, total até10^12 USD,100 itens,30 páginas e2MiB por PDF.

## Interface

Bloqueia aprovação com alterações não salvas, sem motivo ou sem confirmação explícita. Não repete escritas automaticamente em conflitos. Um pedido não abre outro rascunho se já existe invoice ativa. Respostas tardias de consulta não substituem outro documento aberto; PDF atrasado não reaparece após uma decisão. URLs blob de prévia/download são revogadas. A prévia reutiliza documentPreview e o visualizador PDF existente, sem iframe ou token em URL.

## Testes e revisão

backend/test_commercial_invoices.py executa23 cenários HTTP locais e as mesmas23 variantes em MongoDB descartável quando TEST_MONGO_URL é configurado. Cobre autorização, falsificação, consistência, aprovação/congelamento, concorrência de criação/decisão/alteração/download, cancelamento, limite/tamanho/erro sem vazamento, precisão e ausência de dados internos/ações ativas no PDF. Inclui documento paginado com25 itens, cabeçalho/marca d'água repetidos e nenhum item perdido.

CommercialInvoices.test.jsx cobre preparação sem gravação, payload mínimo, abertura de invoice existente, motivos/confirmação, dados alterados, conflito sem repetição, prévia privada, descarte de consulta/PDF tardios e recuperação da lista. O fluxo Chromium percorre pedido entregue→invoice→PDF DRAFT→aprovação→PDF aprovado→recarregar e verifica bytes/texto do download, bloqueio de alteração do pedido e ausência de nova conta. Mantém os cenários anteriores de CRM/cotação/embarques/documentos/acesso e bloqueia rede externa.

O script tools/render_commercial_invoice_review.py produz documentos de QA exclusivamente sintéticos, sem banco, credenciais, startup ou rede. Foram renderizados e inspecionados o exemplo de uma página e o teste de25 itens em cinco páginas, com textos longos e acentos.

## Limites de liberação

A fonte embarcada cobre o alfabeto latino usado nos exemplos, não todos os sistemas de escrita. Caracteres sem glifo geram erro antes da aprovação, sem substituição silenciosa. Suporte tipográfico a outros alfabetos exige extensão e validação próprias. Sem assinatura, envio, validação automática de cadastros/HS/NCM, impostos ou regras aduaneiras, emissão NF-e, Packing List, parciais ou devoluções nesta entrega.

A etapa1 segue pendente de banco/persistência/storage/proxy e homologação com contas autorizadas. Testes sintéticos, PDF diagramado e CI não certificam operação em produção. Nenhuma implantação, migração, índice, backup ou serviço pago faz parte desta entrega.

Referências de desenho consultadas em20/10/2026: https://www.trade.gov/commercial-invoice e https://www.trade.gov/common-export-documents . Descrevem documentos comerciais e a necessidade de conferir requisitos do destino; não são usadas como certificação de conformidade de uma exportação brasileira.
