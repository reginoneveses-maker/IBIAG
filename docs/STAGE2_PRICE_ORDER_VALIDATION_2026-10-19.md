# Etapa2 — cálculo salvo como origem do pedido

19/10/2026. Segunda entrega de desenvolvimento, posterior ao vínculo CRM→pedido do PR44. A etapa1 continua aguardando validação operacional no Railway. A etapa2 inteira não está concluída; esta entrega não foi publicada.

## Implementado

PR45: https://github.com/reginoneveses-maker/IBIAG/pull/45

Administrador pode abrir um rascunho a partir de cálculo salvo. O servidor reutiliza o motor de preços, resolve referências únicas/ativas e recalcula quantidade/preço/total em USD. A revisão conferida precisa coincidir com a origem relida ao salvar; caso contrário409, sem criar pedido. Valores/itens/memória forjados no navegador não prevalecem.

source_price_id/revision/snapshot ficam sob controle do servidor. A memória canônica preserva custos, impostos, câmbio, quantidade e resultados históricos. Origem/itens de pedido vinculado são imutáveis; revisão de quantidade/preço exige outro cálculo/rascunho. Edições posteriores no cálculo não reescrevem pedidos. Clientes antigos conservam a origem ao omitir campos novos.

Cálculo usado em pedido, inclusive arquivado/cancelado, não pode ser excluído. Exclusão e criação compartilham a trava existente. A interface trata recusa sem remover a linha ou gerar erro de navegação. Atalhos de CRM e preço podem ser usados juntos; são consumidos ao abrir qualquer formulário, e respostas atrasadas não substituem um rascunho manual.

Criar a partir do cálculo exige draft. Abrir/cancelar/conferir não grava. Rascunho não cria recebível nem movimenta estoque. Confirmação/embarque e movimentações continuam no fluxo existente. É formação de preço, não proposta comercial aprovada, assinatura ou apuração fiscal; Incoterm, datas, cliente e uso de estoque continuam explícitos. Não há envio automático nem consulta de câmbio/frete/tributos.

## Evidência final

SHA d00d6d86c13d8fd632c1366241e300bee9f37b4c; árvore0d238ff8ccb250ffe8d058b39f3180c98bae191a. Árvore local e remota comparadas e idênticas; workspace limpo após publicação da branch.

Pipeline https://github.com/reginoneveses-maker/IBIAG/actions/runs/39332768449 — concluída com sucesso.

| Verificação | Resultado |
|---|---|
| Backend CI, job118334743234 |370 testes e56 subtestes aprovados; sem skips no resumo final |
| Novos cenários HTTP |Dez cenários simulados e os mesmos dez executados com MongoDB descartável; nenhuma consulta ao banco da empresa |
| Frontend CI, job118334743649 |281 testes/15 suítes aprovados |
| Build |Compilação aprovada |
| Chromium |Cálculo salvo→alteração da origem→recusa da revisão antiga→nova conferência→rascunho→recarga→CRM/documentos; sem recebível de rascunho |
| Local |280 testes backend/48 subtestes e281 frontend aprovados;90 casos de ambiente não executados localmente, cobertos pelo CI |

Revisão de segurança: negação a anônimo/usuário comum/papel forjado; IDs/operadores/NUL/formatos inválidos; preço/câmbio/quantidade inválidos; referências ambíguas/inativas; memória e valores canônicos; revisão alterada; preservação histórica/clientes antigos; exclusão concorrente sem órfão; repetição sem segunda conta ou movimento. Dados e provedores são sintéticos/simulados. Teste Docker existente também passou no CI, sem imagem de produção publicada.

## Integração e próximos passos

Branch operations/price-order-draft-20261019. PR45 draft empilhado em operations/crm-order-link-20261019, base ff0ca9a, dependente do PR44. O filtro de PR do workflow inclui operations/** para testar essa sequência isoladamente; gatilhos de push/deploy não foram ampliados. Esta entrega não foi integrada em main, no candidato de segurança ou em produção.

Contrato/limites: docs/SAVED_PRICE_ORDER_DRAFT.md. Sequência: docs/STAGE2_OPERATIONS.md. Continuam pendentes propostas comerciais versionadas/aprovações, embarques manuais reais, documentos operacionais integrados e gestão diária. Liberação exige resolver os pontos da etapa1: banco/persistência/storage/proxy/ingressos e fluxos com contas autorizadas.

Nenhum serviço pago, crédito de fornecedor, backup/restore de produção, conta/registro real, deploy, reinício, migração ou mudança de rede foi acionado. Este relatório é separado da branch de aplicação para preservar a árvore testada.
