# Histórico operacional completo, em páginas

Entrega posterior ao PR51, ainda sem deploy/aceite de produção. Abrange cotações, Commercial Invoices, Packing Lists e embarques. Não é auditoria global de todo CRUD/login, assinatura de eventos, reconstrução integral de snapshots ou backup. Persistência e durabilidade reais ainda dependem da etapa1.

## Consulta

Os quatro formulários oferecem a mesma linha do tempo: autor, instante, motivo e alterações em campos identificados para o usuário. Eventos antigos são carregados sob demanda. Leituras pequenas reutilizam os eventos recentes já obtidos pelo formulário; Atualizar histórico consulta o servidor. Paginação preserva o que já foi exibido; erro/revisão diferente pede recarregar o documento, sem misturar históricos. Respostas tardias são descartadas. Histórico não aprova, altera ou restaura a operação.

GET `/api/operations-history/{kind}/{id}` com kind `quotation`, `commercial_invoice`, `packing_list` ou `shipment`. Somente admin, inclusive quando o solicitante comum é proprietário da empresa do CRM. Registros arquivados/cancelados continuam consultáveis; ambíguos são recusados. Até50 eventos por página, padrão20, com limite adicional de512KiB de eventos; o cursor permite continuar sem truncamento silencioso. A versão da origem ancora a consulta. Se mudar entre páginas,409 e atualização necessária. Cabeçalhos private/no-store e nosniff, sem concessão de acesso por possuir um cursor.

Cursor opaco tem MAC HMAC-SHA256 com chave derivada e finalidade separada da autenticação, recurso/tipo/versão vinculados e validade de15min. Não é token de login nem substitui o Bearer administrativo. Nenhum segredo entra na URL/resposta; valores inválidos/expirados retornam erro estático, sem refletir dados. A interface não usa HTML do evento nem exibe JSON técnico como formulário de negócio.

## Modelo e consistência

A coleção `operation_history` guarda blocos de eventos antigos no mesmo banco já usado pela aplicação. Sem serviço externo, scheduler, TTL, limpeza automática, índice adicional, cluster ou mudança de topologia. Coleção é criada pelo próprio Mongo somente ao gravar um primeiro bloco. Nenhum desses procedimentos foi executado na base publicada.

Cada documento/embarque mantém eventos recentes e uma referência compacta ao último bloco, contagem e versão do último evento arquivado. Ao atingir32 eventos ou96KiB de histórico, o servidor prepara um bloco somente com eventos **já confirmados** e conserva a lista recente vazia para receber a próxima alteração. Não copia a alteração proposta para o arquivo antecipadamente. Blocos têm ID derivado de SHA-256 do conteúdo e referência ao bloco anterior; inserção é idempotente e não atualiza conteúdo existente. Limite de512KiB por bloco; registro principal continua limitado a256KiB. Eventos inválidos, lacunas/IDs repetidos, divergências ou excesso de tamanho pedem revisão, sem apagar registros para “corrigir”. Inteiros BSON Int64 são aceitos sem admitir booleanos como contadores.

Gravação segue a trava de negócio existente e CAS de versão. O bloco é inserido/conferido antes da troca atômica do registro principal; a nova referência e a nova alteração são persistidas **juntas**, nessa única troca. Caso insert, CAS ou lease falhem, a origem continua referenciando seu histórico anterior. Um bloco copiado pode ficar inalcançável, mas guarda somente eventos antigos confirmados: não é percorrido nem contado como revisão nova. Retry reutiliza o mesmo bloco. Não exige transação entre coleções ou réplica nova em um Mongo standalone. Não promete que o banco não perderá dados em falha de armazenamento.

Leitura segue somente a cadeia alcançável a partir da origem e valida hash, tipo, recurso, contagem e sequência. Não procura “todos os blocos do ID”, evitando incluir cópias não referenciadas por gravações falhas. Bloco ausente/adulterado gera409, em vez de histórico vazio ou falso sucesso. Cada busca de bloco usa a chave primária `_id` já indexada pelo Mongo; não há lookup global/varredura de toda a coleção. O próprio documento continua fonte da operação, estoque, financeiro e revisões comerciais. Referências internas do arquivo não são copiadas para a memória da venda ao converter cotação.

Os limites de50/100 eventos das funções puras continuam como proteção interna contra entrada inválida; o fluxo HTTP mantém a janela recente abaixo deles para que não interrompam alterações válidas. A retenção total deixa de depender do tamanho de uma única lista BSON. Não há exclusão/exportação/restauração de blocos na API. Operadores com privilégios diretos no banco podem alterar dados; hashes detectam divergências no caminho consultado, sem afirmar prova criptográfica externa ou WORM.

## Testes

`test_operation_history.py`:11 cenários HTTP, repetidos no MongoDB descartável da CI. Exercitam quatro tipos, paginação completa/sem duplicação, limiar padrão com61 eventos de invoice/106 de embarque, permissões, privacidade e leitura sem escrita, falha de insert, falha depois de inserir/antes de CAS, lease expirada, retry idempotente, concorrência, cursor assinado/expirado/cruzado, cursor recusado como login, revisão alterada, blocos corrompidos/ausentes, limite de bytes/continuação, histórico legado inválido preservado e exclusão do cabeçalho de auditoria da memória comercial.

`OperationHistory.test.jsx`:6 cenários de interface, incluindo texto seguro, páginas, erro com preservação, descarte de resposta tardia, revisão incompatível e atualização sem duplicar. A suíte anterior permanece ativa. Chromium cria34 revisões sintéticas de cotação, encontra20 na primeira página e todas34 após continuar, confere o evento inicial e o último, atualiza sem duplicação e mantém uma conta financeira. Imagens desktop/móvel são inspecionadas; nenhuma base real é usada.

Resultados concretos da CI e evidências serão anexados ao PR. Skips locais de Mongo/Docker não equivalem a execução desses casos. Permanecem: comprovação de armazenamento/persistência e proxy da etapa1, homologação com contas autorizadas, política operacional de retenção/monitoramento de crescimento e qualquer ampliação de auditoria para outros módulos.
