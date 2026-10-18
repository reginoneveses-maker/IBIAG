# Permissões dos dados empresariais

Nesta etapa, o papel `user` atende CRM e tarefas próprios e consulta de materiais
compartilhados. O papel `admin`, conferido no banco a cada requisição, administra
os dados empresariais. Não há novas contas, promoções nem migrações automáticas.

| Área | Usuário comum | Administrador |
|---|---|---|
| CRM/tarefas | Próprios | Equipe e atribuições |
| Catálogo, fornecedores e materiais técnicos compartilhados | Consulta | Consulta e alteração |
| Pedidos, compras, NF-e, contratos, financeiro e indicadores de gestão | Sem acesso | Consulta e alteração |
| Preços persistidos e gestão de ofertas | Sem acesso | Consulta e alteração |
| Calculadora sem persistência | API disponível | Disponível |
| Documentos de CRM | Próprios, sem publicação corporativa | Equipe e publicação |
| Documentos financeiros, societários ou com classificação desconhecida | Sem acesso | Consulta e administração |

O dashboard comum omite os valores empresariais e não consulta o financeiro.
As páginas de gestão restritas mostram uma mensagem de acesso, sem montar os
componentes que carregam os dados. A API mantém a autorização mesmo se a tela
ou o JWT forem adulterados. Tokens antigos não mantêm privilégios removidos do banco.

Arquivos financeiros/legais e anexos de contratos/lançamentos não ficam públicos
para a equipe por terem sido enviados originalmente pelo usuário ou por haver
um segundo vínculo genérico ao mesmo arquivo. Classificações legadas conhecidas
são consideradas; classificações desconhecidas ficam administrativas por padrão.

Este é um padrão conservador para os dois papéis existentes. Permissões futuras
por função ou workspace precisam de regras explícitas e testes antes de liberação.
Antes de publicar, revisar os papéis reais das contas da empresa e seus fluxos:
uma conta comum que usava gestão empresarial precisará de permissão adequada.
Nenhum usuário foi alterado nesta implementação.

Este PR é empilhado na branch de integração para revisar apenas esta política.
O workflow foi habilitado também para PRs destinados à branch de integração,
sem adicionar agendamento ou executar backup. Não publicar automaticamente.
