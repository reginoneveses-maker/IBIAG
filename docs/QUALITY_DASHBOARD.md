# Painel de qualidade documental

Consulta administrativa em /gestao/qualidade, API GET /api/gestao/quality. Reutiliza os certificados de fornecedor e os documentos ativos explicitamente classificados como Ficha Técnica, COA / Laudo, Certificado ou FISPQ / SDS. Não modifica dados e não cria coleção nova.

O painel mostra vencimento e antecedência configurada nos certificados, ausência de validade/anexo, datas inválidas ou invertidas, vínculos ausentes/ambíguos e cadastro sem título/nome. O vencimento hoje não é tratado como vencido; entra em vencimento próximo quando a antecedência cadastrada permite. Antecedência deve ser inteiro de 0 a 365; valor inválido gera conferência cadastral, sem correção automática.

Datas usam America/Fortaleza. Documentos da Central não recebem validade inferida de nome, OCR ou conteúdo. Certificados cadastrados têm validade própria; documentos classificados como Certificado não herdam a validade de outro registro. Documento técnico sem vínculo pode ser um acervo legítimo: a pendência pede conferência, sem declarar descumprimento legal.

Fornecedor e produto aparecem a partir de cadastros atuais com identificador inequívoco. Nomes antigos enviados no documento não resolvem vínculos ausentes. Certificados de fornecedor não presumem cobertura de produto: filtrar por produto retorna apenas documentos técnicos desse produto. COA/Ficha Técnica/FISPQ sem produto gera alerta; Certificado documental sem produto pode ser de âmbito do fornecedor.

Anexo informado significa apenas que há referência cadastrada. O painel não abre arquivos, valida assinaturas, certificadoras, conteúdo, autenticidade, conformidade ou liberação de lote. Sem alertas de metadados não significa aprovação humana. Não aplica uma lista obrigatória de documentos a todos os produtos/países.

Filtros: origem, pendência, fornecedor e produto. Totais correspondem ao conjunto filtrado antes da paginação. Valores internos de arquivo, notas, custos e dados de CRM não são retornados. Duplicidade de identificador da mesma origem recusa a consulta; origem + identificador distingue certificado de documento. Limite de 5000 por origem e 10000 vínculos lidos; exceder gera erro explícito, nunca um total parcial. Não existe snapshot entre coleções: alterações concorrentes exigem atualização da consulta.

A tela oferece seleção de fornecedor/produto a partir dos registros retornados e links para os módulos de manutenção existentes. Não altera permissões desses módulos. A API e a rota da interface exigem administrador atual.

## Testes

Regras determinísticas de vencimento, datas, limites, vínculos e ambiguidade. Rotas HTTP com base mock e MongoDB real descartável: autorização, projeção de campos privados, ausência de escrita inclusive de trava, filtros/contagens/paginação, erros recuperáveis e excesso de registros. Testes de interface incluem respostas tardias, aplicação explícita de filtros e erros sem falso total zero. Cenário no navegador utiliza somente dados sintéticos.

## Instalação

Branch separada baseada no candidato de amostras. Não instala no Windows, reinicia contêineres, importa dados ou interfere no processo do Claude. Homologação dos dados reais e atualização local continuam posteriores à importação.
