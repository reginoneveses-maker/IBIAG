# Empresas com relação publicada com o ingrediente

## Problema corrigido

A descoberta anterior aceitava qualquer resultado que mencionasse o produto. Um livro, artigo ou pesquisa podia virar candidato, e o título de uma página de produto podia ser usado como nome da empresa.

## Critério atual

`backend/buyer_discovery.py` pesquisa tanto vendedores/fornecedores quanto fabricantes de alimentos, bebidas e suplementos que utilizam o ingrediente. Antes de retornar um resultado, lê a página, extrai a identidade da empresa e sua relação com o produto, e exige:

- Página comercial da empresa, em vez de diretório, livro, notícia, pesquisa ou artigo genérico.
- Nome da empresa identificado em um trecho literal da página; o título da busca não vira empresa automaticamente.
- Trecho literal de até 25 palavras com o ingrediente e evidência de venda/fornecimento, ou declaração de composição/uso em um produto próprio.
- Classificação `seller` ou `user`, com `relationship_verified`, `product_evidence` e a fonte publicada no resultado.

O texto extraído deve existir na página consultada. Uma empresa apenas citada em um artigo, uma afirmação genérica sobre os usos do ingrediente e dados inventados pela extração não bastam. A busca exclui fontes acadêmicas e diretórios conhecidos antes da leitura. Não há preenchimento de vagas com resultados não conferidos. Há aliases português/inglês para ingredientes comuns e comparação por palavras inteiras (mango não corresponde a mangosteen).

`frontend/src/pages/TradeIntel.jsx` mostra **Vende / fornece o ingrediente** ou **Utiliza o ingrediente em seus produtos**, junto da evidência. `backend/server.py` conserva essa informação no CRM, e `Pipeline.jsx` a exibe ao abrir a empresa. Evidência de venda/uso não confirma compra/importação, decisor ou qualidade dos contatos.

Pesquisas persistidas com o filtro anterior são apresentadas como antigas e não voltam a exibir seus resultados sem nova busca. Isso não remove os registros nem altera os leads existentes.

## Limites e consumo

São feitas duas consultas web por mercado e conferidas até 12 páginas (até 10 na configuração habitual da interface), com duas leituras simultâneas por processo. Domínios diferentes têm preferência antes de uma segunda página do mesmo site. Ler páginas com extração estruturada consome créditos Firecrawl adicionais em relação à busca simples; o orçamento por mercado é limitado, e não há varredura ilimitada. As chamadas de enriquecimento de contatos ao cadastrar no CRM continuam separadas.

Resultados são candidatos sustentados pelas páginas consultadas, não uma lista exaustiva de empresas do mercado. Sites bloqueados, conteúdo em idiomas não reconhecidos e páginas sem evidência explícita podem deixar empresas de fora. Falha em todas as conferências gera erro explícito; nunca reativa os títulos da busca como alternativa.

## Verificação

Testes cobrem livros, pesquisas, diretórios, artigos no site de uma empresa, empresa extraída de página com título de produto, venda e uso em produtos próprios, citações inexistentes, ingrediente errado, limites de leitura, deduplicação, preservação no CRM e pesquisas antigas. O teste Chromium usa o classificador real com respostas controladas do provedor, rejeita livros/artigos e confirma a evidência na pesquisa e no CRM. A resposta do provedor ao pesquisar com a conta real do usuário ainda precisa ser conferida no uso da interface.
