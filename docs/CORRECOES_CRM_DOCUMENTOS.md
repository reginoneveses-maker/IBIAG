# CRM, documentos e pastas — correção dos fluxos auditados

As mudanças complementam a versão main 1fe5bb7; preservam a lixeira e a classificação existentes.

## Comportamento

- Trade Intelligence mostra site, fonte da empresa, contatos do decisor e fonte do decisor separadamente. Após incluir um candidato, “Ver empresa no CRM” abre a ficha pelo ID retornado. Pesquisas antigas não substituem resultados da pesquisa ativa.
- O CRM abre a empresa indicada por `?lead=ID`, mostra links e documentos e mantém o contexto ao recarregar. Interações e documentos carregam independentemente sem mostrar histórico da empresa anterior.
- A Central permite criar pastas vazias e subpastas, navegar, escolher o destino do upload e mover documentos por “Mover / classificar”. Classificações por área, produto, documento e certificado continuam disponíveis. Os vínculos com empresa são preservados em `lead_id`.
- `POST /api/documents/upload` recebe arquivo e metadados juntos, valida os vínculos antes de armazenar e remove o objeto se o cadastro falhar. Upload individual limitado a 50 MB. A lixeira continua recuperável e não apaga o arquivo.
- Documentos publicados são compartilhados com a equipe autenticada IBIAG; uploads sem cadastro e documentos na lixeira só são acessíveis ao remetente ou administrador. Não é um sistema multiorganização.
- Ofertas rejeitam referências inexistentes ou documentos na lixeira. Restaurar o documento preserva os vínculos existentes. O agregador de documentos da oferta omite documentos na lixeira.
- Paginação e busca documental no backend não dependem do antigo limite de 10 mil arquivos. A Central carrega as páginas para manter sua navegação por classificação.

## Endpoints adicionais

- `GET /api/leads/{id}`
- `GET /api/documents/page`: `category`, `section`, `search`, `lead_id`, `trash`, `skip`, `limit`
- `GET /api/document-folders`
- `POST /api/document-folders`: `{ "path": "Produtos/Acerola/COA" }`
- `POST /api/documents/upload`: multipart `file` e `metadata` JSON

Pastas são organização lógica persistida; os arquivos não precisam mudar de chave em GridFS/S3.
Os caminhos importados anteriormente aparecem na navegação, sem migração destrutiva.
Na inicialização é criado um índice único esparso para a chave de descoberta de novos leads.

## Validação reproduzível

```
TEST_MONGO_URL=mongodb://localhost:27017 python -m pytest -q backend
cd frontend
CI=true DISABLE_EMERGENT_OVERLAY=true npm test -- --watchAll=false --runInBand
CI=true npm run build
npx playwright install chromium
npm run test:e2e
```

O teste de navegador inicia um servidor local isolado com banco/armazenamento em memória e respostas fixas de descoberta; não usa credenciais de produção, não consome o provedor e não altera o acervo real.
O teste HTTP com MongoDB real usa banco descartável e GridFS real, verifica os bytes após download e a pasta após nova consulta.
Os testes de browser e componentes entram no workflow, além dos testes Python e build.

Resultado local: 60 testes Python aprovados com MongoDB real, 6 testes de interação React aprovados e percurso Chromium completo aprovado.
A busca externa ao vivo e o deployment de produção exigem validação no ambiente publicado; estes testes não comprovam credenciais, saldo ou disponibilidade do provedor.

## Retorno de uso real — 3 de outubro

- Adicionar ao CRM consulta automaticamente a página inicial e um link de contato publicado no mesmo domínio via Firecrawl. Nome da empresa, e-mail, telefone e país só são aceitos quando presentes no texto da fonte. Diretórios não são tratados como a empresa. A operação informa campos ausentes e indisponibilidade; não inventa contatos.
- O país extraído da fonte é o endereço publicado da empresa, não uma prova de atividade de compra no país pesquisado. Contatos gerais não são apresentados como contatos pessoais do decisor.
- A ficha mostra o telefone geral e fontes dos contatos; “Buscar / atualizar dados da empresa” completa cadastros anteriores. Contatos existentes são preservados.
- Criar pasta abre automaticamente o caminho criado. O caminho fica na URL, sobrevive à recarga e é mostrado como destino do upload. Mover documento abre o novo destino.
- A prévia identifica a assinatura PDF/PNG/JPEG/GIF/WebP. PDF usa o leitor nativo, com abrir em nova aba e baixar; o iframe sandboxado que bloqueava plugins foi removido. HTML, SVG e arquivos de escritório não são executados na prévia e oferecem download. Políticas locais do navegador ainda podem impedir seu leitor PDF.
- Novos testes cobrem extração com fonte, contatos não publicados, falha do provedor, enriquecimento de cadastro existente, criação de pasta e estrutura da prévia PDF. O percurso de navegador verifica a prévia e o destino após recarga.

## Pesquisa em vários mercados

Trade Intelligence permite selecionar Europa ou Ásia, ou digitar países separados por vírgula/ ponto e vírgula (Alemanha, Espanha, Portugal; códigos DE, ES, PT também aceitos). Regiões seguem o catálogo de países e territórios da ONU M49, consultado em 03/10/2026: https://unstats.un.org/unsd/methodology/m49/overview/ . Europa inclui 51 entradas e Ásia 50; não são contagens de Estados soberanos.

GET /api/buyer-discovery/markets fornece o catálogo. POST /api/buyer-discovery/search-jobs inicia uma tarefa autenticada; GET /api/buyer-discovery/search-jobs/{id} informa resultados e progresso; POST /api/buyer-discovery/search-jobs/{id}/cancel interrompe consultas ainda na fila. Há até três consultas simultâneas, uma pesquisa ativa por usuário e dez resultados por país na interface. Cada país falha independentemente; os demais resultados são preservados. As consultas em andamento terminam após solicitar interrupção. O identificador na URL permite recuperar resultados ao recarregar; reinício do servidor marca pesquisas inacabadas como interrompidas, permitindo iniciar outra.

Resultados identificam o mercado pesquisado e têm filtro por país. O CRM recebe o país individual, código e search_country, nunca o nome da região como país. O enriquecimento pode descobrir um país de endereço diferente do mercado pesquisado. Provedores externos são simulados nos testes; disponibilidade e qualidade dos contatos dependem das fontes reais.

## Limpar e repetir a pesquisa

O botão Limpar pesquisa remove produto, países, região, resultados, filtro, links CRM, erros e identificador da tarefa na URL. Editar produto, países ou região também invalida os resultados anteriores. Respostas atrasadas de pesquisa/polling/CRM não podem repor o estado antigo. Pedidos individuais usam AbortController; tarefas amplas recebem cancelamento da fila. Se a criação de uma tarefa responder depois de limpar, essa tarefa também é cancelada. O backend aceita replace_previous=true para cancelar exclusivamente as tarefas do próprio usuário antes de iniciar outra, evitando bloqueio pela tarefa cancelada; consultas já em execução podem terminar, mantendo o limite global de concorrência.

Diretórios reconhecidos, incluindo Europages, são identificados como fontes em diretório, sem afirmar que o link é o site oficial da empresa. Seus contatos de operador não são usados pelo enriquecimento. A classificação cobre os domínios conhecidos; outras fontes continuam exigindo validação. Busca não usa cache próprio de resultados: produto e país atuais são enviados ao provedor em cada consulta.
