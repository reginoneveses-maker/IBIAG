# Revisão conjunta da etapa 1 — não publicar automaticamente

A composição do PR draft 28 reúne uma única vez os controles dos PRs 19, 20,
21, 23, 24, 25, 26 e 27 e recebeu, após pipelines completas, os PRs 29, 30 e 31.
O PR 22, que pausou backups automáticos, já estava na base main. Os PRs individuais
são o histórico de revisão; não reaplicar suas mudanças sobre esta composição.

## Controles e evidências

- Login por conta/IP e configuração explícita de proxies confiáveis.
- Sessões exclusivas/revogáveis, logout no navegador e validação de senhas.
- Erros genéricos, limites de importações e ZIP expandido.
- Tarefas e CRM por proprietário, com atribuição administrativa e anexos protegidos
  também por vínculos indiretos. Dados legados ficam administrativos até atribuição.
- Pesquisa externa desabilitada por padrão, preservando salvar no CRM sem provedor.
- 46 rotas administrativas para dados/alterações sensíveis de ERP e finanças;
  dashboard comum não consulta o financeiro e páginas restritas não são montadas.
- CORS exato, chave JWT mínima de 32 caracteres, docs/debug fechados por padrão,
  headers/no-store e downloads como anexos inertes. Sem rotação automática.
- Pesquisa Trade como texto literal limitado; operadores e NUL não viram regex livre.

A pipeline 39118957767 do head 8f43fd4 do PR 31 passou: 206 testes backend e 40
subtestes, 257 testes frontend em 11 suítes, build e fluxo no navegador. Inclui
MongoDB descartável; não houve testes ignorados no resumo do backend de CI.
Localmente, 174 testes e 40 subtestes passaram; 32 casos externos/MongoDB foram
ignorados. A mesma árvore de código foi integrada na branch de revisão por
1297480. Esta atualização posterior altera apenas esta documentação; a pipeline
do novo SHA de integração deve ser conferida separadamente antes de publicar.

## Bloqueios de liberação

1. Confirmar peer/topologia/IPs e sanitização dos cabeçalhos do proxy real antes
   de habilitar confiança. Sem isso, o limitador pode agrupar usuários pelo proxy.
2. Revisar contas admin/user e atribuição dos legados, IDs duplicados e órfãos.
   Esta política não implementa tenancy entre empresas nem funções granulares.
3. Concluir revisão de ciclo de vida/recuperação/desativação de contas, ingresso
   de uploads, recursos de parsers, conteúdo/malware e privilégios de banco/storage.
4. Verificar origens HTTPS e segredo JWT sem expor valores, além da sincronização
   de senha administrativa e seeds/migrações já existentes no startup.
5. Controlar a publicação: a hospedagem acompanha main sem esperar checks.
6. Comprovar os fluxos e permissões com contas autorizadas no ambiente publicado.

Roteiro detalhado e relatório atualizado estão na branch audit/security-status-20261018:
docs/SECURITY_RELEASE_VALIDATION.md e docs/SECURITY_AUDIT_2026-10-18.md.

Não foram alteradas variáveis da hospedagem, habilitadas pesquisas pagas, criados
serviços, executadas migrações nem disparados backups de produção nesta revisão.
A etapa 1 permanece aberta e esta composição continua em draft, fora de main.
