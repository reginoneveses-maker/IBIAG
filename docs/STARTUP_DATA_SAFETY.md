# Startup sem substituição/purga de dados comerciais

## Problema reproduzido

O startup chamava seed_all, que substituía toda a coleção de produtos na ausência de portfolio_version, apagava toda a coleção trade_data e removia leads por heurísticas de e-mail/empresa quando faltava prospecting-demo-cleanup-v1. A ausência de um marcador não comprova que registros sejam demonstração. Esses writes podiam quebrar referências de ofertas/pedidos/documentos e alterar dados reais durante um restart. Dois testes de regressão falharam antes da correção: preservação de dados sem marcadores e instalação vazia sem carga comercial automática.

## Mudança

As rotinas antigas de seed/purga comercial foram removidas; não há flag que as reative durante o startup. O startup chama apenas o bootstrap administrativo create-only já existente para provisionar acesso, além dos efeitos operacionais abaixo. Reiniciar não popula produtos/templates/trade/leads e não cria/regrava os marcadores comerciais antigos. Dados e referências existentes permanecem iguais nos casos testados. Instalações vazias precisam de importação/cadastro comercial aprovado nas telas existentes. Não foi criada uma nova rotina de migração ou importador.

O bootstrap continua dependente de ADMIN_EMAIL/ADMIN_PASSWORD e só cria conta ausente, sem redefinir senha, promover conta existente ou enviar mensagens. A remoção das purgas não recupera dados apagados em versões anteriores. Nenhuma operação foi executada em banco publicado.

## Testes e limites

Quatro cenários executam o startup real duas vezes quando relevante: dados existentes sem marcadores (incluindo leads que combinavam com as heurísticas antigas e vínculos de produtos/documentos), marcadores existentes preservados, banco vazio com bootstrap administrativo idempotente e falha de índice único sem exclusão comercial. Os mesmos quatro casos são repetidos contra MongoDB descartável real no CI; localmente usam mongomock_motor. Incluem verificação de índices TTL e preservação de IDs/referências. Eles não comprovam migração de todos os formatos legados nem privilégios de produção.

O startup ainda cria índices de segurança/descoberta/usuários e marca jobs pending/running como interrupted. Duplicidades legadas podem impedir a criação de índice: falhar exige triagem, não apagar dados automaticamente. O tratamento de jobs durante restart com múltiplos workers ainda exige revisão operacional. Conectividade, permissão para criar índices, conteúdo/ownership legado e concorrência de processos reais devem ser validados antes da liberação.

Não houve backup, recuperação de dados, limpeza de registros reais, alteração de infraestrutura, publicação em main ou consumo de API paga. Publicação exige o roteiro de segurança do candidato e validação controlada.
