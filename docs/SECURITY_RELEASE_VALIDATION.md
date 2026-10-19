# Liberação controlada da etapa 1 — verificações ainda não executadas

Este roteiro prepara a validação; não autoriza declarar produção validada. A
aplicação continua fora de main, no PR draft 28. Não executar pesquisas pagas,
ativar serviços ou disparar backups para realizar estes passos.

## Critérios antes do deploy

1. Fixar o SHA candidato e exigir a pipeline inteira nesse SHA, com MongoDB
   descartável, testes de interação, build e navegador. Não compor novamente os
   PRs individuais sobre a composição já existente.
2. Revisar a política inicial: usuários comuns acessam o próprio CRM/tarefas e
   leitura de materiais compartilhados; operações de ERP/finanças e alterações
   corporativas são administrativas. Conferir as contas existentes sem promover
   ninguém automaticamente. Ainda não há tenancy entre empresas.
3. Levantar apenas contagens e integridade dos dados legados: leads/tarefas sem
   responsável, referências a usuários ausentes, IDs duplicados, anexos órfãos e
   classificações desconhecidas. Não apagar, transferir ou reclassificar em massa.
4. Confirmar origens HTTPS exatas e validade do segredo JWT (mínimo 32 caracteres)
   sem imprimir valores. No candidato do PR 33, o bootstrap passa a criar somente contas ausentes;
   não redefine a senha existente ao mudar ADMIN_PASSWORD ou reiniciar. A versão
   ainda publicada deve ser conferida separadamente. No PR 38, as purgas/seeds comerciais de startup foram removidas; conferir a versão
   efetivamente publicada, os índices e o efeito sobre jobs antes de reiniciar uma
   instalação existente. A remoção do código não recupera dados já apagados.
5. Confirmar o comando real do container e o peer visto pelo servidor. A
   documentação pública do proxy não comprovou uma lista de IPs confiáveis nem
   todo o comportamento contra falsificação de cabeçalhos. Não usar wildcard,
   aceitar cabeçalhos do cliente ou inventar allowlist. Sem confiança comprovada,
   o limitador vê o peer do proxy e pode agrupar usuários legítimos.
6. Identificar o banco efetivamente usado pela aplicação sem registrar a URI.
   Comprovar persistência, autenticação/rede/privilégios mínimos do MongoDB e
   acesso privado do storage efetivo, políticas IAM e ausência de endpoints
   públicos indevidos. Em 19/10, os metadados do serviço mongodb listado na
   hospedagem não mostram volume montado nem nomes de variáveis; isso não
   comprova que seja o destino de MONGO_URL ou a política efetiva do banco.
   Ausência de proxy TCP público isoladamente não prova proteção suficiente.
   Não reiniciar/mover o banco, anexar volume sobre seus arquivos ou provisionar
   serviços como experimento. Preparar plano revisável de preservação/migração
   antes de qualquer ação; backups/serviços pagos exigem autorização específica.
7. Preparar controle de deploy/rollback: main atualmente pode iniciar publicação
   sem esperar checks. Não alterar configurações que reiniciem serviços sem
   conhecer o efeito. Não criar ambiente/serviço pago como atalho.
8. Resolver ou aceitar explicitamente com a operação as pendências de código
   registradas na auditoria: recuperação de senha esquecida/emergência administrativa,
   conteúdo/malware, concorrência/tempo/CPU globais e auditoria operacional de
   segredos/privilégios. O código já inclui limites de XML, CSV/XLSX e corpos da API;
   isso não comprova limites do proxy/socket nem detecção de malware. A auditoria
   offline do histórico Git tem cobertura/filtros e exclusões documentados.

## Evidências depois da publicação controlada

- Registrar SHA implantado, horário e resultado dos checks; nunca registrar tokens,
  senhas, URLs privadas ou conteúdo comercial nos relatórios.
- Com duas contas autorizadas e um admin: comprovar acesso próprio, negar IDs
  alheios e aliases de arquivos, negar ERP/finanças ao usuário comum e verificar
  dashboard sem totais privados. Conferir dados legados pelo admin.
- Provar logout/replay, expiração, suspensão/reativação de conta comum, troca de
  senha e permissão lida do banco. Tokens antigos devem continuar recusados após
  reativar ou trocar a senha; confirmar novo login e persistência da nova senha. Provar tentativa por
  conta e por cliente real atrás do proxy usando identidades de teste e sem
  bloquear o administrador ou fazer testes de carga em produção.
- Verificar origens CORS permitidas/negadas, headers reais, HTTPS, docs/debug,
  downloads, preservação da prévia PDF/imagem e falhas genéricas sem vazamento.
- Validar importações CSV/XLSX/XML com dados sintéticos e dentro/fora dos limites,
  incluindo ausência de alterações quando recusadas e fechamento de temporários.
  Validar tamanho de ingresso e timeouts reais do proxy sem testes de carga.
- Verificar que a versão publicada deixou de carregar scripts de telemetria e
  analytics removidos no PR 37; usar rede do navegador sem registrar dados sensíveis.
- Confirmar descoberta externa e backups continuam pausados. A flag de pesquisa
  padrão false no novo código não cancela jobs antigos já em execução.
- Documentar qualquer falha, corrigir e repetir o teste afetado antes de encerrar
  a etapa. Manter rollback conhecido; não oferecer backup de produção como
  solução automática sem a autorização específica exigida pelo usuário.

Nenhuma dessas verificações publicadas foi executada por este documento.
