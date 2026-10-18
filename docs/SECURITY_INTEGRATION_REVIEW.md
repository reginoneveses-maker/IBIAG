# Revisão conjunta da etapa 1 — não publicar automaticamente

Esta composição reúne, uma única vez no código, as correções dos PRs 19, 20,
21, 23, 24, 25, 26 e 27. Os PRs individuais continuam disponíveis para revisão
de cada funcionalidade. A composição não encerra a etapa 1 nem substitui os
bloqueios de produção. O PR 22, que pausou os backups, já integra a base `main`.

## Escopo composto

- Login por conta/IP e configuração explícita de proxies confiáveis.
- Sessões exclusivas, revogação e logout do navegador.
- Respostas genéricas de erro e limites de importação.
- Validação de senhas e correção de serialização do cadastro.
- Tarefas por proprietário e atribuição administrativa.
- CRM por proprietário, incluindo importação, contatos, métricas e anexos.
- Pesquisa externa desabilitada por padrão, com CRM disponível sem enriquecimento.

Os conflitos de composição foram resolvidos preservando os imports e controles
de cada funcionalidade, inclusive validação do lead ao criar tarefa, propriedade
da tarefa e a política de pausa antes de qualquer consulta externa.

## Evidências locais desta composição

Backend: 157 testes e 32 subtestes passaram; 29 testes de recursos externos foram
ignorados localmente. Frontend: 255 testes em 10 suítes e build de produção passaram.
O navegador local não está disponível; a verificação de navegador e os testes
com MongoDB descartável devem passar nesta composição no GitHub Actions.
Todos os PRs individuais anteriores passaram em suas respectivas pipelines.

## Bloqueios de liberação

1. Confirmar o proxy real e seus IPs/cabeçalhos antes de habilitar confiança.
2. Planejar atribuição dos dados legados, conferir IDs duplicados e órfãos.
3. Concluir permissões dos demais dados operacionais/financeiros e a revisão
   de uploads, CORS/headers e privilégios efetivos de banco/storage.
4. Verificar a política do segredo administrativo sem exibir seu valor.
5. Controlar o deploy: a hospedagem ainda acompanha `main` sem esperar checks.
6. Validar as permissões e os fluxos com contas autorizadas no ambiente publicado.

Não ativar pesquisas pagas, serviços ou backups por integrar esta composição.
`ALLOW_PAID_DISCOVERY` permanece falso por padrão e não foi habilitado na hospedagem.
Nenhuma migração, consulta paga ou publicação de aplicação é realizada por esta revisão.
