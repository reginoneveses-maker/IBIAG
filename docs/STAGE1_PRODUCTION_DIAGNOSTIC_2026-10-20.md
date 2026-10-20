# Etapa 1 — primeira execução operacional do auditor

20/10/2026, por volta de11:22 America/Fortaleza. Evidência fornecida pelo operador em captura de tela; não é execução direta do agente nem log completo exportado. O operador confirmou Railway CLI5.71.0 no Windows, login na conta própria, criação local/cadastro de chave SSH e execução de python --version no backend existente, que respondeu Python3.11.17. A chave privada e a passphrase não foram recebidas. A impressão digital do host não foi confirmada por referência independente; a primeira conexão foi aceita pelo operador, com essa limitação informada.

## Resultado legível na captura

O operador executou o bundle readonly_audit_bundle.py fixado no commit8f324ebcf35f720b0aa6a0aa3d0cd0181a8ce751 após o guard SHA256282abee0e1dfc055b1e37f385520eeb2f7dc4dcf7fe3ebea6006c54faa2cc9a3, via stdin/Python isolado no serviço ibiag-backend, ambiente production. Não foi executado startup/server. A saída informa audit_completed=true, read_only=true e production_certified=false; automated_checks_passed=false.

| Verificação | Flag observada | Interpretação limitada |
| --- | --- | --- |
| connectionStatus | query_completed=true | Consulta do estado da conexão concluiu |
| Identidade Mongo | authenticated=false | A conexão do auditor não apresentou usuário autenticado |
| Privilégios | privilege_details_available=false; privileges_require_review=null | Não houve privilégios autenticados disponíveis para atestar mínimo privilégio |
| Leads | leads_missing_owner=true | Existe ao menos um lead sem owner_id, sem revelar contagem ou registros |
| Confiança no proxy | proxy_trust_configured=false | A configuração de IPs confiáveis não está preenchida segundo o código revisado |
| Formato do proxy | proxy_configuration_valid=true | Sintaxe aceita; não comprova peer/cadeia de produção |
| Checagens incompletas | incomplete_checks=[] | As consultas previstas não reportaram falha; não equivale a auditoria de todos os módulos |

Consultas ao banco configurado concluíram sem identidade autenticada apresentada. Esse resultado é incompatível com certificar a exigência de banco protegido, mas ainda não prova configuração efetiva de authorization do mongod nem exposição à internet. É necessário conferir opções reais do servidor e acesso pelo container existente. A inexistência de privilégio autenticado disponível não é evidência de privilégio mínimo.

Na captura também estão true as flags api_docs_disabled, https_origins_configured, jwt_format_valid, paid_discovery_disabled e public_registration_disabled. Elas avaliam variáveis/defaults com módulos revisados do candidato, não introspecção do código antigo publicado. Em particular, não substituem a sonda HTTP anterior que encontrou docs/schema acessíveis. Nenhuma delas certifica o comportamento efetivo dos endpoints na implantação atual.

## Inventário repetido nesta execução

O conector confirmou novamente projeto IBIAG/ambiente production, serviços backend e mongodb online, volumeMounts=[] em ambos, volumes=[] e staged=null. O mongodb continua identificado pelo serviço9cc0395c-7601-451b-a6fa-1511ab168158. Metadados sem volume associado são sinal para diagnosticar dbPath e montagem real, não autorização para anexar volume vazio ou reiniciar. A correlação de rede registrada anteriormente continua separada dessa evidência.

## Próxima verificação e sequência segura

Verificar filesystem/montagem do diretório padrão /data/db no container Mongo existente; isso isoladamente não identifica um dbPath customizado. Em seguida, conferir getCmdLineOpts com saída estritamente selecionada para dbPath/authorization, sem argv completo, variáveis, URI ou credenciais. Comprovar ligação ao banco usado pelo backend antes de propor alteração de autenticação/persistência. Não reiniciar/redeploy Mongo, abrir proxy público, criar cluster, anexar volume vazio, apontar para banco vazio, exportar dados ou ativar backup como atalho.

Leads sem owner exigem atribuição revisada, preservando titularidade; não atribuir tudo ao admin, apagar registros ou inventar permissões para deixar auditor verde. Código candidato já recusa acesso comum sem owner: conferir o legado e a operação pretendida antes de migrar. Proxy requer peer e política real de limpeza de headers; não usar wildcard nem inventar lista de IPs. A etapa1 permanece aberta até corrigir/revalidar os achados e validar a liberação controlada com contas autorizadas.

Nenhuma alteração de conta/dado, autenticação, rede, volume, implantação ou backup foi executada por esta continuação. Nenhum token, URI, passphrase, hash de senha, registro comercial ou captura original foi incluído neste relatório. A sessão SSH pertence ao computador do usuário; o agente ainda não tem canal de execução direta nesse terminal.

## Armazenamento e opções do mongod —11:27–11:28 America/Fortaleza

Novas capturas fornecidas pelo operador confirmam que df -T /data/db no serviço mongodb retornou filesystem/type overlay, montado em /. Isso é evidência de que esse caminho não tem filesystem persistente separado; não se deve interpretar os totais/percentual desse df como tamanho ou consumo exclusivo do banco IBIAG. Não foram reproduzidos esses valores neste relatório.

A consulta somente leitura getCmdLineOpts no admin retornou os três campos selecionados: dbPath=(padrao do servidor), authorization=(nao especificada), keyFileConfigured=false. A ausência de dbPath em parsed não é uma leitura de pathname explícito; no mongod Linux sem dbpath customizado, o padrão documentado é /data/db. Em conjunto com a identidade ausente e consultas de negócio concluídas pelo auditor, a evidência exige correção de controle de acesso. Ainda não houve teste de escrita anônima, enumeração de dados nem exposição pública.

Não houve restart, deploy, alteração de autenticação, usuário Mongo, URI, dados ou volume. Não montar volume vazio sobre /data/db e não mover/copy arquivos WiredTiger ativos como se fossem cópia consistente.

## Proposta de preservação e correção — não executada

1. Dimensionar somente o uso de /data/db e verificar a ferramenta de dump disponível, sem ler/exibir registros. Nenhuma cópia será iniciada nessa fase. Não usar o df global como estimativa do dump.
2. Solicitar autorização específica para uma cópia pontual privada de preservação no computador do operador. A restrição do usuário proíbe iniciar backups sem autorização; autorizações gerais de desenvolvimento não a substituem. Não ativar agenda de backups, bucket ou provedor adicional.
3. Depois da autorização, preparar e validar os comandos de cópia consistente para esta topologia. Identificar todas as fontes de escrita e combinar uma janela controlada: um mongodump em standalone com escrita concorrente não equivale a snapshot pontual. Não presumir que fechar o navegador basta, nem usar --oplog em standalone sem suporte. Não parar/reiniciar backends antigos para obter quiescência sem revisar efeitos de startup. Se forem necessários bloqueio de escrita/indisponibilidade, apresentar a ação e validar recuperação/desbloqueio antes de executar.
4. Conferir integridade e recuperabilidade da cópia em destino autorizado antes de qualquer mudança que substitua o container/disco atual. Nunca publicar dump/manifesto comercial em GitHub, chat ou evidências. Não tratar presença de arquivo/SHA isolado como restauração comprovada.
5. Apresentar dimensionamento/custo e pedir autorização específica para armazenamento persistente e eventuais recursos temporários necessários. A documentação Railway consultada em20/10 lista volume a US$0,15 por GB utilizado/mês e egress a US$0,05/GB, além do plano/compute existentes. Não é cotação do total do usuário; tamanho real ainda não foi medido. Não ativar plano, volume, backup ou serviço com esta proposta.
6. Somente após preservação e destino validados, executar migração controlada para storage persistente e habilitar autenticação com usuário da aplicação limitado ao banco necessário. Criar credenciais fora do chat; nunca embutir em comandos salvos ou logs. Evitar trocar MONGO_URL para destino vazio. Manter plano de retorno que não dependa do antigo disco efêmero sobreviver ao redeploy.
7. Repetir auditor somente leitura, comprovar autenticação/privilégios/montagem, depois tratar leads sem proprietário com titularidade revisada e validar cadeia do proxy. Publicar candidato somente com checks/retorno e homologação autorizada; backups recorrentes continuam desativados.

Referências: https://www.mongodb.com/docs/v8.0/reference/installation-ubuntu-community-troubleshooting/ ; https://www.mongodb.com/docs/manual/reference/command/getcmdlineopts/ ; https://docs.railway.com/volumes/reference ; https://docs.railway.com/pricing/plans . São bases técnicas para o plano, não evidência de execução de migração.

## Dimensionamento e autorização —11:32–11:33 America/Fortaleza

O operador forneceu o resultado de du -sh /data/db:1.1G. É uso físico do diretório e inclui alocação/journal, não tamanho de dump lógico ou estimativa exata do arquivo transferido. Não executar cópias brutas sem consistência nem inferir que o espaço do df global pertence ao banco.

Em11:33 o usuário respondeu sim à pergunta explícita sobre uma cópia pontual de segurança no computador e a pausa temporária das gravações necessária, após ser informado de possível tráfego cobrado. Essa autorização supera somente a proibição anterior para esta cópia/pausa, não para backups recorrentes, criação de volume/serviços pagos ou migração/restart. Nenhum desses recursos foi ativado.

A preparação está no PR53, base sequencial PR52, tools/preserve_mongo_once.sh e docs/ONE_OFF_PRESERVATION.md. São cópia física sob fsyncLock, retorno a gravações antes do download, diretório temporário privado, limites de tempo/tamanho, guard separado e recuperação conservadora que não repete decremento incerto. A documentação oficial alerta que mongodump pode esperar indefinidamente atrás de escritas enfileiradas sob fsyncLock; não foi usado como alternativa cega. O comando mongodump --version solicitado ao operador é apenas descoberta de ferramenta; não iniciou dump.

Onze testes locais sintéticos passaram, incluindo falhas/desbloqueio, morte do processo e stdin Windows. A primeira CI com Mongo8 real detectou que acesso encadeado ao resultado assíncrono de currentOp podia indicar desbloqueio incorreto; a escrita real posterior ficou bloqueada no fixture. As tentativas com await explícito ainda não bastaram: o teste continuou identificando escrita bloqueada apesar da consulta auxiliar indicar falso. O fluxo foi corrigido para exigir fsyncUnlock com lockCount=0 quando a aquisição própria foi confirmada, usar currentOp como comando do servidor e preservar decremento único em resultados incertos. Nenhuma versão intermediária foi executada em produção. O teste de restauração em outro container e validação de BSON/índices/GridFS/escrita continua sendo condição para fornecer comando real. Nunca confundir esses testes descartáveis com restauração dos dados IBIAG.

O banco publicado permanece sem pausa/copiar arquivo/restore confirmado. O helper anterior readonly_audit_bundle.py continua sendo somente leitura; a nova rotina de preservação requer o aceite explícito separado já recebido. A sessão SSH e os dados reais continuam no computador/servidor do operador, sem passagem pelo agente/GitHub/Library.


## Ferramenta pontual — validação isolada aprovada

PR53, commit166fef7d136ac858430fb5aa3380ce91cb92a72e, workflow39445605497/job118706558779: sucesso. Onze testes de falha/recuperação passaram e o ensaio com MongoDB8 real, em containers descartáveis sem rede, confirmou restauração independente de BSON/índice unique/GridFS, escrita na origem após a cópia, escrita no destino restaurado, desbloqueio após falha do arquivo, preservação de lock preexistente e liberação por guard após SIGKILL somente do processo pai. SHA256 do helper:06c5b37d09cd30a1f477020253f161a6d0a74e44205033cad72ea87318bf01bb.

As falhas anteriores incluíram confirmação incorreta do unlock, uso de await fora de função async, incompatibilidade do kernel do runner com Mongo8 e uma verificação de binário BSON pelo método errado do shell. O teste final usa resposta lockCount=0 do servidor, contexto async explícito, runner Ubuntu22.04 compatível e EJSON para verificar bytes. Não foi desativada a proteção do fornecedor contra kernel incompatível. Nenhuma dessas tentativas acessou a Railway.

Esses resultados validam a ferramenta em fixture, não a recuperabilidade dos dados reais. Produção continua sem cópia/pausa confirmada; o próximo passo autorizado depende da execução pelo operador em seu computador, seguida de transferência binária e conferência de SHA256. Volume persistente, autenticação mínima, owners, proxy e homologação continuam pendentes. Não há autorização nova para serviços/volumes pagos, migração/restart ou backups recorrentes.


## Primeira tentativa real —12:17–12:18 America/Fortaleza

O operador executou o helper166fef7 após validação de SHA256. A captura mostrou duas mensagens PRESERVATION_NOT_CONFIRMED e retorno não zero, sem copy_created nem MANUAL_UNLOCK_REQUIRED. Não é cópia confirmada; a etapa exata da falha não estava disponível na saída antiga. Não deduzir a causa a partir de testes sintéticos aprovados.

A consulta posterior somente leitura ao comando currentOp retornou fsync_locked=false. O teste de diretório retornou MARKER_ABSENT. É evidência de ausência de lock de fsync naquele momento e de coordenador residual; não é teste de escrita ou restauração dos dados reais. O diagnóstico pelo here-string terminou com numeric argument required por CRLF no exit0; a consulta anterior terminou e sua saída é visível. Nenhum desbloqueio manual, restart ou segunda tentativa foi solicitado com essa evidência.

A revisão5e1426aac3faab01596a9adb09cb4153062584b8 acrescenta fases/código fixos sem dados comerciais e desliga a entrada padrão de mongosh para evitar disputa com bash -s. O ensaio de Mongo8 passou a receber o script por stdin com CRLF final. A causa da primeira tentativa continua não confirmada. Não houve criação de volume, serviço pago, backup recorrente, migração ou implantação.


Validação da revisão5e1426a: workflow39447680392/job118713828949 aprovado, 11 testes e ensaio Mongo8 por stdin com restauração BSON/índice/GridFS, escrita posterior, falha de tar com fase ARCHIVE/código2 e desbloqueio, lock anterior preservado e recuperação pelo guard após SIGKILL do pai. Pipeline geral39447680122 também aprovada no mesmo commit: backend554+56 subtestes, frontend/build/navegador. SHA256 do helper revisado:5f2760de543eb56871ee7e0c862ab30a019ae1f91f094dd45fb3c6573d6846c0. A revisão não torna a cópia real concluída nem comprova a causa da tentativa anterior. Uma próxima execução deve usar o arquivo/hash novos e retornar fases em caso de erro; não repetir automaticamente nem aceitar avisos de tar.
