# Etapa2 — primeira entrega e validação

19/10/2026. Repositório reginoneveses-maker/IBIAG. Desenvolvimento autorizado enquanto a validação operacional da etapa1 aguarda acesso ao servidor existente. A etapa1 permanece aberta; a etapa2 inteira não está concluída.

## Implementado

Vínculo explícito CRM→pedido sobre os módulos existentes. Nome e país vêm do cadastro validado pelo servidor e ficam preservados como identidade histórica. Apenas rascunhos podem trocar/remover vínculo; pedidos manuais/legados continuam válidos. Omissão do campo em clientes antigos não apaga vínculo. Empresas referenciadas por pedidos, inclusive arquivados, não podem ser excluídas. Criação/exclusão concorrentes usam a trava existente, com autorização antes e dentro dela. Nenhum privilégio ERP foi concedido ao usuário comum.

Atalho na ficha CRM, seleção paginada, repetição após erro, respostas atrasadas descartadas e retorno à ficha pelo pedido. O parâmetro de criação é consumido antes de recarregar. Abrir formulário não salva nem confirma a operação; rascunho não gera recebível ou movimento de estoque.

## Comprovado

PR44: https://github.com/reginoneveses-maker/IBIAG/pull/44

SHA ff0ca9a5de5bafe4bec9c745ae45b585a4a43f02; árvore7d784019a78e3d8da5084285bc6db9a426977445. Árvore local e remota comparadas e idênticas.

Pipeline: https://github.com/reginoneveses-maker/IBIAG/actions/runs/39330912506 — concluída com sucesso.

| Validação | Resultado |
|---|---|
| Backend CI, job118328559088 |350 testes +40 subtestes aprovados; sem skips no resumo final |
| MongoDB |Dez novos cenários HTTP repetidos com banco local descartável, além da simulação; nenhum banco real da empresa usado |
| Frontend CI, job118328559394 |274 testes/15 suítes aprovados |
| Build |Compilação aprovada |
| Chromium |CRM→rascunho→recarga→CRM→documentos; um pedido e nenhum recebível pelo rascunho; percurso aprovado |
| Local |270 backend/40 subtestes e274 frontend aprovados;80 casos dependentes de ambiente não executados localmente, cobertos no CI |

Revisão de segurança: autenticação e administração no servidor; papel forjado recusado; IDs inexistentes/duplicados, operadores e NUL recusados; snapshot/versão preservados; exclusão concorrente sem órfão; usuário alheio recusado antes da trava compartilhada. Teste de navegador detectou reabertura indesejada do atalho na recarga, corrigida e revalidada. Testes de componentes também cobrem resposta tardia após abertura manual.

## Integração e pendências

Código persistido em operations/crm-order-link-20261019; PR44 draft contra o candidato de segurança006da6d para revisão e CI. Não foi integrado em main, no PR28 ou em produção. A pipeline comprova o ambiente controlado e não certifica fluxos publicados ou dados legados reais.

Próximas funcionalidades exigem entregas próprias: cotações ligadas ao processo, embarques manuais reais, documentos operacionais e gestão diária/indicadores. Ver docs/STAGE2_OPERATIONS.md na branch da funcionalidade. Antes de liberar, resolver etapa1: banco/persistência/storage/proxy, dois ingressos de backend e validação com contas autorizadas. Dados legados não foram migrados nem associados por nome.

Nenhum deploy, reinício, migração, registro/conta real, serviço pago, chamada paga de fornecedor, backup ou restauração de produção foi executado. Este relatório é armazenado fora da branch de aplicação para não alterar a árvore que acabou de passar no CI.
