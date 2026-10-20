# Cotações comerciais com aprovação interna

## Escopo e uso

Gestão → Preços → Criar cotação abre uma conferência do cálculo salvo, sem gravar automaticamente. O administrador escolhe a empresa do CRM e informa referência, validade, Incoterm, pagamento, entrega, observações e motivo. Salvar gera um rascunho de cotação. Aprovar internamente exige uma segunda ação com motivo; não registra aceite do comprador, envio, pedido, reserva de estoque ou recebimento.

A cotação aprovada e vigente oferece Preparar pedido em rascunho. Somente Salvar no formulário de pedido cria o pedido. Cliente, Incoterm, quantidade e preço vêm da memória aprovada e não são editáveis. Estoque próprio, datas e notas operacionais continuam no pedido. Confirmação, embarque e financeiro reutilizam o fluxo existente. Cada cotação pode gerar somente um pedido, inclusive se esse pedido for posteriormente cancelado ou arquivado.

## Contrato e integridade

- GET /api/quotations: lista administrativa resumida, filtro de situação/empresa, páginas de até250, ordenação por id. Sem custos, condições extensas ou histórico na lista.
- GET /api/quotations/{id}: detalhe administrativo com histórico e vínculo derivado do pedido.
- POST /api/quotations: exige id/referência únicos, empresa válida, cálculo vinculado à oferta e revisão SHA256 conferida. Quantidade, preço e total são recalculados pelo servidor.
- PUT /api/quotations/{id}: apenas condições de rascunho, com versão e motivo obrigatórios. Origem, comprador e valores são imutáveis; recalcular ou trocar comprador exige outra cotação.
- POST /api/quotations/{id}/status: aprovação interna ou cancelamento explícitos. Aprovação exige validade e referências atuais válidas. Cancelamento é terminal e não é permitido depois da conversão.
- GET /api/quotations/{id}/order-draft: conferência sem gravação; exige aprovação, validade UTC e ausência de pedido anterior. Revalida empresa/produto/fornecedor/oferta. Oferta inativa, religada ou com unidade alterada bloqueia conversão.
- POST /api/orders recebe source_quote_id e source_quote_revision. Sob a trava compartilhada, refaz todas as validações e obtém a memória do banco; descarta snapshots, itens, cliente e total enviados pelo navegador. Não aceita confirmação direta nem origem simultânea de cálculo.

A coleção quotations mantém uma memória limitada do cálculo original, condições e até50 eventos. Cada evento registra autor autenticado, data, versão, motivo e alterações. Limite adicional de256KiB por documento; ultrapassá-lo não grava parcialmente. Somente administradores acessam todas as rotas. Não há exclusão destrutiva de cotação ou novos privilégios para proprietários comuns do CRM.

Empresas, produtos, fornecedores, ofertas e cálculos referenciados não podem ser excluídos. Substituição destrutiva de portfólio também é bloqueada. Não há migração, índice ou escrita de produção nesta entrega.

A conversão grava somente o pedido, sem um segundo estado de conversão na cotação. Sua associação é consultada em orders.source_quote_id sob a trava de escrita existente, inclusive para registros arquivados/cancelados. Isso evita divergência entre duas gravações. Mudanças posteriores no CRM, no preço ou em rótulos do catálogo não reescrevem a memória aprovada. Referências e saldos ainda são validados. Clientes antigos que omitem os campos novos preservam o vínculo armazenado.

## Verificação e limites

backend/test_commercial_quotations.py cobre HTTP, identidade e valores canônicos, versões, validade, autorização, falsificação, preservação histórica, exclusões, falhas antes da gravação, limites de histórico/tamanho e concorrência decisão/conversão. Os mesmos17 cenários são executados contra MongoDB descartável quando TEST_MONGO_URL está configurado; sem isso, são skips declarados. A suíte existente também verifica a integração contábil e o estoque.

Quotations.test.jsx e Orders.test.jsx verificam conferência sem gravação, payload mínimo, condições editadas, motivos, bloqueios, conflito sem repetição automática, respostas tardias, lista/paginação e preparação do pedido. Chromium percorre cálculo→cotação→aprovação interna→alteração do cálculo original→pedido único e verifica preservação da quantidade/valor, financeiro sem duplicação e nova conversão bloqueada. Provedores externos são bloqueados no navegador e dados são sintéticos.

Não inclui PDF comercial, envio, assinatura/aceite externo, cotação com vários itens, parcelamento financeiro ou devoluções. Homologação com contas autorizadas e liberação permanecem dependentes da etapa1: banco/persistência, armazenamento, proxy reverso e evidência de segurança em produção. Código testado em desenvolvimento não equivale a funcionalidade liberada.


## Atualização: histórico completo em páginas

O fluxo HTTP agora rotaciona os eventos antigos em blocos no mesmo banco, mantendo uma janela recente limitada e a consulta de todas as revisões. Os limites locais mencionados acima continuam como proteção das funções internas e de dados inválidos; não exigem descartar alterações antigas para salvar uma nova revisão válida. Ver OPERATION_HISTORY.md para atomicidade da referência, permissões, limites de bytes, falhas/retry e pendências de durabilidade em produção.
