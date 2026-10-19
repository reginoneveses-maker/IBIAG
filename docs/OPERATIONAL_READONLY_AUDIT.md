# Auditoria operacional somente leitura

## Execução e saída

O comando deve ser executado no servidor correto com o ambiente já existente MONGO_URL/DB_NAME. No container: python security_readonly_audit.py. No checkout: python backend/security_readonly_audit.py. Não passar URI, senha ou chave como argumento. Não carrega .env, não importa a aplicação, não roda startup, não cria índices, não aplica migrações, não altera contas e não dispara backups ou chamadas a provedores.

A saída contém somente flags, nomes fixos de verificações e contagens. Não mostra documentos, IDs, nomes de usuários, banco, URI, endereços de proxy, origens CORS, senhas, hashes, objetos ou privilégios brutos. Ainda assim, contagens e resultados internos devem ser tratados em canal privado; publicar apenas conclusão redigida. Falhas de conexão/consulta não exibem exceções ou credenciais.

Exit 0 significa que as verificações automatizadas executadas passaram; **não significa liberação de produção**. Exit 1 indica achado ou verificação incompleta; exit 2 indica que o comando não concluiu. production_certified é sempre false: persistência, proxy real e fluxos publicados precisam de evidência independente. Não alterar a saída para fabricar aprovação.

## Cobertura

- connectionStatus com showPrivileges: confirma principal autenticado e disponibilidade dos privilégios efetivos, sem expor identidades. Direitos administrativos globais/fora do banco/configuração de usuários são sinalizados para revisão, sem tentar revogá-los. Ausência de dados de privilégio nunca passa como seguro. Não comprova sozinho que toda conexão anônima esteja bloqueada ou que não haja outro usuário privilegiado.
- Configuração: registro público/pesquisas pagas/docs desabilitados, formato mínimo da chave JWT, origens HTTPS e sintaxe estrita/ presença da configuração de proxy. Valores não são retornados. Sintaxe de IP correta não comprova confiança/sanitização do proxy real; formato mínimo da chave não comprova entropia ou segredo.
- Dados: IDs ausentes/duplicados em users/leads/tasks/documents; e-mail ausente/duplicado sem distinção de maiúsculas e papel desconhecido; responsáveis ausentes/órfãos de leads/tarefas; vínculos de lead órfãos em documents/tasks/interactions.
- GridFS: referências file_path de documents sem objeto correspondente em ibiag_files.files. Para S3, não acessa provedor nem presume privacidade. A cobertura de referências não abrange todos os caminhos/coleções, aliases, dados binários ou tipos legados; a lista de owners inexistentes não autoriza transferência automática.

Queries usam pipeline fixa sem $out/$merge, máximo de cinco segundos por consulta de contagem/agregação e allowDiskUse=false. O cliente limita pool a duas conexões e timeouts de conexão/resposta. Agregações/lookup ainda consomem CPU/leitura e não são snapshot transacional: executar em período adequado e repetir achados após controlar escritores. Falha/timeout resulta em verificação incompleta; não aumentar custos, permissões ou limites automaticamente para fazê-la passar. Um achado em duas contagens pode corresponder ao mesmo registro; não somá-las como total de pessoas.

## O que exige comprovação operacional separada

Identificar a implantação e o banco efetivamente usados; verificar persistência/mount do banco, autenticação anônima recusada, permissões mínimas e storage privado; conferir peer real e proteção contra forwarded headers falsos; testar duas contas autorizadas, admin, recuperação, revogação/suspensão e autorização de arquivos; definir política de malware/MFA/capacidade; controlar publicação e rollback. Não abrir proxy de banco, reiniciar banco, anexar volume sobre dados ou criar serviço pago como teste. Backups/restore e novos recursos pagos dependem da autorização específica do usuário.

O conector de hospedagem disponível em 19/10/2026 fornece apenas nomes das variáveis (valuesRedacted=true), sem sessão de execução no servidor. A instalação local do CLI falhou no download do binário pelo proxy de rede. Portanto esta auditoria está preparada/testada, mas não foi executada no banco publicado. Não há prova de ausência de dados ou vulnerabilidade apenas porque uma consulta não pôde ser executada.

## Validação automatizada

Cinco cenários de dados repetem em mock e MongoDB descartável real: achados e dados intactos, vínculos GridFS válidos, autenticação ausente/privilégios excessivos, consultas indisponíveis e S3 sem provedor. Respostas de connectionStatus nesses cenários são controladas para testar classificação, não evidência de permissões de produção. Dois testes extras verificam configuração insegura e falhas redigidas da CLI. A classificação é conservadora, não auditoria independente nem scanner de malware.

Referência oficial: [MongoDB 8.0 connectionStatus](https://www.mongodb.com/docs/v8.0/reference/command/connectionStatus/). Os testes de agregação usam MongoDB 7 no CI; a versão/compatibilidade do banco publicado precisa ser confirmada.
