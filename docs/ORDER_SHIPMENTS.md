# Embarque completo vinculado a pedido

Entrega de desenvolvimento da etapa 2. Não comprova homologação nem publicação em produção.

## Operação

O administrador confirma a venda no cadastro de pedidos e usa **Registrar embarque**. A tela em Gestão → Embarques registra referência, origem/destino, modal, responsável ativo, transportadora, reserva, documento de transporte, datas previstas/reais, observações e motivo da alteração. O responsável indicado não recebe acesso administrativo por essa indicação.

Um embarque cobre a quantidade integral de um pedido. Não há fracionamento, tracking externo, contratação de transportadora, emissão fiscal, geração de BL/AWB ou integração paga. As referências de documentos são texto; anexos e emissão de documentos operacionais precisam do fluxo próprio de documentos.

Situações: planejado → reservado → em trânsito → chegou ao destino → entregue. Planejado/reservado permitem cancelar o transporte; transporte cancelado pode voltar a planejado enquanto a venda continuar confirmada. Cancelar transporte não cancela a venda nem elimina a conta a receber. Cancelamento da venda continua explícito no cadastro do pedido. Não se reverte uma saída real para desfazer estoque: devoluções exigem fluxo próprio.

Saída/chegada previstas são obrigatórias e ordenadas. Trânsito exige saída real, chegada exige saída e chegada reais e entrega exige as três datas reais. Datas reais não podem estar no futuro nem contrariar a sequência ou anteceder o pedido. Datas reais já registradas são preservadas; origem/destino/modal ficam fixos depois da saída real. Alterações posteriores de observação, responsável e referências continuam auditadas. Pedidos antigos já embarcados/entregues podem receber registro retrospectivo compatível, sem executar uma segunda baixa.

## Integridade e segurança

- Rotas `GET /api/shipments`, `GET /api/orders/{id}/shipment` e `PUT /api/orders/{id}/shipment` exigem administrador consultado pela autenticação existente. Papéis enviados em cabeçalhos e indicação como responsável não concedem acesso.
- A gravação recebe campos logísticos estritos e versão inteira, rejeita campos extras/NUL e limita comprimentos. Não aceita itens, valores, autoria, carimbos de tempo ou histórico do navegador.
- O servidor relê o pedido vigente dentro da mesma trava de escrita do ERP, valida versão, responsável único/ativo, transição, datas e saldos e grava um único documento por comparação de versão. Pedido, embarque e evento ficam na mesma gravação. Não há outra coleção de embarques, conta financeira ou movimento avulso de estoque.
- Planejado/reservado/cancelamento de transporte mantêm o pedido confirmado; trânsito/chegada usam o pedido embarcado; entrega usa o pedido entregue. A reserva, baixa e conta a receber são as já derivadas do pedido. Não são duplicadas pela mudança logística.
- Atualizações genéricas de pedidos preservam o embarque armazenado e não podem trocar situação por fora do fluxo, exceto cancelar/rascunhar uma venda cujo transporte foi cancelado antes da saída.
- Histórico registra autor, data, versão, estado anterior/novo, motivo e alterações. Não há exclusão do histórico por esta API. Limites de 100 eventos e 256 KiB UTF-8 rejeitam nova gravação sem remover eventos anteriores. É um histórico da aplicação, não um arquivo inviolável contra administradores diretos do banco.
- Listagem paginada (50 por padrão, máximo 250) por situação/arquivo projeta só resumo; não inclui histórico, itens, custos ou memória do cálculo. Pedidos arquivados podem ser consultados, sem alteração logística. Nenhuma migração/índice/validador de produção é instalado.
- Conflito de versão mantém o formulário; o operador recarrega para conferir antes de tentar novamente. A tela não repete gravação automaticamente. Respostas antigas de listagem/abertura são ignoradas.

## Verificação

`backend/test_order_shipments.py` usa HTTP e base sintética isolada e repete os mesmos cenários em MongoDB descartável quando configurado. Cobre fluxo completo/estoque/recebível, permissões, dados inválidos, concorrência/versão, falsificação por rota genérica, cancelamento/reabertura, imutabilidade, projeção/paginação, falha antes do commit e preservação de histórico nos limites.

`frontend/src/pages/gestao/Shipments.test.jsx` cobre abertura por pedido, corpo/versionamento, conflito sem repetição, consulta arquivada, datas/rota preservadas, filtro/repetição e falha de abertura. O Chromium percorre CRM → cálculo → pedido confirmado → embarque completo → recarga → documentos, com todas as chamadas externas bloqueadas/simuladas e uma única conta a receber.

Resultados concretos de execução e CI são registrados no PR e no relatório de validação. Skips locais não equivalem à execução real de MongoDB/Docker. A liberação depende também da etapa 1 (proxy, persistência/banco/storage, acessos e ingressos no Railway).


## Atualização: histórico completo em páginas

O fluxo HTTP agora rotaciona os eventos antigos em blocos no mesmo banco, mantendo uma janela recente limitada e a consulta de todas as revisões. Os limites locais mencionados acima continuam como proteção das funções internas e de dados inválidos; não exigem descartar alterações antigas para salvar uma nova revisão válida. Ver OPERATION_HISTORY.md para atomicidade da referência, permissões, limites de bytes, falhas/retry e pendências de durabilidade em produção.
