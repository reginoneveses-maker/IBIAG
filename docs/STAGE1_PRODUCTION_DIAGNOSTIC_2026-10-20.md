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
