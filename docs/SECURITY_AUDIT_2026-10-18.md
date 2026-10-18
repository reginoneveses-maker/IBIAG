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

Foi montada uma branch local de revisão contendo PRs 19–23; um conflito de
imports foi resolvido preservando os dois módulos. Isso é integração de testes,
não integração na branch de produção.

- Backend: **122 testes passaram, 28 subtestes passaram, 7 ignorados**.
- Frontend: **249 testes passaram, 8 suítes**.
- Build de produção do frontend: passou.
- `git diff --check`: passou.
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
| 4. Login real | bcrypt/JWT, teste HTTP de login/logout e replay; políticas de senha, expiração e recuperação ainda precisam revisão |
| 5. Permissão no servidor | Há `Depends(get_current_user)` e `require_admin`; negação para não-admin comprovada em rotas de usuários; matriz completa pendente |
| 6. Não confiar no ID da tela | Algumas rotas validam relações; vários CRUDs ainda usam o ID diretamente sem escopo por proprietário |
| 7. Cada um vê o autorizado | **Pendente crítico:** CRM/tarefas e dados operacionais são compartilhados; não há isolamento geral por usuário/workspace |
| 8. Banco protegido | MongoDB consultado não possui proxy TCP público; autenticação, privilégios, criptografia e regras de rede não foram comprovados |
| 9. Storage/Firebase/Supabase | Código usa GridFS/S3. Não foi identificada integração Firebase/Supabase nesta revisão; IAM/bucket privado exigem validação do provedor efetivo |
| 10. Admin protegido | Administração de usuários exige admin; testes HTTP negam elevação por usuário comum; auditar todas as ações privilegiadas |
| 11. Debug desligado | FastAPI usa padrão sem debug; documentação OpenAPI ainda acessível no código; verificar stack publicado |
| 12. Erros sem detalhe | PR 21 cobre falhas 5xx; mensagens de validação, tarefas assíncronas e logs externos ainda pendentes |
| 13. Validação no servidor | Pydantic e validações de negócio existentes; limites/campos e payloads livres ainda não integralmente auditados |
| 14. Sanitização | Validações de URLs/pastas e links HTTP(S) existem; revisão completa de saídas, HTML e campos livres pendente |
| 15. Upload protegido | Limites de documentos já existiam; PR 23 cobre importações antes sem limite; faltam política MIME/conteúdo, malware, limites de ingresso/disco e recursos do parser |
| 16. Injeção SQL/NoSQL | Persistência principal é MongoDB; ausência de SQL não comprova proteção contra operadores NoSQL e regex abusivas |
| 17. Limite de tentativas | Por conta integrado; por IP e concorrência com MongoDB comprovados em CI no PR 19; proxy publicado continua pendente |
| 18. Git sem segredo | Varredura histórica limitada sem achados; ainda falta auditoria dedicada de todos os formatos e histórico |
| 19. Headers e CORS | Nginx tem headers; CORS vem do ambiente; cabeçalhos do backend/TLS e origens efetivas não foram validados ao vivo |
| 20. Testar como estranho | Negação anônima em seis rotas e negação de admin testadas via HTTP; isolamento entre contas reais de produção pendente |
| 21. Auditoria completa | Esta é revisão técnica com testes e inventário de pendências; auditoria integral de produção ainda não concluída |

## Bloqueios para concluir a etapa 1

1. Definir e implementar escopo de acesso por workspace e funções em todos os
   módulos, com migração segura dos dados existentes e testes de duas contas.
   Não aplicar um filtro parcial que apenas esconda registros antigos.
2. Confirmar topologia/IPs do proxy, sanitização de X-Forwarded-For e comando
   efetivo de inicialização antes de liberar o limitador individual em produção.
3. Estabelecer validação e publicação controlada: hoje commits em `main` podem
   disparar deploy sem aguardar checks. Nenhum deploy de aplicação foi solicitado
   nesta execução.
4. Concluir política de senha, recuperação/desativação de contas, uploads,
   cabeçalhos/API, CORS e auditoria dedicada de segredos e permissões do banco.
5. Validar os fluxos publicados com contas de teste autorizadas, incluindo
   acesso indevido por IDs, documentos privados e expiração/revogação de sessões.

Foi feita apenas consulta de configuração no Railway, sem ler valores de
variáveis, alterar infraestrutura, ativar serviços pagos, chamar Firecrawl ou
disparar backup de produção. Serviços já existentes continuam no estado
observado; não se afirma que seus custos correntes estejam zerados.
