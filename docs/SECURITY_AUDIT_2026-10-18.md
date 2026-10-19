# ExportHub / IBIAG — auditoria e execução de 18/10/2026

## Atualização em 19/10/2026 — importações, ingresso da API e auditoria offline

**Código validado deste marco:** PRs [35](https://github.com/reginoneveses-maker/IBIAG/pull/35) e [36](https://github.com/reginoneveses-maker/IBIAG/pull/36), integrados somente à branch de revisão do draft [28](https://github.com/reginoneveses-maker/IBIAG/pull/28). Head 93f32a854f5452f38a488e117fbba878dfb6f9b1. [Pipeline final 39267821670](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39267821670): sucesso completo, 278 testes backend + 40 subtestes (MongoDB descartável real), 266 testes frontend em 13 suítes, build e navegador. Main permanece c9e2b6508c3f791e0b7ec2ba9863a9a0bf5dae6a, sem deploy desta composição.

### PR 35 — CSV/XLSX com orçamento de recursos

Leitura comum nas três rotas existentes, sem duplicar importadores. CSV UTF-8/BOM e XLSX: até 10.000 linhas de dados, 128 colunas, 250.000 células e 8 Mi caracteres de texto, além dos limites de upload/ZIP anteriores. Preflight CSV respeita aspas/delimitadores antes do parser; XLSX verifica todos os XMLs, rejeita DTD/entidades, caminhos inseguros, coordenadas esparsas e excesso de estilos/shared strings antes de openpyxl. Workbook em read-only, cached values, sem links externos e fechado ao terminar. Dimensões falsas não permitem truncamento silencioso ou alocação descontrolada. Cabeçalhos normalizados duplicados são recusados. Mensagens 400/413 estáticas. Interface deixa de oferecer .xls, que já não tinha dependência de leitura instalada.

Foram adicionados 12 casos unitários e cinco cenários HTTP repetidos também com MongoDB real no CI: CSV/XLSX com 2.000 empresas, zeros iniciais, isolamento de proprietário/deduplicação, layout IBIAG na terceira linha, comissões e ausência de alteração/deleção quando uma importação é recusada. Pipeline individual 39265563142 e composição 39266184557 passaram: 265 backend/40 subtestes, 266 frontend, build/navegador. Local: 213 backend/40 subtestes passaram e 52 dependentes de ambiente foram ignorados; frontend/build passaram. Documentação: docs/TABULAR_IMPORT_SECURITY.md. Não é antivírus, isolamento de processo, limite global de CPU/concorrência ou validação completa de regras comerciais.

### PR 36 — tamanho efetivamente consumido pela API

Middleware ASGI aplica orçamento padrão de 2 MiB e envelopes explícitos para nove rotas de arquivo (64 MiB nos uploads comuns; 6 MiB para XML; 2/3 MiB para lotes específicos). Rejeita Content-Length inválido/duplicado e combinação ambígua com Transfer-Encoding. Conta os bytes efetivamente consumidos, mesmo sem tamanho declarado ou com tamanho subdeclarado; bloco excedente não é entregue ao parser. Integração com a exceção multipart fecha arquivos temporários parciais antes do retorno 413. Respostas de recusa mantêm headers privados e CORS de origem exata.

Treze novos testes verificam fronteiras, chunks, declaração falsa/ambígua, padrões de rotas, CORS, erros estáticos, resposta já iniciada e HTTP real com stream JSON/multipart e arquivo forçado a spool em disco. Pipeline individual 39267150006 passou; composição final acima também passou. Local: 226 backend/40 subtestes passaram, 52 casos de ambiente ignorados e executados no CI. Documentação: docs/REQUEST_BODY_LIMITS.md. Isso limita consumo dentro da aplicação, não o tráfego no socket/proxy, bodies ignorados, tempo de envio, concorrência global ou efeitos já executados. Proxy real continua sem comprovação.

### Auditoria de segredos — escopo e triagem

Scanner temporário detect-secrets 1.5.0, 27 plugins, sem validação de credenciais pela rede (--no-verify), sem chamadas a provedores. Varredura das referências Git disponíveis/fetched no início deste marco: 302 commits, 946 blobs únicos, 32.212.086 bytes. Foram examinados 860 blobs UTF-8 (14.706.474 bytes); 86 blobs binários ficaram fora, sem OCR/descompactação. Controle positivo sintético no mesmo diretório de varredura foi detectado como GitHub Token e alta entropia; seu valor foi criado offline, nunca utilizado e excluído dos resultados reais.

Resultado bruto: 928 candidatos em 68 versões de arquivos, correspondendo a 25 caminhos. Triagem por contexto: 842 hashes públicos de integridade SHA-512 do lockfile; 78 ocorrências de palavra-chave em fixtures/testes ou identificadores de campos da UI; sete URLs de autenticação sintéticas em testes de recusa; uma chave pública de ingestão de analytics no HTML. Não se identificou credencial privada de produção entre esses candidatos. Isso não prova ausência de segredos: permanecem filtros heurísticos padrão, binários, commits/refs não disponíveis, secrets do CI/hosting, logs, banco, storage e permissões reais fora do escopo. As exceções de allowlist/lockfile/swagger foram desabilitadas; nenhum valor de candidato foi publicado ou validado em provedor. A primeira execução apontou zero por contexto de diretório do CLI; esse resultado foi descartado e a análise acima usa nova execução calibrada. Não houve rotação de credenciais.

A chave pública sinalizou um problema diferente: o HTML inicial carregava scripts remotos de geração e analytics, com configuração de gravação de sessão. Não se comprovou coleta/vazamento. A remoção está isolada no PR 37, ainda sujeita à pipeline antes de integrar.

### Pendências atuais da etapa 1

Recuperação de senha esquecida/emergência administrativa; avaliação e remoção de seeds/migrações destrutivos no startup (há exclusões de produtos/trade/leads condicionadas a marcadores legados); validação do peer real do proxy/allowlist/sanitização de cabeçalhos; privilégios efetivos de banco/storage e auditoria operacional de segredos; ownership/duplicidades/órfãos legados; conteúdo/malware e limites globais de uploads/concorrência; política publicada de chaves/origens; liberação controlada e fluxos reais. Main ainda publica automaticamente sem aguardar a pipeline. A etapa 1 segue aberta. Nenhuma conta real, variável de hosting, serviço pago, chamada de provedor, backup de produção ou deploy foi executado.

Os resumos anteriores abaixo são históricos; esta atualização substitui suas contagens e pendências quando divergirem.



Resultado mais recente: PR 34 integrado somente à revisão draft 28. A composição b4cfca8 passou integralmente na pipeline [39137199614](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39137199614): 243 testes backend, 40 subtestes, 266 testes frontend, build e navegador. A etapa 1 permanece aberta e não houve publicação de aplicação em produção.

Marco anterior: os PRs 32/33 foram integrados somente na revisão draft 28. A composição a20892a passou integralmente na pipeline [39135986654](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39135986654): 236 testes backend, 40 subtestes, 266 testes frontend, build e navegador. Não houve publicação de aplicação ou alteração de conta em produção. A etapa 1 continua aberta.

A etapa 1 (Segurança e Controle de Acesso) permanece aberta. Foram recuperadas
as conversas “Análise do ExportHub” e “Criar plataforma ExportHub”, confrontadas
com o código, PRs, GitHub Actions e configuração de hospedagem disponível.
Relatos anteriores não foram tratados como comprovação de produção.

Marco anterior: a integração 9e25b65 passou na pipeline [39119193582](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39119193582): 206 testes backend, 40 subtestes, 257 testes frontend, build e navegador. PRs 29–31 integrados somente na revisão draft 28. Etapa 1 aberta; nada publicado em produção.

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
4. Concluir recuperação de senha esquecida e emergência administrativa, revisão de bootstrap/startup,
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

Inventário estático após os PRs 32/33: 115 rotas; 47 dependem diretamente de admin e 64 de usuário autenticado (algumas destas também exigem admin no corpo). Restam quatro sem dependência explícita: login, cadastro público desligado por padrão, health e raiz. Isso é inventário, não comprovação dinâmica de cada caminho.

Pendências técnicas identificadas: limites de ingresso e de recursos dos parsers/importadores; política de conteúdo/malware; ciclo de vida e recuperação de senha esquecida e emergência administrativa; revisão dedicada de segredos e privilégios de banco/storage. O proxy real ainda não tem allowlist comprovada: não foi habilitada confiança em X-Forwarded-For/X-Real-IP. Também faltam publicação controlada, revisão das contas/legados e testes autorizados no ambiente publicado.

Nenhuma alteração de aplicação foi enviada a main nesta continuação. Não houve ativação de pesquisas pagas, novos serviços, backups de produção ou consulta a valores secretos. Não se declara a etapa 1 concluída.

O PR 31 corrige uma falha 500 reproduzida pesquisando `[`: filtros passam a usar texto literal, com limites e rejeição de NUL antes do MongoDB. Os três testes HTTP são repetidos com MongoDB descartável em CI. Validação local da composição atual: 174 testes e 40 subtestes passaram; 32 ignorados por falta de MongoDB/recursos externos locais. A pipeline 39118957767 do head final 8f43fd4 passou: 206 testes backend e 40 subtestes, 257 testes frontend, build e navegador. Integrado somente na branch de revisão por 1297480. O resumo backend de CI não contém testes ignorados; a validação local mantém os 32 skips por ambiente. A pipeline 39119193582 da integração final 9e25b65 também passou integralmente, após a atualização de documentação.

Roteiro detalhado de liberação: [SECURITY_RELEASE_VALIDATION.md](SECURITY_RELEASE_VALIDATION.md). Inclui o comportamento já existente de sincronizar senha administrativa e executar seeds/migrações no startup; esses efeitos precisam revisão antes de reiniciar a instalação existente.

Estado deste marco: PRs 29, 30 e 31 integrados somente no PR draft 28; main permanece sem essas alterações de aplicação. As pipelines individuais/composição de código passaram. A pipeline final 39119193582, no SHA 9e25b65, passou integralmente. Nenhuma validação publicada foi realizada, e não há declaração de conclusão integral da etapa 1.

## Continuação — suspensão, troca de senha e bootstrap

- PR 32: painel administrativo de suspensão/reativação de contas comuns, validação de estado/geração em cada requisição e bloqueio de novos logins. Tokens anteriores, inclusive legados, não voltam a funcionar após reativar. Atribuições novas a contas suspensas são recusadas; dados existentes não são apagados. Não permite suspender administradores por esta API. Pipeline 39135033549 passou com 220 testes backend, 40 subtestes, 261 testes frontend, build e navegador. Integrado somente na revisão por b4c7fa4, cuja pipeline 39135326370 também passou.
- PR 33: troca autenticada de senha com confirmação da credencial atual, limite compartilhado de cinco tentativas por janela de 15 minutos, gravação com comparação de hash/geração e revogação das sessões. Tela limpa campos e exige novo login. O bootstrap deixa de restaurar ADMIN_PASSWORD sobre conta já existente e usa criação atômica com índice único. Não promove uma conta comum existente. Pipeline 39135666895 passou: 236 testes backend, 40 subtestes, 266 testes frontend em 13 suítes, build e navegador. Integrado somente na revisão por a20892a.

Validação local deste marco: 189 testes backend e 40 subtestes passaram; 47 casos dependentes de MongoDB/ambiente foram ignorados localmente e executados no CI. O navegador usa contas sintéticas para suspender, negar login/replay, reativar, exigir novo login, trocar senha de admin e rejeitar token/senha antigos. Não foram usados dados de produção.

Páginas do candidato: /gestao/acessos (somente admin) e /prospects/senha (conta ativa). São código na revisão; não foram publicadas. Documentação: docs/ACCOUNT_SUSPENSION.md e docs/PASSWORD_CHANGE.md.

A suspensão não cancela requisições já autorizadas, jobs antigos ou arquivos já obtidos. A troca autenticada não é recuperação de senha esquecida. Recuperação de conta e emergência administrativa ainda precisam de fluxo próprio. Mudar ADMIN_PASSWORD deixa de redefinir contas existentes quando o novo código for publicado; nenhum segredo foi rotacionado nesta execução. Os demais seeds/migrações de negócio ainda exigem revisão antes do deploy.

Permanecem abertos: proxy real e configuração publicada, recuperação de acesso, limites de ingresso/recursos de parser e conteúdo dos uploads, auditoria dedicada de segredos/privilégios de banco/storage, contas e dados legados e validação dos fluxos publicados. Main não recebeu estas alterações de aplicação; nenhum serviço pago, mensagem, consulta externa, backup ou conta real foi ativado/alterado nesta continuação.

Pipeline final da composição: 39135986654, SHA a20892a, sucesso completo após integrar os PRs 32/33. O relatório foi atualizado em branch de auditoria, sem alterar a árvore de código já testada nem main.

## Continuação — XML de NF-e com limites próprios

O PR 34 substitui decoding que descartava bytes e substituição de namespace por parsing incremental explícito com defusedxml 0.7.1. DTD, entidades e referências externas são proibidas. Há limite de 5 MiB antes do parser, 64 níveis e 50 mil elementos. Excesso retorna 413; XML inválido/proibido, estrutura não reconhecida ou total inválido/não finito/negativo retorna mensagem estática 400, sem exceção interna. Namespaces, prefixos e encoding declarado são preservados na extração. A rota continua administrativa e não persiste documento/nota/arquivo.

Sete testes novos verificam entrada/saída válidas, prefixo e ISO-8859-1, DTD/entidades locais/remotas sem fetch, tamanho/profundidade/nós, erros redigidos, valores monetários e autorização/ausência de gravações. Validação local conjunta: 196 testes e 40 subtestes passaram; 47 casos de ambiente/MongoDB foram ignorados localmente. Pipeline individual 39136973269 passou integralmente: 243 testes backend, 40 subtestes, 266 testes frontend, build e navegador, incluindo os casos anteriores com MongoDB descartável.

O PR 34 foi integrado somente à revisão draft 28 por b4cfca8. Não houve publicação da aplicação em main nem acesso a XMLs de produção. Documentação e referência oficial da dependência fixada: docs/NFE_XML_SECURITY.md. A correção não comprova validade fiscal, assinatura digital ou conformidade completa de schema, não é antivírus e não limita o ingresso multipart/proxy. Recursos de CSV/XLSX e proteção dos demais uploads permanecem pendentes, junto com recuperação de acesso, privilégios/segredos, dados legados e validação publicada do proxy/fluxos. Nenhum serviço pago, consulta de provedor ou backup foi ativado.

Pipeline final da composição b4cfca8: 39137199614, sucesso completo. A árvore integrada foi comparada com a árvore local testada, sem diferenças. Um teste local adicional de compatibilidade confirmou a leitura de XLSX sintético com a nova dependência; isso não comprova proteção integral de planilhas. Nenhum serviço externo pago, backup ou conta real foi ativado/alterado.
