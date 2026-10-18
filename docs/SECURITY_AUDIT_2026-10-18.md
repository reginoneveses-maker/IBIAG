# ExportHub / IBIAG — auditoria e execução de 18/10/2026

A etapa 1 (Segurança e Controle de Acesso) permanece aberta. Foram recuperadas
as conversas “Análise do ExportHub” e “Criar plataforma ExportHub”, confrontadas
com o código, PRs, GitHub Actions e configuração de hospedagem disponível.
Relatos anteriores não foram tratados como comprovação de produção.

## Ordem preservada

1. Segurança e controle de acesso.
2. Operação única e integração dos módulos.
3. Calculadora e lucro real.
4. Automações.
5. Dashboard.
6. Integrações externas.

CRM, Trade Intelligence, catálogo, fornecedores, documentos, cotações, preços,
pedidos, compras, estoque, financeiro e contratos já possuem código. Isso não
comprova que todos os fluxos estejam operacionais em produção. As etapas 2–6
não foram declaradas concluídas nem liberadas nesta execução.

## Alterações e evidências

| PR | Conteúdo | Testes / estado |
|---|---|---|
| [16](https://github.com/reginoneveses-maker/IBIAG/pull/16) | Cabeçalhos no Nginx | Integração anterior confirmada; headers HTTPS efetivos ainda exigem validação |
| [17](https://github.com/reginoneveses-maker/IBIAG/pull/17) | Revogação e TTL de sessões | Integração anterior confirmada; fluxo do navegador complementado no PR 20 |
| [18](https://github.com/reginoneveses-maker/IBIAG/pull/18) | Limite por conta | Integração anterior confirmada; concorrência com MongoDB coberta no PR 19 |
| [19](https://github.com/reginoneveses-maker/IBIAG/pull/19) | Limite por IP e proxy com confiança explícita | Head `9580a31`, pipeline [39114796392](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39114796392) passou; não integrado; proxy real pendente |
| [20](https://github.com/reginoneveses-maker/IBIAG/pull/20) | JWT exclusivo por sessão e logout com revogação | Head `3827ba8`, pipeline [39114604630](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39114604630) passou; não integrado |
| [21](https://github.com/reginoneveses-maker/IBIAG/pull/21) | Respostas genéricas para falhas 5xx | Head `7dd89ab`, pipeline [39114734866](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39114734866) passou; não integrado |
| [22](https://github.com/reginoneveses-maker/IBIAG/pull/22) | Pausa do agendamento de backup | Pipeline [39114769129](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39114769129) passou; integrado em `c9e2b65` |
| [23](https://github.com/reginoneveses-maker/IBIAG/pull/23) | Limites nas importações de CRM, portfólio e XML | Head `fd17107`; pipeline [39114930649](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39114930649) passou; não integrado |
| [24](https://github.com/reginoneveses-maker/IBIAG/pull/24) | Isolamento de tarefas, atribuição administrativa e interface | Head `22a5765`; pipeline [39115505754](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39115505754) passou; não integrado |
| [25](https://github.com/reginoneveses-maker/IBIAG/pull/25) | Validação de senhas, respostas de autenticação sem entrada confidencial e correção do cadastro | Head `4d438f0`; pipeline [39115756310](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39115756310) passou; não integrado |

As alterações de aplicação continuam em PRs porque a hospedagem acompanha
`main` e o backend informa `checkSuites=false`. Integrar código pode publicar
automaticamente antes da validação operacional. O PR 22 altera somente workflow
e documentação, fora dos caminhos observados de deploy dos aplicativos.

## O que foi corrigido

- `backend/serve.py`, `backend/Dockerfile`: nenhuma confiança em cabeçalhos
  encaminhados por padrão. `TRUSTED_PROXY_IPS` aceita apenas IPs exatos
  verificados; rejeita `*`, CIDRs, nomes e entradas vazias. Testes exercitam o
  middleware real do Uvicorn fixado no projeto. O checklist está no PR 19 em
  `docs/PROXY_SECURITY.md`. Não foi inventado um IP para o proxy de produção.
- `backend/test_login_mongo.py`: concorrência entre contas e entre IPs contra
  MongoDB local descartável do CI. O job backend do head atual do PR 19 passou
  com 120 testes e 28 subtestes. Nenhuma credencial de produção foi usada.
- `backend/server.py`, `frontend/src/AuthContext.jsx`: identificador aleatório
  por JWT evita que logins no mesmo segundo compartilhem token. “Sair” chama
  `/api/auth/logout` com a sessão capturada e limpa o navegador imediatamente.
  Uma resposta atrasada de `/auth/me` não restaura a sessão encerrada. Se a
  rede falhar, a revogação remota permanece não confirmada; o token ainda pode
  ser válido até expirar. A interface ainda não apresenta esse retorno ao usuário.
- `backend/safe_errors.py`: erros HTTP 5xx e falhas inesperadas retornam mensagem
  genérica e identificador de incidente, sem detalhes/cabeçalhos do provedor.
  Erros 4xx e `Retry-After` preservam o contrato. Não se afirma cobertura de
  todos os logs da hospedagem, mensagens 4xx e erros de tarefas em segundo plano.
- `backend/upload_limits.py`: leitura máxima de 50 MiB + 1 byte antes de parsers
  de importação; arquivos vazios/acima do limite são rejeitados. ZIPs de
  planilhas têm limite de 100 MiB expandidos e 2.000 entradas. Testes HTTP
  confirmam rejeição antes de pandas ou gravação nos quatro endpoints.
- `.github/workflows/backup.yml`: cron removido da branch padrão. Execução
  manual exige `authorized=true`, cujo padrão é falso. A execução agendada
  [39094697919](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39094697919)
  havia falhado em 18/10. Não foi executado backup de produção nem apagada qualquer cópia existente.

## Verificação conjunta local

Foi montada uma branch local de revisão contendo PRs 19–25; um conflito de
imports foi resolvido preservando os dois módulos. Isso é integração de testes,
não integração na branch de produção.

- Backend: **137 testes passaram, 32 subtestes passaram, 15 ignorados**.
- Frontend: **252 testes passaram, 9 suítes**.
- Build de produção do frontend: passou.
- `git diff --check`: passou.
- O teste local de navegador da branch conjunta não chegou a executar: o Chromium não estava instalado e o download retornou arquivo incompleto. As pipelines individuais dos PRs 24 e 25 passaram no teste de navegador do CI; isso não equivale a um E2E da branch conjunta nem a validação de produção.
- Os testes ignorados localmente dependem de recursos externos/ambiente. A
  validação de MongoDB no CI é evidência separada, não teste de produção.
- Varredura por padrões em **845 blobs históricos**: nenhum padrão de chave
  privada, token clássico GitHub, access key AWS ou chave literal Firecrawl foi
  encontrado. Nenhum arquivo `.env` apareceu na busca de caminhos históricos.
  Essa varredura limitada não comprova ausência de todo tipo de segredo.

## Matriz dos 21 controles solicitados

| Controle | Evidência / limite atual |
|---|---|
| 1. API keys protegidas | Backend lê variáveis; nenhum valor foi consultado ou exposto nesta execução. Escopos e rotação ainda precisam de auditoria |
| 2. `.env` não exposto | Ignorado no Git e não encontrado na busca histórica de caminhos; configuração HTTP real não foi testada |
| 3. Senhas fora do código | Admin vem do ambiente; varredura limitada não substitui scanner completo de segredos |
| 4. Login real | bcrypt/JWT, testes HTTP de login/logout e replay; PR 25 rejeita truncamento, aplica mínimo no cadastro e corrige resposta de criação; força, expiração e recuperação ainda precisam revisão |
| 5. Permissão no servidor | Há `Depends(get_current_user)` e `require_admin`; negação para não-admin comprovada em rotas de usuários; PR 29 aplica admin em 46 rotas sensíveis; contas comuns mantêm CRM/tarefas próprios e catálogo compartilhado somente leitura; não é tenancy por empresa |
| 6. Não confiar no ID da tela | PRs 24/26 validam proprietário e relações de tarefas/CRM/anexos no servidor, inclusive IDs indiretos; PR 29 restringe o ERP a admin |
| 7. Cada um vê o autorizado | PRs 24/26 isolam tarefas e CRM/anexos; PR 29 protege finanças/ERP e documentos sensíveis. Legados ficam administrativos até atribuição explícita. Não existe tenancy entre empresas |
| 8. Banco protegido | MongoDB consultado não possui proxy TCP público; autenticação, privilégios, criptografia e regras de rede não foram comprovados |
| 9. Storage/Firebase/Supabase | Código usa GridFS/S3. Não foi identificada integração Firebase/Supabase nesta revisão; IAM/bucket privado exigem validação do provedor efetivo |
| 10. Admin protegido | Administração de usuários exige admin; testes HTTP negam elevação por usuário comum; auditar todas as ações privilegiadas |
| 11. Debug desligado | PR 30 fixa debug falso e desabilita docs/OpenAPI por padrão; verificar stack publicado |
| 12. Erros sem detalhe | PRs 21/30 protegem falhas 5xx, a fronteira ASGI e interrupções de stream; logs do Uvicorn sem URLs; revisão integral de validação/jobs permanece pendente |
| 13. Validação no servidor | Pydantic e validações de negócio existentes; limites/campos e payloads livres ainda não integralmente auditados |
| 14. Sanitização | Validações de URLs/pastas e links HTTP(S) existem; revisão completa de saídas, HTML e campos livres pendente |
| 15. Upload protegido | PR 23 limita importações e ZIP expandido; PR 30 força downloads inertes/attachment. Faltam política integral de conteúdo/malware, limites de ingresso/disco e recursos do parser |
| 16. Injeção SQL/NoSQL | Persistência principal é MongoDB; PR 31 escapa a regex da pesquisa Trade e limita filtros; isso não comprova todos os operadores, campos e caminhos |
| 17. Limite de tentativas | Por conta integrado; por IP e concorrência com MongoDB comprovados em CI no PR 19; proxy publicado continua pendente |
| 18. Git sem segredo | Varredura histórica limitada sem achados; ainda falta auditoria dedicada de todos os formatos e histórico |
| 19. Headers e CORS | PR 30 exige origens HTTPS exatas, headers API/no-store e downloads inertes; headers/TLS e origens efetivas precisam validação publicada |
| 20. Testar como estranho | Negação anônima em seis rotas e negação de admin testadas via HTTP; isolamento entre contas reais de produção pendente |
| 21. Auditoria completa | Esta é revisão técnica com testes e inventário de pendências; auditoria integral de produção ainda não concluída |

## Bloqueios para concluir a etapa 1

1. Revisar a matriz admin/user com a operação e planejar a atribuição de legados,
   IDs duplicados e relações órfãs sem modificar dados automaticamente. Os testes
   de isolamento entre contas do CRM/tarefas e bloqueio do ERP foram implementados.
   Tenancy entre empresas e funções granulares não fazem parte da política atual.
2. Confirmar topologia/IPs do proxy, sanitização de X-Forwarded-For e comando
   efetivo de inicialização antes de liberar o limitador individual em produção.
3. Estabelecer validação e publicação controlada: hoje commits em `main` podem
   disparar deploy sem aguardar checks. Nenhum deploy de aplicação foi solicitado
   nesta execução.
4. Concluir recuperação/desativação de contas, revisão de bootstrap/startup,
   limites de ingresso e parsers, conteúdo dos uploads e auditoria dedicada de
   segredos e permissões do banco/storage. CORS/headers já têm correções testadas,
   mas ainda precisam da configuração e verificação publicadas.
5. Validar os fluxos publicados com contas de teste autorizadas, incluindo
   acesso indevido por IDs, documentos privados e expiração/revogação de sessões.

Foi feita apenas consulta de configuração no Railway, sem ler valores de
variáveis, alterar infraestrutura, ativar serviços pagos, chamar Firecrawl ou
disparar backup de produção. Serviços já existentes continuam no estado
observado; não se afirma que seus custos correntes estejam zerados.

## Continuação: tarefas e senhas

O PR 24 protege listagem, conclusão e exclusão na consulta ao banco. IDs,
proprietário e criação vêm do servidor. Tarefas antigas não foram apagadas nem
atribuídas arbitrariamente: ficam com acesso administrativo até atribuição
explícita. O painel administrativo agora permite selecionar o responsável.
A transferência valida o usuário de destino e registra o último ator/data; não
é um histórico integral. No CI, 123 testes e 23 subtestes passaram, incluindo
os oito casos HTTP repetidos contra MongoDB descartável e conclusão concorrente.

O PR 25 corrige um truncamento reproduzido no bcrypt fixado no projeto:
entradas diferentes após 72 bytes eram aceitas como iguais. A API e os helpers
rejeitam entradas maiores, vazias ou com NUL, preservando espaços e Unicode.
Novos cadastros exigem no mínimo 8 caracteres; login legado de senha curta é
preservado. Respostas 422 de autenticação não repetem a entrada do usuário.
O teste de cadastro expôs também um `_id` interno que causava erro de
serialização após a gravação; ele foi removido da resposta, junto com o hash.
O job backend do CI passou com 114 testes e 27 subtestes.

Senhas antigas originalmente maiores que 72 bytes precisam de redefinição
controlada; não houve migração ou consulta aos valores de produção. A política
do segredo de bootstrap deve ser verificada antes da publicação.

Documentação de cada PR: `docs/TASK_ACCESS_CONTROL.md` e
`docs/PASSWORD_INPUT_SECURITY.md`. Ambas as mudanças permanecem fora da
produção. Não foram ativados serviços pagos ou backups de produção nesta
continuação. A etapa 1 permanece aberta.


## Continuação: CRM, custos, ERP e respostas da API

- PR 26: CRM por proprietário, incluindo pesquisa/importação, histórico, métricas e anexos por caminhos indiretos; 14 casos HTTP repetidos com MongoDB real no CI. Pipeline 39116902534 passou.
- PR 27: descoberta/enriquecimento externo desligados por padrão. Guardas impedem pesquisas e retries; salvar no CRM continua disponível sem chamada externa. Pipeline 39117253215 passou.
- PR 28: composição dos controles para revisão, mantida em draft e fora de main. A primeira pipeline conjunta 39117499834 passou com MongoDB e navegador.
- PR 29: 46 rotas administrativas, dashboard sem consulta/exposição de finanças ao usuário comum, documentos financeiros/societários e aliases protegidos; frontend impede montar páginas restritas. Pipeline 39118021039 passou. Integrado somente na branch de revisão por c45149b, sem deploy.
- PR 30: CORS exato, chave JWT mínima de 32 caracteres, docs/debug fechados por padrão, cabeçalhos/no-store, erros redigidos até na fronteira ASGI e downloads como anexos inertes. Não há rotação de chaves automática. Validação local: 171 testes backend e 40 subtestes passaram, 29 testes externos ignorados; 257 testes frontend em 11 suítes passaram. Pipeline 39118591560 passou: 200 testes backend e 40 subtestes, 257 testes frontend, build e navegador. Integrado somente na branch de revisão por 5f5570d.

Inventário estático atual: 113 rotas; 46 dependem diretamente de admin e 63 de usuário autenticado (algumas destas também exigem admin no corpo). Restam quatro sem dependência explícita: login, cadastro público desligado por padrão, health e raiz. Isso é inventário, não comprovação dinâmica de cada caminho.

Pendências técnicas identificadas: limites de ingresso e de recursos dos parsers/importadores; política de conteúdo/malware; ciclo de vida e recuperação/desativação de contas; revisão dedicada de segredos e privilégios de banco/storage. O proxy real ainda não tem allowlist comprovada: não foi habilitada confiança em X-Forwarded-For/X-Real-IP. Também faltam publicação controlada, revisão das contas/legados e testes autorizados no ambiente publicado.

Nenhuma alteração de aplicação foi enviada a main nesta continuação. Não houve ativação de pesquisas pagas, novos serviços, backups de produção ou consulta a valores secretos. Não se declara a etapa 1 concluída.

O PR 31 corrige uma falha 500 reproduzida pesquisando `[`: filtros passam a usar texto literal, com limites e rejeição de NUL antes do MongoDB. Os três testes HTTP são repetidos com MongoDB descartável em CI. Validação local da composição atual: 174 testes e 40 subtestes passaram; 32 ignorados por falta de MongoDB/recursos externos locais. A pipeline 39118957767 do head final 8f43fd4 passou: 206 testes backend e 40 subtestes, 257 testes frontend, build e navegador. Integrado somente na branch de revisão por 1297480. O resumo backend de CI não contém testes ignorados; a validação local mantém os 32 skips por ambiente. A atualização posterior de documentação na integração tem sua própria pipeline, a conferir antes de publicar.

Roteiro detalhado de liberação: [SECURITY_RELEASE_VALIDATION.md](SECURITY_RELEASE_VALIDATION.md). Inclui o comportamento já existente de sincronizar senha administrativa e executar seeds/migrações no startup; esses efeitos precisam revisão antes de reiniciar a instalação existente.

Estado deste marco: PRs 29, 30 e 31 integrados somente no PR draft 28; main permanece sem essas alterações de aplicação. As pipelines individuais/composição de código passaram. A pipeline de integração no SHA posterior à atualização da documentação ainda deve ser acompanhada. Nenhuma validação publicada foi realizada, e não há declaração de conclusão integral da etapa 1.
