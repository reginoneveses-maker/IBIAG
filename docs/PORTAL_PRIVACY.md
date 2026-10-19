# Privacidade do portal — telemetria removida

A auditoria de código/histórico encontrou o carregamento incondicional de um script remoto da plataforma de geração e a inicialização de analytics com configuração de gravação de sessão no HTML do portal. Esses scripts executavam no mesmo contexto das telas autenticadas. Não foi investigado o conteúdo remoto, acessada a conta de analytics ou comprovada coleta/vazamento de informações.

O HTML deixa de carregar ambos e de criar a variável global de analytics. Também remove o handler inline que ocultava um tipo de erro de execução. Os bundles locais da aplicação continuam sendo gerados pelo CRA; as dependências e ferramentas de desenvolvimento não foram atualizadas nesta mudança.

Dois testes verificam o shell sem scripts executáveis/handlers inline. O teste completo de navegador bloqueia solicitações externas antes da primeira navegação, registra somente o tipo de recurso (não URL/valor), e falha se houver tentativa de script/fetch/XHR externa durante os fluxos. Confere também ausência da variável global de analytics ao fim. Fontes/imagens/CSS externos ficam bloqueados no teste; fotografias locais e fluxos devem funcionar sem provedores reais. Os testes com navegador/APIRequest usam apenas fixtures locais.

Essa política de rede existe no teste, não é um firewall da aplicação publicada. Fontes externas e imagens/links comerciais ainda podem existir no produto. Nenhuma configuração do fornecedor, dado anterior, credencial de produção ou serviço pago foi alterado. Não há prova de remoção em produção antes de publicar e validar o candidato. CSP, política de dependências de frontend e decisão operacional sobre integrações externas permanecem separadas desta correção.
