# Limites de processamento de CSV/XLSX

Um único leitor atende CRM, portfólio e restauração de comissões. O CRM usa a
primeira linha como cabeçalho; o portfólio preserva a aba IBIAG e a terceira linha.
Validação termina antes da criação de DataFrame e antes de qualquer gravação,
substituição do catálogo ou alteração de comissões. Arquivos recusados não são
truncados nem parcialmente aplicados por este leitor. As validações de negócio
posteriores continuam separadas.

## Orçamentos por arquivo

- Até 10.000 linhas de dados, 128 colunas e 250.000 células de tabela incluindo
  cabeçalhos. O orçamento de grade evita expansão de linhas esparsas em DataFrame.
- Até 32.767 caracteres por célula e 8 Mi caracteres de texto total.
- Permanecem 50 MiB brutos, 100 MiB de expansão ZIP e 2.000 entradas do controle
  anterior. Cada parte XML/relações do XLSX tem no máximo 16 MiB.
- Até 20 abas, 1 milhão de elementos XML e profundidade 64; até 10 mil elementos
  no XML de estilos, 20 mil em outras partes de metadados e 100 mil strings
  compartilhadas. Todo o pacote é examinado, inclusive abas/partes não utilizadas.

Excesso retorna 413 com orientação para dividir em lotes. Arquivo inválido,
cabeçalho duplicado/ambíguo, DTD/entidades/referências externas ou pacote ambíguo
retorna 400 estático, sem valores, caminhos ou exceções de bibliotecas. Arquivos
XLS binários antigos devem ser convertidos para XLSX ou CSV UTF-8; não havia
dependência de leitor XLS no projeto. A tela agora anuncia apenas os formatos
suportados. Não há limite novo para a quantidade de empresas já armazenadas.

## Antes de alocar a tabela

CSV passa por contagem de registros, campos e tamanho de campos respeitando
aspas, delimitadores citados e quebras internas. Isso antecede csv.reader, para
não criar uma lista enorme com milhões de colunas vazias. Aceita UTF-8/BOM,
vírgula, ponto e vírgula e tabulação; telefones textuais mantêm zeros iniciais.

XLSX passa por inspeção incremental com defusedxml de todas as partes XML e
relações. Os limites verificam coordenadas reais de linhas/células e ignoram
dimensões declaradas falsas. DTD, entidades e referências externas são proibidas.
Só depois abre openpyxl em modo read_only, data_only e keep_links=False; fecha
o workbook explicitamente. Fórmulas não são calculadas: usam valores em cache,
quando presentes. A grade final também é verificada antes do pandas.

Referências oficiais:
- https://openpyxl.readthedocs.io/en/stable/optimized.html
- https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html
- https://pypi.org/project/defusedxml/0.7.1/

## Evidência e limites da comprovação

Doze testes do leitor incluem CSV/XLSX de 2.000 empresas, aspas/encoding/zeros,
limites antes dos leitores, dimensões falsas e coordenadas distantes, strings
compartilhadas/rich text, DTD e caminhos ambíguos. Cinco testes HTTP são repetidos
com MongoDB descartável no CI: importação/deduplicação/isolamento, portfólio e
comissões, rejeição sem alterar dados existentes, erros genéricos e permissões.

Não é antivírus, limite de ingresso multipart/proxy, quota global de memória/CPU,
isolamento de processo nem validação integral dos dados comerciais/fiscais. Células
com fórmulas dependem do cache salvo pelo Excel; não há execução de macros ou
consulta de links externos. Novos limites exigem validação com amostras autorizadas
antes de publicar; arquivos com muitas abas, estilos ou dados esparsos podem
precisar ser simplificados/divididos. Somente dados sintéticos foram usados.
Nenhuma importação de produção, serviço pago, pesquisa externa ou backup foi
executado por esta alteração.
