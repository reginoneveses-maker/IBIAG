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
