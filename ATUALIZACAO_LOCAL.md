# Atualização da instalação existente da IBIAG

Esta versão reúne amostras, qualidade documental e dossiê do pedido. É atualização de código, não importação nem migração do banco. O computador do usuário não foi acessado por esta entrega.

## Antes de começar

1. Finalizar/pausar a importação e quaisquer alterações pelo Claude ou outro operador. Fechar formulários de edição e não iniciar nova importação até terminar.
2. Usar **Baixar backup completo** no menu e aguardar o download. Validar o arquivo com o verificador existente quando disponível; preservar o arquivo fora da pasta de código. Não prosseguir sem a cópia completa. Não publicar o backup, pois contém dados e usuários.
3. Conferir os totais na instalação atual e registrar também eventuais importações posteriores. Foram informados pelo usuário 635 documentos e 3.006 leads; estes números não foram verificados remotamente.
4. Preservar a pasta antiga de código para retorno. Extrair a nova versão em outra pasta permanente; não substituir dados, arquivos enviados ou configuração por arquivos do ZIP.

## Invariantes

- Manter exatamente o projeto Docker ibiag-local e o volume existente ibiag-local_mongo_data.
- Não apagar, recriar, mover, restaurar por cima ou esvaziar o volume. Não usar down -v, volume rm, volume prune ou reset do Docker.
- Não criar, editar, copiar por cima, regenerar nem exibir o conteúdo de %LOCALAPPDATA%\IBIAG\Local\.env.local.
- Sem alterar MongoDB, usuários, senhas, autenticação, redes, portas ou variáveis da instalação.
- Não conectar este procedimento à Railway ou a outro Docker remoto.
- A atualização substitui somente os contêineres api e web. Pode interromper brevemente o uso da aplicação.

## Aplicação pelo operador local

Abra PowerShell na raiz do NOVO pacote, onde existe compose.local.yaml. Antes de executar qualquer mudança, confirme Docker Desktop local com Linux containers, contexto npipe/unix local e ausência de DOCKER_HOST remoto. Se a instalação/configuração/volume não existirem, interrompa: este procedimento não é primeira instalação.

As variáveis abaixo são apenas caminhos e parâmetros de execução; não alteram o arquivo de configuração:

~~~powershell
$ibiagConfig = Join-Path $env:LOCALAPPDATA "IBIAG\Local\.env.local"
if (-not (Test-Path -LiteralPath $ibiagConfig)) { throw "Configuracao original ausente. Interrompa." }
$ibiagRoot = (Get-Location).Path
$ibiagCompose = Join-Path $ibiagRoot "compose.local.yaml"
if (-not (Test-Path -LiteralPath $ibiagCompose)) { throw "Abra o terminal na raiz do novo pacote." }
~~~

Confira a existência do volume por listagem. Se não aparecer, interrompa sem criar outro:

~~~powershell
$ibiagVolumes = @(& docker volume ls --format '{{.Name}}')
if ($LASTEXITCODE -ne 0 -or $ibiagVolumes -notcontains "ibiag-local_mongo_data") { throw "Volume original nao confirmado. Interrompa." }
~~~

O ambiente do processo não deve sobrescrever LOCAL_MONGO_ROOT_PASSWORD, LOCAL_DB_PASSWORD ou LOCAL_JWT_SECRET. Não imprimir seus valores. O iniciador existente tem esse isolamento; um operador que execute os comandos diretamente deve conferir/remover apenas as sobreposições do processo, preservando os valores para restaurá-los ao final, sem editar .env.local. COMPOSE_PROFILES e COMPOSE_ENV_FILES também não devem apontar a outra implantação.

Após confirmar backup, pausa da importação e contexto local, reconstruir SOMENTE as imagens da aplicação. A compilação ocorre antes de substituir serviços, preservando a instalação ativa se o build falhar:

~~~powershell
docker compose --project-name ibiag-local --project-directory $ibiagRoot --env-file $ibiagConfig -f $ibiagCompose build api web
if ($LASTEXITCODE -ne 0) { throw "Compilacao falhou. Nao atualize os servicos." }
docker compose --project-name ibiag-local --project-directory $ibiagRoot --env-file $ibiagConfig -f $ibiagCompose up -d --no-deps --wait --wait-timeout 180 api web
if ($LASTEXITCODE -ne 0) { throw "Atualizacao nao confirmada. Preserve tudo e investigue o erro." }
~~~

Não executar up para mongo, inicializador de banco, local_admin.py, importação, restauração ou criação de nova conta durante esta atualização. Não é necessário fazer logout dos dados nem refazer cadastros.

## Conferência após atualizar

- Abrir http://127.0.0.1:8787, entrar com a conta existente e atualizar o navegador.
- Conferir totais de leads/documentos e abrir alguns cadastros e arquivos já importados. Comparar com os totais registrados antes; registros na lixeira podem alterar o significado do contador.
- Verificar produtos/fornecedores, cotações/pedidos e arquivos privados.
- Verificar menu Amostras; Qualidade documental; e Ver dossiê em Pedidos/Operação do dia.
- Não confirmar vendas, pagamentos, recebimentos ou movimentações de estoque apenas para testar com dados reais.
- Só então retomar importações/uso. A conferência automatizada do código usa dados sintéticos, não substitui esta validação local.

Se houver falha, manter volume, configuração, backup e pasta antiga. Não improvisar restauração na base ativa. A versão antiga pode exigir reconstrução de api/web a partir da pasta antiga sob as mesmas precauções; dados novos criados por módulos novos não devem ser apagados.

## Validação do código

Base funcional a088a67aa5629d8bc7840eb1b440266ac6f9e3f6: 622 testes backend e 56 subtestes; 352 testes frontend; build e navegador; instalação isolada dos contêineres, autenticação/persistência e iniciador Windows aprovados nos PRs 55, 56 e 57. Este guia não executa nem comprova uma atualização no computador do usuário.
