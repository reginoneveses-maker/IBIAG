# Cálculo salvo → pedido em rascunho

Etapa2, segunda entrega, 19/10/2026. Complementa CRM→pedido sem recriar calculadora, pedidos, estoque ou financeiro. Base: PR44/ff0ca9a. Desenvolvimento isolado; sem liberação em produção.

## Fluxo

1. Administrador calcula e salva um preço na tabela existente de Gestão→Preços. Para gerar pedido, o cálculo precisa de oferta ativa com produto/fornecedor únicos, quantidade e preço positivos e câmbio manual positivo que produza valor de venda positivo em USD.
2. “Criar pedido” abre uma conferência. GET /api/prices/{id}/order-draft é administrativo e somente leitura: resolve referências, recalcula com o motor atual e fornece quantidade, unidade, preço unitário USD, total, memória e revisão da origem. Não grava pedido nem altera a oferta.
3. Escolher empresa do CRM ou cliente manual e revisar os demais campos. O rascunho tem um UUID próprio; abrir, cancelar ou recarregar a conferência não cria operação. O parâmetro do atalho é consumido ao abrir qualquer formulário, inclusive manual; respostas atrasadas são ignoradas. Atalhos com price e lead preenchem ambos juntos.
4. Salvar usa POST /api/orders existente. O servidor relê/recalcula o preço e exige a mesma revisão conferida. Mudança da origem exige abrir/conferir novamente, com409 e nenhum pedido criado. Itens/totais/memória recebidos do cliente não prevalecem. A criação a partir do cálculo só aceita status draft.
5. Confirmar ou embarcar depois exige edição explícita e as datas/regras existentes. Rascunho não reserva/baixa estoque nem gera recebível. Não há segundo ledger: confirmação, embarque e recebimento continuam usando os registros existentes.

## Memória e integridade

source_price_id referencia o cálculo; source_price_revision é SHA-256 determinístico da memória canônica; source_price_snapshot preserva entradas e resultados calculados, fornecedor, oferta/produto, moeda/câmbio, impostos/custos, quantidade, margem e datas persistidas. O hash identifica a revisão dos dados, não é assinatura ou aprovação jurídica e não contém segredo de autenticação. Datas ausentes de registros legados não são substituídas por agora ao calcular a revisão.

O servidor preenche esses três campos; o navegador envia apenas a referência/revisão, sem retransmitir a memória completa ao salvar. Valores forjados são descartados; atualização por cliente antigo que omite os campos conserva a origem. Origem e itens de pedido vinculado não podem ser trocados/alterados; para rever quantidade/preço, salvar/revisar o cálculo e criar outro rascunho. O rascunho anterior pode ser arquivado pelas regras existentes, sem apagar histórico. Nome/pais do cliente seguem o vínculo CRM e sua memória histórica.

Editar o cálculo depois não reescreve pedidos existentes. Cálculo referenciado não pode ser excluído, mesmo se o pedido estiver arquivado/cancelado. Exclusão e criação usam a trava existente, evitando referência órfã por concorrência. Produto/oferta/fornecedor inexistentes, inativos ou ambíguos, cálculo inválido e origem sem oferta exigem revisão; não se adivinham vínculos por nome. Informações históricas de custo permanecem administrativas.

## Escopo e limites

É uma memória de formação de preço usada como origem de rascunho, não uma proposta comercial aprovada/assinada. Não gera/envia proposta, não confirma negócio, não muda etapa do CRM, não emite documento fiscal nem faz consulta de câmbio/frete/tributação. Incoterm, entrega, vencimento e uso de estoque continuam sendo decisões explícitas no pedido; esta entrega não presume obrigações logísticas pelo cálculo salvo. Pedidos continuam em USD, usando o resultado USD do motor existente; não introduz conversão contábil ou moeda nova.

Cálculos podem ser reutilizados para pedidos diferentes; repetição do mesmo POST/UUID é recusada pelo fluxo existente, sem duplicar pedidos, estoque ou contas. O endpoint de conferência não certifica fornecedor, contato, viabilidade fiscal, disponibilidade física ou aprovação interna. Papéis por setor, propostas comerciais versionadas e aprovações formais precisam de entregas próprias.

## Testes e publicação

backend/test_order_price_source.py contém dez cenários HTTP, repetidos em MongoDB local descartável no CI: conferência somente leitura, números canônicos, valores forjados, revisão alterada, preservação histórica/clientes antigos, origem manual, erros/referências ambíguas, permissões, exclusão concorrente e confirmação/embarque/repetição. Não usa banco da empresa.

Orders.test.jsx e Precos.test.jsx cobrem atalho, campos congelados, escolha explícita de cliente, revisão rejeitada, origem inválida, resposta atrasada e exclusão recusada sem desaparecer o cálculo. O Chromium percorre mudança do cálculo durante a conferência, rejeição da revisão antiga, nova conferência, salvamento/recarga e retorno ao CRM/documentos.

A pipeline passa a aceitar PRs contra operations/** para validar entregas empilhadas sem integrar funcionalidades da etapa2 ao candidato de segurança. Não altera gatilhos de deploy, serviços, segredos, provedores ou backups. Resultados e SHA final serão registrados no PR/relatório após execução completa. Liberação permanece dependente da validação operacional da etapa1.
