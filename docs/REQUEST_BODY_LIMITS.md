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
