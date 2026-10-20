# Cópia pontual de preservação — procedimento do operador

Autorização específica recebida em20/10/2026,11:33 America/Fortaleza: uma cópia pontual para o computador do operador, possível tráfego adicional e pausa temporária de gravações. Não autoriza backups recorrentes, serviços/volumes pagos ou migração/restart. Esta entrega prepara a ferramenta; não comprova cópia em produção.

## Razão e limites

O diagnóstico operacional encontrou Mongo sem identidade autenticada, diretório padrão em overlay e nenhum volume Railway associado. du -sh /data/db mostrou1.1G: tamanho de filesystem, não volume de dados lógico nem previsão exata de arquivo/tráfego. Não reiniciar o Mongo, montar volume vazio sobre os dados ou apontar a aplicação para um banco vazio antes de preservar e validar uma recuperação. O backup lógico existente em backend/backup.py permanece separado; não foi agendado/acionado. Este helper de manutenção copia fisicamente o Mongo standalone8 para preservar o disco atual antes de qualquer migração.

A documentação oficial do Mongo8 declara que fsync com lock torna os arquivos seguros para cópia com tar e que leituras de mongodump podem ficar bloqueadas depois de gravações enfileiradas. Por isso, o helper usa arquivos do dbPath, incluindo journal, com um único lock e desbloqueio antes da transferência ao computador. Não usar --oplog em standalone. Não copiar WiredTiger ativo sem o lock. Referência: https://www.mongodb.com/docs/v8.0/reference/command/fsync/ .

## Contrato de tools/preserve_mongo_once.sh

Exige --approved-one-off e os IDs exatos de projeto/ambiente/serviço Mongo. Destino de consulta é somente mongod local padrão: nunca recebe URI/senha, não baixa código/dependências, não conecta serviços externos. Antes da pausa, recusa Mongo diferente de8/WiredTiger, replica set/mongos, dbPath customizado, criptografia em uso, lock preexistente, links simbólicos no dbPath, ferramentas ausentes ou menos de3GiB livres em/tmp. Mongo8 é a versão indicada no serviço atual; preflight ainda precisa confirmar a instância efetiva.

Um marcador privado com token único impede cópias simultâneas. A saída e erros nunca mostram nomes/registros/contagens do banco. A cópia temporária fica em diretório0700 com arquivo0600. Contém informações comerciais e deve permanecer somente no servidor existente/computador autorizado, nunca em chat, GitHub, Library ou anexos de auditoria.

Aquisição do lock tem limite de15s; tar tem timeout110s e limite de arquivo de2GiB. Erro/aviso de tar invalida a cópia. Trap de saída/sinal chama liberação; um processo separado de prazo150s serve de proteção para desconexão/interrupção comum. O token impede que um guard antigo libere uma nova sessão. O decremento do lock nunca é repetido cegamente: resposta incerta ou lock restante exige verificação manual, preservando locks de outras operações. Não há garantia de cleanup frente a SIGKILL de todos os processos, falha do host/banco ou indisponibilidade total; operador deve permanecer disponível para recuperação. Não executar outro lock/backup administrativo em paralelo.

A cópia só ganha nome final após desbloqueio confirmado e verificações gzip/tar/SHA256. A saída copy_created=true/writes_unlocked=true não certifica restauração dos dados reais: restoration_proven permanece false. Um arquivo parcial ou código diferente de0 não é uma cópia confirmada. As verificações de conteúdo não substituem restauração em destino autorizado.

## Sequência de uso — aguardar evidência de teste

1. Confirmar as versões/ferramentas disponíveis na sessão Mongo existente, suficiente espaço livre e ausência de outro operador realizando manutenção. Não expor credenciais. Baixar somente o helper do SHA revisado; conferir SHA256 antes de enviar como stdin para bash no container Mongo com --approved-one-off. O comando final de execução só será fornecido depois dos testes.
2. Manter o terminal aberto. A saída de sucesso informa caminho privado temporário, bytes, SHA256 e writes_unlocked. Em qualquer falha, verificar se a liberação foi confirmada. Se aparecer MANUAL_UNLOCK_REQUIRED, não iniciar outra cópia nem reiniciar; consultar estado do lock e o marcador desta sessão, e executar somente o desbloqueio correspondente, sem loops de fsyncUnlock.
3. Transferir o arquivo por railway service files download, que preserva bytes, para uma pasta privada no computador do operador. Não usar redirecionamento/pipe de bytes via Windows PowerShell5, que pode alterar o arquivo. Não usar --overwrite. Conferir SHA256 local igual ao remoto e teste de integridade; a cópia no/tmp do mesmo container, sozinha, não resolve a perda de dados no redeploy.
4. Validar recuperabilidade em destino autorizado e separado antes de qualquer mudança que descarte a instância atual. Versão/formato compatíveis, índices e tipos BSON e anexos/GridFS devem permanecer. Não restaurar sobre a origem, executar --drop nela ou alterar senha/owners para fazer os testes passarem. Nenhuma restauração em produção foi autorizada/executada por este documento.
5. Manter a cópia privada até aceite da migração e política de retenção acordada. Não apagar automaticamente a cópia validada. Solicitar separadamente o custo/escopo do storage persistente e qualquer recurso temporário necessário; não criar infraestrutura enquanto só há autorização para a cópia pontual.

## Validação prevista e executada

Onze testes locais com arquivos sintéticos e Mongo simulado passaram: cópia byte a byte/hashes; erro de arquivo com desbloqueio e sem vazamento; alvo/aceite explícito; lock anterior preservado; falha de unlock conserva marcador; guard após SIGKILL; token antigo não libera novo owner; stdin com CRLF final do Windows; sintaxe dos comandos em contexto async; lock próprio confirmado precisa de fsyncUnlock mesmo se uma leitura auxiliar indicar falso. Nenhum dado real, rede Railway ou lock real foi usado localmente.

A workflow preservation-check.yml não tem cron nem backup de aplicação: executa somente em PR com alteração da ferramenta. Cria containers Mongo8 descartáveis sem rede, grava fixture sintética, faz cópia física, restaura em outro container e confere tipos BSON, índice unique, bytes de GridFS, ausência de alteração posterior à cópia e escrita normal na réplica restaurada. Também força erro de tar para confirmar desbloqueio no Mongo real e recusa lock preexistente sem liberá-lo. Resultado da CI será registrado no PR antes de fornecer comando de execução.

A ferramenta não torna o banco autenticado, persistente ou a etapa1 concluída. Corrigir esses achados e revalidar proxy/titularidade/contas continua necessário.

A primeira execução CI encontrou timeout da escrita posterior à cópia sintética: acesso encadeado ao resultado assíncrono de currentOp havia produzido confirmação incorreta de desbloqueio. O procedimento não foi fornecido/executado em produção. As chamadas Mongo foram colocadas em contexto async explícito. A tentativa seguinte ainda encontrou escrita bloqueada apesar da consulta auxiliar indicar falso. O fluxo foi corrigido para não pular fsyncUnlock quando a aquisição própria foi confirmada e exigir lockCount=0 da resposta do servidor. As consultas passaram a usar o comando currentOp do servidor, em vez de tratar o helper do shell como prova de unlock. A escrita real posterior continua sendo condição obrigatória do teste. A validação final será discriminada no PR, sem tratar a tentativa falha como sucesso.

O teste real também mata o processo pai em uma fixture com prazo reduzido para comprovar que o guard separado libera um lock Mongo real e permite escrita. A alteração de prazo existe apenas na cópia do script da fixture; o helper publicado mantém150s. Cópia sintética/restauração e falhas anteriores não representam pausa ou backup executados em produção.


## Tentativa operacional e diagnóstico adicional —20/10 12:17–12:18

O operador executou a versão166fef7 com hash conferido. A saída informou PRESERVATION_NOT_CONFIRMED duas vezes, sem sucesso ou MANUAL_UNLOCK_REQUIRED. Consulta posterior somente leitura ao comando currentOp retornou fsync_locked=false e o marcador estava ausente. Não há cópia confirmada nem prova de restauração real. O erro numeric argument required veio do exit0 com CRLF do here-string de diagnóstico; não invalida a saída anterior da consulta.

A revisão seguinte passa a informar fase fixa e código de retorno de tar, sem nomes de arquivos, registros ou erros brutos. Não afrouxa a rejeição de avisos/erro de tar e não presume a causa da falha. Todas as chamadas mongosh isolam stdin em /dev/null para não disputar a entrada de bash -s. O ensaio real passa a enviar o helper por stdin com CRLF final, além dos testes de arquivo/restauração/falhas/guard. O resultado dessa revisão precisa passar na CI antes de outra tentativa operacional.
