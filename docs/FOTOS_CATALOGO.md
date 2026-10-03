# Fotos reais no catálogo

O importador de portfólio cria produtos sem `image_url`. O catálogo agora dá prioridade à foto cadastrada e, quando ela estiver vazia, inválida ou não carregar, usa uma fotografia real do ingrediente identificado no nome do produto.

As fotografias ficam em `frontend/src/assets/product-photos`, são publicadas pelo build em `/static/media/` e não dependem de serviços de imagens externos nem de chamadas ao Firecrawl durante a navegação. `credits.json` registra fonte, autor, licença e a alteração de apresentação (thumbnail do Commons e enquadramento por CSS). Os créditos e os links da licença aparecem em cada card. Cada fotografia conserva sua licença original, incluindo as condições de compartilhamento pela mesma licença quando aplicáveis.

Há fotos de açaí, acerola, coco, castanha de caju, castanha-do-pará, guaraná em pó, abacaxi, laranja, maracujá, goiaba, limão-tahiti, banana, cupuaçu, manga e limão-siciliano. A associação aceita nomes em português/inglês e ignora diferenças de acentuação e pontuação. Misturas identificadas e nomes desconhecidos não recebem uma foto arbitrária pela categoria.

As fotos pesquisadas são **representativas do ingrediente**, conforme indicado no card. Não comprovam o fabricante, lote, embalagem, certificação orgânica ou aspecto final do pó/extrato. Para exibir a fotografia específica do produto oferecido, cadastre sua URL HTTPS em **Gestão → Produtos → Editar → Imagem / URL**. Essa foto tem prioridade sobre as imagens representativas. Se nenhuma imagem estiver disponível, o card apresenta uma mensagem em vez de um ícone de imagem quebrada.

Validação: testes React para produtos importados, distinção entre castanhas, misturas, prioridade da foto cadastrada e falhas sucessivas; teste Chromium para decodificar as 15 fotos publicadas pelo build, fallback de URL inválida e persistência após recarregar o catálogo. A base desse teste é isolada; não há alteração nos produtos ou arquivos existentes na produção.
