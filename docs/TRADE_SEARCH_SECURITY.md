# Pesquisa literal em Trade Intelligence

O campo `search` é texto literal, sem sintaxe de expressão regular. O servidor
escapa os operadores antes de consultar empresa/descrição; maiúsculas/minúsculas
continuam equivalentes. Uma pesquisa por `[` antes causava erro 500; agora procura
esse caractere. Padrões como `(a+)+$` não são executados como regex fornecida pelo
usuário. Filtros de país e segmento continuam comparações exatas.

Limites de entrada: pesquisa 128 caracteres, país 8, segmento 64. Entradas maiores
retornam 422 antes da consulta. NUL também é rejeitado para não gerar regex BSON
inválida. Autenticação e limite de 500 resultados continuam.
Três testes HTTP são repetidos em MongoDB descartável na pipeline, sem consultar
provedores externos ou dados de produção. Isso não substitui revisão de índices,
limites globais de requisição e desempenho em grandes bases.
