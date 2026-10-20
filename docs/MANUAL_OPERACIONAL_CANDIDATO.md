# IBIAG — Manual operacional da versão em revisão

Data: 20/10/2026, America/Fortaleza.

Este manual descreve o candidato operations/document-history-20261020, commit 43715ff26f66666b130d2a67c9d18ef68a8beab4. As funções novas ainda não foram publicadas. Não confundir este repositório com o site ExportHub anteriormente criado em outro artefato. O manual não afirma conclusão de todos os dez setores ou homologação comercial.

## Índice

1. Acesso e responsabilidades
2. CRM e preparação da venda
3. Cálculo e cotação
4. Pedido, estoque e recebível
5. Commercial Invoice
6. Packing List
7. Embarque
8. Financeiro e compras
9. Operação do dia
10. Histórico e conflitos
11. Roteiro de conferência
12. Situação de publicação

## 1. Acesso e responsabilidades

Utilize uma conta individual autorizada. Os fluxos de pedidos, preços operacionais, cotações, documentos comerciais, embarques e painel descritos aqui são administrativos. Ser proprietário de uma empresa no CRM ou responsável por um embarque não concede acesso ao financeiro ou à administração.

A configuração real de autenticação do banco, persistência, proxy e contas continua pendente. Não utilizar a aprovação dos testes de desenvolvimento como certificação de segurança do ambiente publicado.

## 2. CRM e preparação da venda

Na ficha da empresa, o administrador pode usar Criar pedido para esta empresa. Também é possível selecionar Empresa do CRM no formulário de pedidos. Abrir o formulário não salva pedido, altera etapa comercial ou movimenta valores.

Confira a identidade e o país. O servidor obtém os dados do cadastro. Alterações posteriores no CRM não reescrevem automaticamente a identificação histórica do pedido. Trocar ou remover o vínculo exige que o pedido ainda seja rascunho.

Uma empresa ligada a pedido não pode ser excluída, mesmo se o pedido estiver cancelado ou arquivado. Cadastros antigos não são associados por semelhança de nome.

## 3. Cálculo e cotação

Em Gestão → Preços, confira o cálculo salvo antes de usar Criar cotação. Escolha a empresa do CRM e preencha referência, validade, Incoterm, condições de pagamento e entrega, observações e motivo.

Salvar cria um rascunho. Aprovar internamente é uma ação separada e exige motivo. Não registra aceite do comprador, envio, reserva de estoque ou recebimento.

Uma cotação aprovada e vigente permite preparar um pedido. O pedido só é criado ao salvar seu formulário. Cliente, quantidade, preço e condições vêm da memória aprovada. Para mudar comprador ou valores, prepare outra cotação com o cálculo correto. Cada cotação gera somente um pedido, inclusive se ele for cancelado posteriormente.

Frete e acréscimos precisam estar corretamente refletidos na origem comercial; a invoice não os soma novamente.

## 4. Pedido, estoque e recebível

| Situação | Efeito operacional |
| --- | --- |
| Rascunho | Sem reserva ou conta automática |
| Confirmado | Uma conta a receber em USD; reserva quando usa estoque próprio |
| Embarcado | Baixa única do estoque próprio, conservando a conta |
| Entregue | Conserva a mesma baixa e a mesma conta |
| Cancelado | Libera reserva e retira a conta projetada; recusado após embarque ou recebimento |

Antes de confirmar, confira itens, quantidade, preço, data e vencimento. Entrega direta pelo fornecedor não movimenta estoque próprio.

Não crie uma conta manual adicional para uma venda que já possui recebível derivado. Pedidos antigos sem o fluxo operacional precisam de conferência antes de editar/salvar para evitar sobreposição com contas manuais antigas.

Documentos ativos podem bloquear mudanças comerciais, cancelamento ou arquivamento. Cancele o documento incorreto pelo próprio fluxo e examine as restrições restantes; não apague registros para contornar a regra.

## 5. Commercial Invoice

Em Pedidos, use Criar / ver Commercial Invoice em venda confirmada, embarcada ou entregue. Se houver documento ativo, o sistema abre esse documento.

Confira emitente legal, registro fiscal, endereços, comprador, destinatário, data, local do Incoterm, condições, origem, classificação por item e representante. Dados ausentes exigem preenchimento e conferência. Condições aprovadas de cotação permanecem protegidas.

Salve o rascunho e confira o PDF. DRAFT identifica cada página. Depois de salvar todas as mudanças, informe motivo, confirme a conferência e aprove internamente.

O aprovado fica imutável. Correção exige cancelamento com motivo e novo número. Cancelamento é terminal; PDFs já baixados não mudam retroativamente. A invoice é em USD, não é NF-e, não contém fornecedores/custos internos e não implica envio, assinatura ou aceite externo.

## 6. Packing List

Abra pelo pedido ou por Gestão → Packing Lists. Preencha emitente, endereços, responsável e grupos de volumes.

Cada grupo informa marcas distintas, embalagem, número de volumes, pesos líquido/bruto, cubagem opcional e distribuição dos itens. Pesos, cubagem e quantidades são TOTAIS DO GRUPO. Não multiplique novamente pelo número de volumes.

Exemplo de preenchimento: dez caixas com peso líquido total de 250 kg devem informar dez volumes e 250 kg de peso líquido no grupo.

Para aprovar, distribua exatamente a quantidade integral de cada item do pedido entre os grupos e confira os pesos físicos. Peso bruto não pode ser menor que líquido. Medidas ausentes continuam desconhecidas, não zero.

Salve, confira a prévia e aprove explicitamente com motivo. Documento aprovado é imutável; correção segue cancelamento e novo número. Packing List não traz preços, não baixa estoque e não cria outra conta.

## 7. Embarque

Confirme a venda e use Registrar embarque ou Gestão → Embarques. Preencha referência, origem/destino, modal, responsável ativo, transportadora, reserva, referências de transporte, datas e motivo.

Sequência: planejado → reservado → em trânsito → chegou ao destino → entregue.

O fluxo cobre o pedido completo. Registre datas reais apenas quando o fato ocorrer. Elas não podem ser futuras ou contrariar a cronologia. Datas reais registradas são preservadas; rota e modal ficam fixos após a saída.

Cancelar transporte antes da saída não cancela a venda nem o recebível. Devolução e embarque parcial exigem outro fluxo, ainda não incluído. Não tente reverter saída real para devolver estoque implicitamente.

Não há rastreamento automático, contratação de frete ou emissão de BL/AWB neste fluxo.

## 8. Financeiro e compras

Registre recebimento pela ação financeira correspondente ao recebível existente. Entrega física e pagamento são fatos independentes. Repetir o mesmo estado de pagamento preserva sua data original.

Compra operacional não cancelada gera conta a pagar na própria moeda. Pagamento antecipado não acrescenta estoque. Receber fisicamente só acrescenta estoque próprio quando esse modo está indicado, com produto/unidade compatíveis.

Após recebimento, não se apagam quantidades para simular devolução. Valores e vencimento de compra paga também têm restrições. Totais financeiros permanecem separados por moeda; o sistema não presume câmbio.

## 9. Operação do dia

Em Gestão → Operação do dia, aplique situação, país e período. O painel destaca recebimento vencido, previsão logística vencida, documentação a conferir, embarque ausente/cancelado e cadastro/vínculo a revisar.

Os cartões não são somáveis: o mesmo pedido pode ter várias pendências. Vencimento hoje não é atraso; o corte diário é America/Fortaleza. Use os links para abrir e conferir a operação antes de decidir.

Se a consulta exigir refinamento, reduza período ou filtros. Não interprete erro/carregamento como total zero. O painel não aprova, paga ou altera registros.

## 10. Histórico e conflitos

Cotações, invoices, packing lists e embarques oferecem histórico paginado de autor, instante, motivo e alterações. Carregue eventos antigos sob demanda. Atualizar histórico não desfaz operações.

Em conflito de versão, preserve o preenchimento e recarregue para conferir a versão atual antes de tentar de novo. Não repita decisões cegamente. Histórico de outro momento não deve ser misturado com a nova revisão.

Esse histórico não é backup nem auditoria inviolável de todos os módulos. Sua durabilidade depende do armazenamento real.

## 11. Roteiro de conferência

Após a liberação técnica, use contas autorizadas e dados próprios de homologação:

1. Conferir empresa, oferta e cálculo; preparar cotação sem criar venda implicitamente.
2. Aprovar internamente e gerar um único pedido em rascunho.
3. Confirmar e conferir um recebível, reserva somente quando aplicável.
4. Preparar, conferir e aprovar Invoice e Packing List.
5. Registrar os cinco estados logísticos com fatos e datas compatíveis.
6. Registrar recebimento financeiro e conferir ausência de conta/baixa duplicada.
7. Consultar histórico, recarregar telas e conferir Operação do dia.
8. Validar separadamente permissões, importação/deduplicação e relatórios por moeda.

Este roteiro está preparado; não foi executado na produção por esta atualização.

## 12. Situação de publicação

Consulta direta Railway em 20/10/2026: cinco serviços online, zero problemas reportados e zero falhas recentes na janela padrão. Isso comprova estado de infraestrutura, não funcionamento integral. O projeto não tem volumes ou buckets associados; o Mongo atual não deve ser reiniciado ou receber volume vazio antes de preservação e recuperação comprovadas.

A captura enviada pelo operador mostra copy_created=true, writes_unlocked=true e restoration_proven=false. Há indicação de cópia no servidor, mas não confirmação de download/hash local ou restauração real. Não publicar o arquivo do banco em GitHub ou anexá-lo a este manual.

Os testes anteriores estão registrados nos PRs 44–53; não foram reexecutados nesta atualização documental. Nenhum código de aplicação, dado comercial, implantação, credencial, volume, serviço pago ou backup recorrente foi alterado.

Fontes internas: STAGE2_OPERATIONS.md, FLUXOS_OPERACIONAIS.md, COMMERCIAL_QUOTATIONS.md, COMMERCIAL_INVOICES.md, PACKING_LISTS.md, ORDER_SHIPMENTS.md, OPERATIONS_DASHBOARD.md e OPERATION_HISTORY.md na revisão identificada no início. Situação técnica detalhada: STAGE2_RELEASE_STATUS_2026-10-20.md e STAGE1_PRODUCTION_DIAGNOSTIC_2026-10-20.md na branch de auditoria.
