# Dossiê de consulta do pedido

Tela /gestao/dossie?order=ID, acessível por Pedidos e Operação do dia. API administrativa GET /api/orders/{id}/dossier. Não cria coleção, arquivo, tarefa, reserva, aprovação ou pagamento.

## Fontes e conferências

- Identidade histórica do pedido, país, Incoterm, data, situação e revisão.
- Cotação de origem quando explicitamente vinculada: referência e revisão preservadas no pedido; consulta da situação/revisão atual e unicidade do vínculo reverso a pedidos, inclusive arquivados. Sem cotação vinculada não é por si só uma pendência.
- Commercial Invoices e Packing Lists vinculados por order_id, incluindo cancelados para consulta. Compara a revisão comercial canônica de cada tipo com o pedido atual, reutilizando os mesmos snapshots dos módulos existentes.
- Estados ativos derivados pelas regras do painel operacional: ausente, rascunho, aprovado compatível, origem alterada ou múltiplos ativos. A compatibilidade da origem de um documento cancelado não o torna ativo ou aprovado.
- Embarque manual, rota, transportadora, referência de transporte e datas previstas/reais. Mostra pendências logísticas das regras existentes; não consulta transportadoras.

Totais são por pedido, limitados a 200 documentos de cada tipo. Excesso retorna 413 sem resultado parcial. Pedido ausente/arquivado retorna 404, ambiguidade e dados inconsistentes retornam 409. Pedidos cancelados não arquivados podem ser consultados; a situação permanece visível. Metadados com estado/revisão desconhecidos nunca aparecem aprovados. Se a origem comercial não for conferível, os documentos indicam origem não conferida.

## Limites

Consulta de registros atuais em múltiplas coleções, sem snapshot atômico: atualize antes de agir. Não é auditoria completa da autenticidade ou integridade do conteúdo dos arquivos. Não lê conteúdo, gera ZIP/PDF ou chama serviço externo. Não retorna custos de fornecedor, valores financeiros, condições de pagamento, notas privadas, históricos, caminhos de arquivos ou snapshots comerciais completos.

Arquivos gerais do CRM/produto/fornecedor não são anexados por semelhança de nome. Invoice e Packing List só entram pelo vínculo explícito ao pedido. Anexação de outros documentos a processo, matriz por produto/país, COA por lote, certificados de origem, licenças e submissões Siscomex continuam fora desta entrega. Não declara documentação obrigatória universal nem liberação aduaneira. Aprovações exibidas são internas, não aceite do comprador ou validação oficial.

A tela somente oferece links para os módulos existentes, cujas ações continuam exigindo revisão e confirmação próprias. Acesso exclusivo de administrador atual, com respostas private/no-store. Erros não exibem dossiê anterior como atual.

## Validação e instalação

Testes HTTP com mock e MongoDB real descartável verificam permissões, projeção privada, ausência completa de escrita, origem atual/desatualizada, cancelados, ambiguidade, limites e vínculo de cotação. Testes de interface verificam escolha explícita do pedido, links, falhas/atualização, respostas tardias e ausência de aprovação global. O cenário integrado no navegador percorre operação → dossiê, com Invoice/Packing List reais de teste, sem alterar as fontes ou registros comerciais.

Branch separada sobre qualidade e amostras. Não atualiza o Windows, não acessa o computador e não interfere na importação do Claude. Homologação real e integração na instalação serão posteriores à importação.
