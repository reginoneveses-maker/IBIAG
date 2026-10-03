# Empresas com relação publicada com o ingrediente

## Problema corrigido

A descoberta anterior aceitava qualquer resultado que mencionasse o produto. Um livro, artigo ou pesquisa podia virar candidato, e o título de uma página de produto podia ser usado como nome da empresa.

## Critério atual

`backend/buyer_discovery.py` pesquisa tanto vendedores/fornecedores quanto fabricantes de alimentos, bebidas e suplementos que utilizam o ingrediente. Antes de retornar um resultado, lê a página, extrai a identidade da empresa e sua relação com o produto, e exige:

- Página comercial da empresa, em vez de diretório, livro, notícia, pesquisa ou artigo genérico.
- Nome da empresa identificado em um trecho literal da página; o título da busca não vira empresa automaticamente.
- Trecho literal com o ingrediente e evidência de venda/fornecimento, ou declaração de composição/uso em um produto próprio. Uma página comercial pode combinar o título do ingrediente com uma ação de pedido/cotação publicada em outro trecho; a soma das citações é limitada a 25 palavras.
- Classificação `seller` ou `user`, com `relationship_verified`, `product_evidence` e a fonte publicada no resultado.

O texto extraído deve existir na página consultada. Uma empresa apenas citada em um artigo, uma afirmação genérica sobre os usos do ingrediente e dados inventados pela extração não bastam. A busca exclui fontes acadêmicas e diretórios conhecidos antes da leitura. Não há preenchimento de vagas com resultados não conferidos. Há aliases português/inglês para ingredientes comuns e comparação por palavras inteiras (mango não corresponde a mangosteen).

`frontend/src/pages/TradeIntel.jsx` mostra **Vende / fornece o ingrediente** ou **Utiliza o ingrediente em seus produtos**, junto da evidência. `backend/server.py` conserva essa informação no CRM, e `Pipeline.jsx` a exibe ao abrir a empresa. Evidência de venda/uso não confirma compra/importação, decisor ou qualidade dos contatos.

Pesquisas persistidas com o filtro anterior são apresentadas como antigas e não voltam a exibir seus resultados sem nova busca. Isso não remove os registros nem altera os leads existentes.

## Limites e consumo

São feitas duas consultas web por mercado e conferidas até 12 páginas (até 10 na configuração habitual da interface), com duas leituras simultâneas por processo. Domínios diferentes têm preferência antes de uma segunda página do mesmo site. Ler páginas com extração estruturada consome créditos Firecrawl adicionais em relação à busca simples; o orçamento por mercado é limitado, e não há varredura ilimitada. As chamadas de enriquecimento de contatos ao cadastrar no CRM continuam separadas.

Resultados são candidatos sustentados pelas páginas consultadas, não uma lista exaustiva de empresas do mercado. Sites bloqueados, conteúdo em idiomas não reconhecidos e páginas sem evidência explícita podem deixar empresas de fora. Falha em todas as conferências gera erro explícito; nunca reativa os títulos da busca como alternativa.

## Verificação

Testes cobrem livros, pesquisas, diretórios, artigos no site de uma empresa, empresa extraída de página com título de produto, venda e uso em produtos próprios, citações inexistentes, ingrediente errado, limites de leitura, deduplicação, preservação no CRM e pesquisas antigas. O teste Chromium usa o classificador real com respostas controladas do provedor, rejeita livros/artigos e confirma a evidência na pesquisa e no CRM. A resposta do provedor ao pesquisar com a conta real do usuário ainda precisa ser conferida no uso da interface.


## Correção da busca regional (3 de outubro de 2026)

A pesquisa de acerola na Europa retornou uma empresa e falhas em países. Os logs disponíveis mostram a execução e as consultas de progresso, mas a versão anterior não registrava os códigos HTTP das falhas do provedor; não foi possível atribuir retrospectivamente essas falhas a saldo, limites ou timeout.

A conferência com páginas reais reproduziu falsos negativos: AMAZONAS Naturprodukte, Abbott Blackstone International e KoRo Handels GmbH eram rejeitadas pelo filtro anterior apesar de suas páginas comerciais. A versão 3 valida o nome no texto visível, remove URLs de links Markdown dessa conferência e seleciona evidência curta literal da própria página quando a sugestão da extração é incompleta, longa ou imprecisa. A identidade inventada, o ingrediente errado e páginas classificadas como artigos continuam rejeitados.

Agora as chamadas de busca e verificação compartilham um limite de duas requisições simultâneas. Falhas temporárias recebem tentativas limitadas; erros 402, 401, 403 e 429 geram mensagens distintas, e os logs registram apenas operação, categoria e status HTTP. Saldo/chave bloqueados interrompem chamadas dos países ainda na fila. Páginas repetidas são consultadas uma vez por produto e URL durante o mesmo job, sem cache entre usuários. Nomes usuais como United Kingdom e Russia substituem nomes legais longos nas consultas.

A interface informa falhas e consultas incompletas mesmo quando há resultados, diferencia mercado pesquisado de país comprovado da empresa e agrupa empresas repetidas nos mercados. Um endereço publicado de outro país, quando reconhecido, exclui a empresa daquela busca. País ausente ou não fundamentado fica vazio e não é substituído pelo alvo da pesquisa. A classificação e a geografia extraídas ainda exigem validação humana das fontes.

`POST /api/buyer-discovery/search-jobs/{job_id}/retry` exige autenticação e autorização sobre o job, cria uma nova pesquisa só dos países com falha, preserva resultados já encontrados e não altera o histórico original. Pesquisas anteriores à versão 3 devem ser refeitas para aplicar o novo filtro.

Validação: regressões de identidade/evidência, endereço estrangeiro, 429 e 402, cache por job, falha parcial, preservação de resultados e autorização do retry; testes React de aviso/retry e deduplicação; fluxo Chromium atualizado. Páginas reais foram recuperadas via conexão Firecrawl de auditoria: https://www.amazonas-products.com/en/products/acerola/, https://abbottblackstone.eu/organic-products/organic-acerola-powder/ e https://www.korodrogerie.de/en/organic-acerola-powder-250g. O classificador anterior rejeitou as três e o novo aceitou as três. Isso não confirma o saldo da chave de produção nem uma execução autenticada completa dos 51 países; o próximo teste da interface deve verificar os novos diagnósticos e a cobertura.
