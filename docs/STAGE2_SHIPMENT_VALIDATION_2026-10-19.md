# Validação da etapa 2: embarque completo manual — 19/10/2026

## Resultado e limites

PR46 em rascunho, empilhado sobre PR45, que depende de PR44 e do candidato de segurança PR28. Não integrado à main, não publicado e não homologado em produção. O projeto completo não está concluído.

Código da entrega:887ed1eb95bc99770af386074fb0e6daa8f8dbca. Árvore:d1b6fed8a68d3b4e3055eb179ff407029cf0146d. A árvore local foi comparada à árvore remota e é idêntica. Não houve alteração em registros comerciais reais, credenciais, deploy, banco, armazenamento, rede, backups ou serviços pagos.

## Implementado

- Cadastro manual de um embarque completo a partir de pedido confirmado, com referência, responsável ativo, origem/destino, modal, transportadora, reservas/referências, datas previstas/reais e motivo.
- Planejado/reservado/trânsito/chegada/entrega/cancelamento de transporte, com transições e datas conferidas no servidor. Cancelamento de transporte mantém a venda; não reverte saída real.
- Histórico com autor/data/versão/alterações, limites de100 eventos e256KiB UTF-8 sem truncar registros anteriores. Datas reais e rota depois da saída preservadas.
- Gravação única no pedido dentro da trava/versionamento existente. Reuso do estoque e recebíveis derivados; nenhum segundo movimento/conta/coleção.
- Rotas administrativas, corpo estrito/limitado, proteção contra falsificação do histórico ou bypass pela atualização genérica de pedidos, listagem paginada com projeção de resumo e arquivos somente leitura.
- Tela em Gestão→Embarques e links nos pedidos; conflitos exigem nova conferência, sem repetição automática; respostas tardias descartadas.

## Revisão de segurança

A autenticação continua consultando o usuário atual; responsável indicado não recebe permissão de ERP. Papéis em cabeçalho não concedem acesso. Cliente não controla histórico, autoria, data de auditoria, versão nova ou campos comerciais pelo endpoint logístico. Falha antes da gravação deixa o pedido intacto e libera a trava. A comparação de versão protege gravações concorrentes. Limites de histórico rejeitam novas alterações sem apagamento. Texto é renderizado pelo React sem HTML interpretado. O histórico não é inviolável para administradores diretos do MongoDB.

Não há acesso externo, provedor de tracking, cobrança de frete, emissão de BL/AWB, assinatura, emissão fiscal, embarques parciais ou devolução implícita. O contrato está em docs/ORDER_SHIPMENTS.md.

## Evidência de testes

Local:293 testes de backend+48 subtestes passaram;103 casos de ambiente/MongoDB/Docker foram pulados localmente.287 testes de interface em16 suítes e compilação passaram. Treze novos cenários HTTP são repetidos com MongoDB descartável; seis testes de tela cobrem o fluxo e erros.

A primeira pipeline39336752524 aprovou396 testes de backend+56 subtestes,287 testes de interface e compilação, mas falhou no Chromium ao localizar o seletor de responsável. A correção adicionou nomes acessíveis explícitos aos seletores e opções com label; o teste usa o responsável sintético conhecido. A falha não foi ignorada nem removida do fluxo.

Pipeline final39337251888: SUCCESS no SHA887ed1eb95bc99770af386074fb0e6daa8f8dbca. Backend396 testes+56 subtestes passaram (MongoDB real descartável e regressão de contexto Docker; sem skips no resumo da suíte), frontend287 testes em16 suítes, compilação e fluxo Chromium completos. Jobs118349710996 (backend) e118349711175 (frontend), ambos success. O fluxo executou o mesmo pedido calculado até entrega, preservou cinco eventos/datas após recarga e verificou uma única conta a receber em cada situação. A mensagem final do script mantém o título antigo do fluxo de documentos; as novas etapas de embarque são asserções obrigatórias antes desse PASS. Provedores externos permanecem bloqueados/simulados. Isso não é validação do banco/contas publicados.

## Estado de integração

| Entrega | Desenvolvimento | Integração/main/produção |
| --- | --- | --- |
| Segurança PR28 | Candidato testado; diagnóstico operacional preparado | Pendente de validar instalação |
| CRM→pedido PR44 | Pipeline39330912506 aprovada | Não integrado/publicado |
| Cálculo salvo→rascunho PR45 | Pipeline39332768449 aprovada | Não integrado/publicado |
| Embarque manual PR46 | Evidência desta entrega | Não integrado/publicado |

O navegador percorre a calculadora/CRM e os cadastros existentes. Isso comprova o fluxo sintético do candidato; não importa nem certifica o acervo/banco de produção.

## O que falta para usar a nova versão

1. Executar diagnóstico readonly no backend existente por sessão autenticada de operador, conforme docs/STAGE1_OPERATOR_HANDOFF.md nesta branch de auditoria. O conector Railway atual não oferece shell; o conector Atlas conectado não alcançou o destino privado do Railway. Não é falta de uma autorização genérica do usuário e não deve ser contornado com serviço novo.
2. Confirmar banco efetivo/autenticação/privilégios, dbPath/montagem/persistência e storage privado. Os metadados do serviço MongoDB não mostravam volume anexado; não reiniciar, migrar ou anexar volume vazio sem entender os dados existentes.
3. Conferir os ingressos de backend, proxy/peer/forwarded headers, CORS/cabeçalhos/limites e configuração real. Não basta o status online.
4. Resolver os achados preservando dados, validar e integrar os candidatos em ordem, preparar retorno à versão anterior sem ativar backup não autorizado, publicar SHA aprovado e homologar com contas administrativas e comuns autorizadas.
5. Para concluir o escopo ampliado: cotação comercial formal/aprovação e vínculo à oportunidade, documentos operacionais vinculados/emissão de Invoice/Packing List com conferência, indicadores e testes de ponta a ponta. Embarques parciais/devoluções exigem desenho próprio. Serviços externos permanecem desligados até configuração/homologação e eventual autorização de custo.
6. A versão móvel/PWA é uma evolução posterior; não foi criada nem publicada nesta entrega.

O usuário já autorizou continuar o desenvolvimento. O acesso técnico necessário à produção continua sendo uma dependência separada, adiada anteriormente pelo usuário para o dia seguinte. Nenhuma senha, URI, token ou chave deve ser enviada em conversa.
