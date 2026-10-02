# Pedidos, compras, estoque e financeiro

## Pedidos

Pedidos são registrados com itens de produtos e ofertas existentes. Quantidade e preço USD devem ser positivos; o total é calculado no servidor. Confirmação exige data do pedido e vencimento.

- Rascunho: sem reserva ou conta automática.
- Confirmado: uma conta a receber em USD; reserva quando `track_stock` é verdadeiro.
- Embarcado: baixa única da quantidade de estoque próprio e mantém a mesma conta.
- Entregue: mantém a baixa e a mesma conta, sem segunda movimentação.
- Cancelado: libera reserva e remove a conta projetada; não permitido após embarque ou recebimento financeiro.

Entrega direta pelo fornecedor não movimenta estoque próprio. Retorno de mercadoria e estorno efetivo exigem um fluxo de devolução separado; esta implementação recusa a reversão de embarques para evitar reentrada implícita indevida.

## Compras

Fornecedor cadastrado, quantidade, preço, moeda, data e vencimento são obrigatórios. O servidor calcula o total. Toda compra operacional não cancelada gera uma conta a pagar na própria moeda.

Pagamento e recebimento físico são independentes. `stock_received` indica recebimento; `track_stock` indica entrada em estoque próprio, que exige produto cadastrado e unidade correspondente. Compra paga antes da entrega não acrescenta estoque. Recebimento posterior acrescenta uma vez e conserva pagamento.

Recebimento não pode ser apagado ou cancelado. Produto, quantidade, unidade e modo de estoque tornam-se imutáveis após receber. Valores, vencimento e fornecedor pagos não podem ser alterados.

## Integridade

Um registro de pedido ou compra é a fonte do movimento e da conta. Não há segunda gravação que possa ficar parcialmente aplicada: saldo e financeiro são calculados a partir dos registros. O saldo armazenado do produto é a base; o saldo exibido incorpora movimentos e reservas. Ajuste manual administrativo informa o saldo físico atual, recalculando a base sem apagar os movimentos.

Uma trava atômica de MongoDB com `_id` único serializa gravações de estoque entre processos. A validade é conferida antes da gravação, com margem de 60 segundos e timeout de conexão de 45 segundos. Registros têm versão para recusar edição desatualizada. Novo POST com identificador já existente é recusado; marcar o mesmo estado de pagamento novamente preserva a data original.

Pedidos/Compras anteriores sem `workflow_enabled` não geram automaticamente movimentos ou contas. Ao editar e salvar uma operação antiga com os dados obrigatórios, ela passa pelas regras novas; é necessária conferência para evitar duplicar uma conta manual preexistente.

Pedidos em rascunho ou cancelados e compras canceladas podem ser arquivados e restaurados por administrador. Produtos e ofertas vinculados ficam protegidos contra exclusão que romperia referências. Totais financeiros são separados por moeda; não se presume câmbio.

## Validação automatizada

`test_business_workflow.py` verifica as transições e regras financeiras/estoque. `test_business_api.py` executa as funções reais da API com banco simulado, incluindo concorrência de trava, conflito de versão, repetição, insuficiência e falha antes da gravação. Isso não substitui validação do fluxo pela interface e pelo banco real após deploy.
