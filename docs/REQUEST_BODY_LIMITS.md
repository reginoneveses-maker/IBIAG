# Limite do corpo de requisições na aplicação

O middleware externo da API valida Content-Length antes de chamar a aplicação
e conta os bytes efetivamente consumidos em receive, antes de entregá-los ao
parser. Content-Length ausente ou declarado abaixo do tamanho real não elimina
a contagem. O chunk que ultrapassa o orçamento não é entregue ao parser.

## Limites totais, incluindo envelope multipart

| Requisição | Limite |
|---|---|
| Demais rotas /api, incluindo JSON | 2 MiB |
| /upload, /documents/upload, /documents/import-batch | 64 MiB |
| /documents/link-batch | 2 MiB |
| /documents/metadata-batch | 3 MiB |
| /invoices/parse-xml | 6 MiB |
| /portfolio/import-xlsx, /portfolio/restore-commissions, /leads/import | 64 MiB |

Os caminhos da tabela têm prefixo /api. Barra final conserva o mesmo orçamento.
Os limites de arquivo, ZIP expandido, XML e tabela dentro dos handlers continuam
mais restritos e não foram aumentados. Rotas novas recebem o limite geral até
revisão explícita; um teste exige orçamento para todas as rotas UploadFile atuais.
Não há novas variáveis de hospedagem ou configuração alterada em produção.

Corpo acima do limite retorna 413 estático. Content-Length inválido, duplicado
ou acompanhado de Transfer-Encoding retorna 400 estático. Respostas antecipadas
recebem headers privados/no-store e CORS somente para origens já autorizadas.
Nenhum tamanho informado, valor de header, token ou conteúdo é repetido no erro.

Para estouro durante multipart, a exceção usa o caminho de limpeza do Starlette:
arquivos temporários já abertos são fechados. Se o framework tentar retornar
outro erro depois do estouro, o middleware substitui a resposta por 413. Se a
resposta já começou, não pode mudar o status; interrompe a transmissão com
exceção estática, sem entregar o chunk excedente ou propagar detalhes internos.

## Comprovação e limites

Treze testes cobrem limite antecipado sem leitura/chamada à aplicação, fronteira
exata, chunked, tamanho declarado falso, headers ambíguos, rotas, CORS/headers,
erros posteriores e resposta iniciada. Um teste com o parser multipart real força
o spool em disco e confirma fechamento do arquivo parcial e endpoint não chamado;
outro comprova rejeição de JSON em streaming antes do endpoint.

Isto limita o corpo consumido pela aplicação; não impede que bytes atinjam o proxy
ou socket. Corpos ignorados pelo handler não são drenados só para medir tamanho.
Não é limite global de concorrência, tempo/CPU/memória, taxa por IP nem validação
completa do protocolo HTTP/proxy. Também não desfaz efeitos de código que já tenha
autorizado/processado uma requisição; os handlers atuais parseiam seus corpos
antes das operações. Topologia, timeouts, sanitização de headers e limites do
terminador real continuam exigindo validação publicada. Validar amostras/fluxos
autorizados antes de publicar. Somente dados sintéticos foram usados, sem ativar
serviços pagos, pesquisas externas ou backups.

## Espera do corpo e capacidade por worker

O candidato limita a 16 requisições API ativas por processo, incluindo leitura e resposta. A próxima recebe 503 estático com Retry-After:1, headers privados e CORS exato antes de entrar na aplicação. Slots são liberados em finally, inclusive em falha e cancelamento. Não cria fila ilimitada nem serviço/contador externo; vários workers/réplicas multiplicam esse orçamento e exigem dimensionamento operacional.

A leitura consumida tem orçamento de 30 segundos sem novo bloco e 300 segundos totais desde a entrada no middleware. Um envio em gotejamento não renova o orçamento total. A espera excedida cancela receive e gera exceção multipart compatível com fechamento de temporários, substituindo eventual 400 interno por 408 estático. O orçamento é cooperativo: um receive que não respeite cancelamento ou CPU síncrona bloqueada pode atrasar a interrupção. Não é limite rígido de CPU/tempo de transação. O corpo concluído desarma esses timers para o listener de desconexão de respostas em streaming.

Nove testes adicionais verificam envio parado/em gotejamento, read cancelado, capacidade compartilhada e recuperação de slots, falha/cancelamento externo, listener após corpo completo, resposta/erro após início, configuração inválida e HTTP multipart lento com arquivo forçado a spool em disco e fechado. Não houve carga em produção. Testes de ASGI/HTTPX não comprovam buffers, framing, TLS, limites de socket ou comportamento do proxy real.

As novas recusas não cancelam trabalho já autorizado, fazem rollback ou limitam arquivos já armazenados; o contador é por worker e não quota por usuário/IP. Corpos que a aplicação ignora, cabeçalhos lentos, streams de saída, memória total e concorrência de jobs requerem proteção/capacidade da hospedagem. Validar uploads legítimos nas conexões da operação antes de publicar; não aumentar infraestrutura/limites ou custos automaticamente.

Referência: [asyncio.wait_for no Python 3.11](https://docs.python.org/3.11/library/asyncio-task.html#asyncio.wait_for).
