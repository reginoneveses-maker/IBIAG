# Importação de XML de NF-e

O endpoint administrativo /api/invoices/parse-xml usa defusedxml 0.7.1 com DTD,
declarações de entidades e referências externas explicitamente proibidas.
Referência oficial: https://pypi.org/project/defusedxml/0.7.1/.

O arquivo tem limite de 5 MiB antes do parser, 64 níveis de profundidade e 50 mil
elementos durante a leitura incremental. Excesso retorna 413; XML inválido ou
proibido retorna mensagem estática 400, sem caminhos, conteúdo ou exceção interna.
Namespaces são tratados na árvore; o encoding declarado é respeitado, sem apagar
bytes inválidos. XML sem estrutura mínima de NF-e e totais negativos/não finitos
são rejeitados. A extração não salva documento, nota fiscal ou arquivo.

Sete testes cobrem saída com namespace, entrada com prefixo/encoding, proibição
de DTD/entidades locais e remotas sem fetch, limites de tamanho/profundidade/nós,
mensagens genéricas, totais e permissões HTTP. Só usam dados sintéticos.

Isto não valida assinatura digital, autenticidade fiscal, autorização da SEFAZ ou
conformidade completa com schema. Também não é antivírus nem limite de ingresso
do proxy/multipart. CSV/XLSX e recursos dos demais importadores continuam exigindo
revisão própria. Nenhum XML de produção foi consultado e não há chamadas externas
durante o parsing. Validar amostras autorizadas antes de publicar a alteração.
