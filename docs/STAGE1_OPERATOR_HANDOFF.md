# Desbloquear a validação operacional da etapa 1

O candidato está no PR draft28; não publicar apenas para obter estes dados. O conector atual fornece metadados, sem terminal/valores de variáveis. O CLI não foi instalado neste ambiente porque o download do binário falhou no proxy. Não há agente SSH ou token CLI disponível aqui. É necessário um caminho de execução autenticado no backend existente ou conexão de leitura ao banco existente, sem enviar segredos em conversa.

## Sessão do operador existente

Usar a conta administrativa própria da hospedagem e um terminal confiável. A documentação oficial permite SSH ao container já publicado, sem criar outro serviço. Se precisar autenticar o CLI, usar railway login no computador do operador; não copiar token/chave privada para chat. A primeira sessão pode pedir cadastro de chave pública. Revisar esse acesso com o responsável; não ativar agente/serviço novo ou workspace com permissões maiores como atalho.

Alvo confirmado pelos metadados: projeto IBIAG, ambiente production, serviço ibiag-backend. Com CLI e chave autorizados, um comando de confirmação sem dados pessoais:

~~~sh
railway ssh --project c1a9635c-789b-4e42-ac9b-cca4326fab9a --environment fcab95f8-3e30-4da9-8e0b-d9b7f94747ce --service ecbfc64a-75d8-47b2-9b25-b2f7467e77e6 -- python -c "print('SESSION_READY')"
~~~

Esse comando apenas confirma execução do Python; não comprova permissões/persistência do banco.

## Auditoria sem deploy

Baixar/revisar [readonly_audit_bootstrap.py](../tools/readonly_audit_bootstrap.py) desta branch de auditoria. O arquivo não contém credenciais. Ele confere os IDs de projeto/ambiente/serviço herdados da sessão, baixa somente três módulos do commit testado883e063, verifica SHA-256 antes de qualquer import, executa o auditor em processo Python isolado e remove somente seus arquivos temporários privados. Não carrega .env, importa server, roda startup, escreve no banco ou retorna URI/registros/segredos.

PowerShell, a partir da pasta onde o arquivo revisado foi salvo:

~~~powershell
Get-Content -Raw -Encoding UTF8 .\readonly_audit_bootstrap.py | railway ssh --project c1a9635c-789b-4e42-ac9b-cca4326fab9a --environment fcab95f8-3e30-4da9-8e0b-d9b7f94747ce --service ecbfc64a-75d8-47b2-9b25-b2f7467e77e6 -- python -
~~~

Bash equivalente usa o mesmo comando railway ssh ... -- python - com entrada redirecionada do arquivo. Dados de conexão vêm apenas do ambiente do backend existente. Se a sessão não herdar o ambiente correto ou não alcançar GitHub/banco, o comando falha com mensagem estática: não force IDs/credenciais, abra proxy público ou faça deploy para contornar. A API de dados também pode ser auditada por conexão MongoDB compatível existente; a disponibilidade do conector não comprova acesso ao alvo privado.

O resultado JSON contém contagens e flags; tratar em canal privado. production_certified será sempre false. Código0 significa só verificações automatizadas aprovadas;1 indica achados/checagens incompletas;2 indica execução não confirmada. Revisar OPERATIONAL_READONLY_AUDIT.md para escopo e limites. Não apagar/transferir registros ou elevar privilégios para obter um resultado verde.

O bootstrap foi verificado localmente em três cenários sem banco/SSH real: alvo ausente recusa antes da rede; origem com hash errado recusa antes de executar; processo isolado importa os três módulos válidos e recusa ausência de configuração do banco. Esses três checks não fazem parte da contagem da pipeline da aplicação e não comprovam sessão publicada.

## Depois do diagnóstico

Comprovar persistência/autenticação/privilégios e storage privado; resolver achados preservando dados; validar peer/forwarded headers e políticas de conteúdo/capacidade; estabelecer checks/rollback; publicar o SHA testado e realizar fluxos com duas contas autorizadas/admin. Recuperação que altera credenciais usa outro comando, com TTY e titularidade confirmada; nunca executar reset de conta real apenas para testar.

Nada deste roteiro autoriza novos serviços pagos, créditos, backup/restore, mudança destrutiva, reinício de banco ou abertura de rede. A sugestão de conector MongoDB não cria/conecta cluster automaticamente. Ainda não foi executado diagnóstico no banco publicado.

Referência oficial consultada: [railway ssh](https://docs.railway.com/cli/ssh). Usar o container existente, sem sessão persistente que instale ferramentas extras e sem port forwarding.

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
