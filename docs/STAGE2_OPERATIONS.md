# Etapa 2 — operações integradas

Início: 19/10/2026, por autorização do usuário para adiantar desenvolvimento enquanto a etapa1 aguarda validação no Railway. Base de código: candidato de segurança006da6d. Nenhuma mudança desta etapa está liberada para produção. A etapa1 continua aberta; não há autorização para serviços pagos, créditos ou backups.

## Auditoria do que já existe

O repositório possui CRM e histórico, tarefas, fornecedores/produtos/ofertas, documentos/pastas/anexos, calculadora, pedidos, compras, estoque derivado e contas financeiras por moeda. As regras existentes estão em FLUXOS_OPERACIONAIS.md. Esses módulos não devem ser recriados.

O manual ExportHub_Manual_de_Uso.docx de07/10 descreve outro artefato publicado, com gravação local e embarques demonstrativos; não comprova o estado atual do repositório nem uma migração dos dados desse artefato. A continuidade desta etapa é no repositório reginoneveses-maker/IBIAG. Não houve leitura/importação de registros locais ou comerciais reais.

## Primeira entrega: empresa do CRM vinculada ao pedido

- Administrador abre a empresa no CRM e usa “Criar pedido para esta empresa”, ou seleciona “Empresa do CRM” no formulário existente de pedidos.
- Abrir o formulário não salva o pedido, confirma venda, altera etapa do CRM, movimenta estoque nem cria conta financeira.
- O pedido guarda lead_id, nome e país. O servidor valida a existência da empresa e obtém nome/país do cadastro ao criar ou trocar o vínculo; valores de identidade enviados pelo navegador não prevalecem.
- Alterar depois o CRM não reescreve a identidade histórica do pedido. Ao salvar novamente com o mesmo vínculo, o servidor preserva nome e país já registrados.
- Vínculo pode ser trocado/removido apenas se o estado armazenado do pedido for rascunho. Confirmados, embarcados, entregues e cancelados não podem trocar de empresa por este fluxo.
- Cliente manual continua disponível. Pedidos antigos sem lead_id continuam válidos; clientes antigos que omitem o campo ao atualizar não apagam um vínculo existente. Não há associação por semelhança de nome nem migração automática.
- Empresas vinculadas a qualquer pedido, inclusive arquivado/cancelado, não podem ser excluídas. A verificação e a gravação de pedidos compartilham a trava existente para evitar referência órfã por concorrência. A autorização de CRM é aplicada antes de adquirir a trava compartilhada e novamente dentro dela antes de informar conflito ao solicitante.
- A lista carrega empresas em páginas de250, oferece nova tentativa após erro e ignora respostas tardias ao trocar de fluxo/fechar formulário. O parâmetro do atalho é consumido ao abrir o formulário, evitando reabertura automática na recarga. Link no pedido retorna à ficha existente do CRM.
- Pedidos e seus valores continuam administrativos; não há concessão de acesso financeiro ao proprietário comum da empresa. Perfis por setor exigem desenho e validação próprios.

## Validação

backend/test_order_crm_link.py executa as rotas HTTP reais com base isolada: identidade canônica, listagem persistida, referências inválidas/operadores/NUL, permissões, preservação histórica/clientes antigos/versão, transições, cliente manual, exclusão protegida e concorrência. Os mesmos dez cenários são executados também com MongoDB local descartável quando TEST_MONGO_URL é fornecido; somente localhost/127.0.0.1/mongo são permitidos.

frontend/src/pages/Orders.test.jsx verifica seleção, atalho, paginação, falha/repetição, histórico e resposta tardia. PipelineOwnership.test.jsx verifica o atalho restrito ao admin. O fluxo Chromium existente percorre CRM→rascunho de pedido→recarregar→CRM→documentos e confirma um único pedido e nenhuma conta gerada pelo rascunho. Provedores externos continuam bloqueados/simulados no teste.

Resultados concretos da execução/CI serão registrados no PR desta entrega. Não confundir skips locais por falta de MongoDB/Docker com execução real desses casos; a validação publicada com contas autorizadas permanece pendente.

## Segunda entrega: cálculo salvo → pedido

O vínculo adicional reutiliza a calculadora e a tabela de preços existentes. A memória canônica é conferida e preservada no rascunho; mudança da revisão exige nova conferência. Não equivale a cotação comercial aprovada nem confirma venda. Ver SAVED_PRICE_ORDER_DRAFT.md. A etapa1 continua pendente; nenhuma entrega está publicada.

## Terceira entrega: embarque completo manual

Implementação vinculada ao pedido existente, com responsável, rota/modal, datas, estados e histórico limitado. Reutiliza a gravação e os saldos do ERP, sem ativar tracking ou outra cobrança. Ver ORDER_SHIPMENTS.md para contrato, limites e testes. Desenvolvimento não equivale à liberação em produção.

## Quarta entrega: cotação comercial com aprovação interna

Memória do cálculo, cliente do CRM e condições comerciais preservadas; aprovação explícita e conversão única em pedido em rascunho. Ver COMMERCIAL_QUOTATIONS.md. Envio, PDF e aceite do comprador não estão incluídos.

## Quinta entrega: Commercial Invoice vinculada ao pedido

Documento comercial em USD com memória explícita da venda, dados cadastrais conferidos, aprovação versionada e PDF privado com marca de rascunho/cancelamento. Sem copiar fornecedores ou custos internos; não cria outra conta ou NF-e. Ver COMMERCIAL_INVOICES.md para uso, contrato, testes e limites.

## Próximas entregas, uma de cada vez

1. Homologar o fluxo CRM/cálculo→cotação→pedido com condições comerciais e aprovação interna; desenhar envio e aceite do comprador separadamente. Cotações não criam pedidos/contas implicitamente.
2. Homologar o embarque completo manual vinculado ao pedido; desenhar embarques parciais/devoluções separadamente antes de qualquer ampliação. Sem ativar tracking pago.
3. Homologar a Commercial Invoice e implementar Packing List vinculada ao processo, com volumes, pesos, embalagem e conferência explícita; sem inferir dados ausentes.
4. Gestão diária e indicadores derivados dos registros, filtros, alertas internos e histórico permanente. Não apresentar exemplos ou inferências como operação concluída.
5. Validar fluxo integrado oportunidade→cotação→pedido→embarque→documentação→recebimento e importação/deduplicação/relatórios. Integrações externas somente depois da configuração e homologação autorizadas.

Dependências de liberação: resolver a etapa1, inclusive banco/persistência/storage/proxy, esclarecer os dois ingressos de backend, validar migração caso necessária e executar os fluxos com contas autorizadas. Não anexar volume vazio, reiniciar/migrar banco ou publicar código como atalho para obter uma validação verde.
