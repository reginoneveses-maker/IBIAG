# Fotos e filtros do catálogo

O catálogo identifica o ingrediente pelo nome PT/EN, com normalização de acentos e pontuação. Não compara a categoria importada diretamente com os filtros: linhas como `Herbs and Roots`, `Superfruits`, `Nuts and Seeds` e valores vazios não são nomes de ingredientes. Os cinco filtros principais mostram suas quantidades; o seletor **Mais ingredientes** oferece os demais ingredientes presentes no portfólio. Produtos desconhecidos ficam em **Outros**. Sucos/polpas são selecionados pela apresentação; caju em suco não aparece em Castanhas. Misturas podem pertencer aos ingredientes identificados, mas não recebem uma imagem de um só ingrediente.

## Imagens por apresentação

`productPhotos.js` exige ingrediente **e apresentação** compatíveis. Açaí extract powder, freeze dried e pulp usam imagens diferentes. Frutas inteiras não são fallback para pós, extratos, polpas, sucos, leite, água, óleo ou concentrados. Não se reutiliza pó de guaraná moído como fotografia de extrato de guaraná. Nomes sem apresentação suficiente (por exemplo, apenas MANGO) não recebem uma imagem adivinhada.

Há 14 imagens de apresentação: extrato de açaí em pó, açaí liofilizado em pó, polpa de açaí, acerola em pó (suco desidratado), extrato de camu-camu em pó, guaraná em pó e sementes, castanhas de caju e do pará, muirapuama em pó, moringa em pó, pau d’arco em pó e cortado e catuaba em pó. A imagem de acerola em pó não é automaticamente usada em extratos padronizados nem concentrados; essas apresentações ainda precisam de imagem própria.

Fotos pesquisadas são referências da apresentação mostrada, não comprovam a identidade de lote, fabricante, embalagem, teor de extrato ou certificação orgânica de um SKU IBIAG. **Não são imagens geradas**. Fonte e descrição aparecem em cada card. `form-credits.json` registra a página comercial e o arquivo original; não atribui licença Creative Commons às fotografias comerciais. `credits.json` mantém as licenças e créditos originais do Commons para castanhas e guaraná em pó. Fotos antigas de frutas permanecem como arquivos históricos no repositório, sem associação ou inclusão no build do catálogo.

Os arquivos são locais, publicados pelo build em `/static/media/`; não há consulta ao Firecrawl nem dependência de imagens externas durante a navegação. A apresentação usa `object-fit: contain` para preservar a fotografia inteira. Se não houver foto compatível, o card informa **Foto desta apresentação ainda não disponível**. Isso inclui várias apresentações do portfólio; a cobertura fotográfica não está completa.

A URL HTTPS cadastrada em **Gestão → Produtos → Editar → Imagem / URL** tem prioridade. Ela permite registrar uma fotografia específica do fornecedor/lote. Se falhar, há uma tentativa de fallback compatível; se essa imagem também falhar, é exibida a mensagem de ausência. A correção não reimporta o portfólio, não altera produtos, preços, fornecedores ou arquivos de produção.

## Validação

Fixture `portfolio-names.json` contém os 165 nomes distintos das abas IBIAG/Orgânico/KW da tabela do usuário, com a linha original (sem preços ou fornecedores). Testes conferem a classificação de todos os nomes, cliques reais nas cinco abas e no seletor, retorno a Todos, distinção caju/suco/castanhas e erro/repetição de carregamento. Testes de imagem conferem correspondência por apresentação, prioridade da URL cadastrada e falhas. O fluxo Chromium usa base isolada, decodifica as 14 imagens, percorre abas e seletor com categorias importadas e verifica que apresentações sem foto não herdam fruta/extrato de outra forma. Esse teste não comprova a interação de uma sessão autenticada na produção.
