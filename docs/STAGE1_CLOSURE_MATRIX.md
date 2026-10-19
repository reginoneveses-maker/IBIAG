# Matriz de encerramento da etapa 1

Data: 19/10/2026. Escopo: os 21 requisitos de segurança solicitados para o ExportHub/IBIAG. O estado de código/testes refere-se ao candidato do PR draft 28 e aos PRs de continuação, não à versão publicada. A auditoria principal e o roteiro de liberação registram SHA/pipelines e pendências mais recentes. Nenhum item é declaração de segurança absoluta.

| # | Requisito | Evidência de código/testes | Comprovação operacional ainda necessária |
|---|---|---|---|
| 1 | Chave de API protegida | Chaves no backend; descoberta paga bloqueada por padrão; nenhum fornecedor pago acionado nos testes | Política/escopo/rotação dos segredos efetivos da hospedagem |
| 2 | .env nunca exposto | Git ignora ambiente/credenciais; PR 41 acrescentou exclusão de contexto Docker e teste real de COPY; pipeline39303673532 aprovada | Imagens antigas/publicadas, configuração de runtime e artefatos fora do Git |
| 3 | Nada de senha no código | Hash bcrypt no banco, entradas limitadas, bootstrap create-only; fixtures sintéticas documentadas | Contas/segredos reais e acesso administrativo ao host |
| 4 | Login de verdade | JWT assinado, usuário/estado/geração consultados, testes HTTP/Mongo | Login autorizado na implantação com duas contas |
| 5 | Permissão no servidor | Dependências de autenticação/admin em ERP/finanças; testes de negação | Papéis reais e política de equipe aprovados |
| 6 | Não confiar no ID da tela | Ownership e vínculos/aliases de arquivo validados no backend | IDs/owners legados e fluxos publicados |
| 7 | Cada um vê o seu | CRM/tarefas por proprietário; materiais compartilhados têm política explícita; testes cruzados | Conferir o compartilhamento pretendido e os dados anteriores; sem tenancy multiempresa |
| 8 | Banco travado | Comando somente leitura verifica autenticação/privilégios quando executado no ambiente correto | Identificar banco real; comprovar autenticação, rede, privilégios e persistência; acesso de execução indisponível neste ambiente |
| 9 | Firebase/Supabase/storage | Esta implementação usa MongoDB e GridFS/S3; não cria Firebase/Supabase só para cumprir nomes | Storage efetivo privado/IAM e referências reais. Metadados não comprovam configuração nem exigem trocar provedor |
| 10 | Admin protegido | Papel/estado revistos no servidor; suspensão não desativa admin; recuperação operacional protegida no PR 39 | Segurança do host/operador, política de identidade/MFA e caso de recuperação autorizado |
| 11 | Debug desligado | Debug false; docs/openapi desabilitados por padrão | Confirmar flags e imagem publicadas |
| 12 | Erro sem detalhes | 5xx genérico/identificador redigido; erros de auth/CLI sem entradas/credenciais | Respostas e logs reais de todas as camadas |
| 13 | Validação no servidor | Modelos/regras de operações, senha/rotas/limites de importação com testes | Formatos de dados legados e fluxos reais; não equivale a prova de todo caminho possível |
| 14 | Tratar entrada do usuário | Valores tipados, consulta literal/escape, erros redigidos e parsers limitados | Política de conteúdo e revisão contínua dos formatos aceitos |
| 15 | Upload protegido | Limites de corpo/ZIP/XML/CSV/XLSX,30s idle/300s de corpo,16 APIs ativas/worker, autorização, download inerte e temporários fechados | Socket/buffering/capacidade real do proxy/servidor e política de malware/conteúdo |
| 16 | Sem injeção SQL | Backend usa MongoDB; query operators/regex de busca controlados; testes negativos | Revisão operacional das fontes/legados; não implica imunidade universal a injeção |
| 17 | Limite de tentativas | Quotas Mongo por conta/peer e reautenticação; testes concorrentes; proxy trust estrito | Peer real, allowlist verificada e cabeçalhos falsificados em ambiente publicado |
| 18 | Git sem senha vazada | Auditoria offline calibrada do histórico disponível; candidatos triados sem valores | Binários, refs indisponíveis, logs/secrets operacionais e rotação se incidente confirmado |
| 19 | Headers e CORS corretos | Origens HTTPS exatas, headers privados, downloads e frontend nginx testados | A sonda publicada /api/auth/me retornou401 sem nosniff/no-store; confirmar após liberação |
| 20 | Testar como estranho | Testes sem login, papel incorreto, ID alheio, replay, uploads malformados e navegador | Cenários reais autorizados, sem bloquear contas nem realizar carga/varredura em produção |
| 21 | Auditoria completa com IA | Revisão de fonte/testes/CI, histórico e ferramenta operacional somente leitura no PR 40 | Executar no banco/host real e resolver achados; auditoria independente não foi realizada |

## Critério para declarar encerramento

A pipeline inteira precisa passar no SHA candidato; os comandos e testes operacionais devem ser executados no alvo correto, com resultados e riscos registrados; achados de permissão, persistência, proxy, storage ou fluxo devem ser corrigidos e revalidados. A implantação deve ter controle de checks/rollback e não executar purgas/ações pagas/backups involuntários. Só então registrar o encerramento, identificando o que foi validado em produção.

Hoje o conector oferece metadados, com valuesRedacted=true, e nenhuma sessão de execução. O download do CLI oficial falhou no proxy. É necessário disponibilizar um caminho de execução administrativa no servidor existente, sem enviar senha/chave em chat nem expor o MongoDB publicamente. Isso é limitação concreta de acesso/verificação, não pedido de autorização para repetir tarefas rotineiras.

Serviços pagos, créditos, backups/restaurações e mudanças destrutivas seguem as restrições explícitas do usuário. A etapa 1 permanece aberta até haver comprovação operacional; testes locais/CI não são substitutos.

## Verificação do conector MongoDB — 19/10/2026

A conexão do plugin MongoDB Atlas foi confirmada nesta continuação. Consultas somente de metadados foram executadas: listagem geral retornou zero projetos e zero clusters; a consulta por organização retornou uma organização e um projeto. Ao listar clusters nesse projeto, a API retornou HTTP404, informando que o alvo não é um projeto Atlas e exige a API do Cloud Manager. Esse resultado não demonstra que o banco da IBIAG esteja vazio, ausente ou indisponível; também não identifica o destino MONGO_URL usado pelo backend.

Não foi obtido connectionId nem foram consultados registros, usuários de banco, credenciais ou configurações de rede. Nenhum projeto/cluster foi criado, migrado, atualizado ou reconfigurado. O conector está conectado, mas o acesso ao banco efetivamente usado pela aplicação permanece sem comprovação. Não se deve criar um cluster para contornar essa diferença: é necessário identificar o banco existente e disponibilizar leitura autorizada nesse alvo, ou executar o auditor pelo backend existente conforme STAGE1_OPERATOR_HANDOFF.md.

O PR28 permanece draft no SHA006da6db8953b18e249ad74b49dafcaa4e2e1e64; a pipeline39306286464 foi consultada novamente e permanece concluída com sucesso. Nenhuma alteração de aplicação ou implantação foi realizada nesta verificação. Os bloqueios operacionais de banco/persistência/storage/proxy/fluxos publicados continuam abertos; a indisponibilidade anterior do plugin não é mais o motivo.

## Banco privado do Railway — nova evidência operacional, 19/10/2026

Consultas somente leitura de status, DNS e fluxos do serviço ibiag-backend identificaram12 registros de resolução de mongodb.railway.internal, todos NOERROR. Na mesma amostra,69 fluxos de saída na porta27017 tinham destino correspondente aos endereços retornados pelo DNS. Os fluxos estão marcados partial e não identificam peerServiceId. A correlação é evidência de tráfego do backend para o nome privado MongoDB no Railway; não comprova autenticação, sucesso de consultas, nome do banco ou integridade dos registros, nem exclui outros destinos.

O serviço mongodb existente usa imagem mongo:8, está online com uma réplica e não apresenta volumes anexados, proxies TCP públicos nem nomes de variáveis no inventário. A ausência de volume anexado exige confirmar dbPath e montagem efetiva antes de qualquer reinício/redeploy/migração. Não é prova isolada de perda de dados nem autorização para anexar um volume vazio. Não foi realizada alteração de armazenamento.

Uma busca filtrada pelo aviso de controle de acesso retornou zero entradas: isso não confirma autenticação habilitada. Os logs de runtime recentes do backend incluem startup concluído; isso também não substitui os testes autenticados. O status da hospedagem mostra cinco serviços online e zero falhas recentes, mas não certifica as funções da aplicação. Há um patch staged com changes=[]; ele não foi aplicado.

Próximo passo concreto: sessão de execução autorizada no ibiag-backend existente, usando o roteiro STAGE1_OPERATOR_HANDOFF.md para executar o auditor já preparado. Em paralelo, leitura no container mongodb deve confirmar caminho/montagem e configuração efetiva de autenticação, sem reiniciar ou mover dados. Não abrir o banco publicamente nem criar cluster Atlas como alternativa ao diagnóstico. A conexão Atlas atual não forneceu acesso a esse destino privado.

Nenhum registro pessoal, URI, hash, senha ou resposta bruta de log foi publicado. Nenhum deploy, reinício, backup, migração, provisionamento pago ou alteração de rede foi executado. O SHA de aplicação006da6d permanece inalterado e aprovado no CI; a etapa1 continua pendente de evidência operacional.
