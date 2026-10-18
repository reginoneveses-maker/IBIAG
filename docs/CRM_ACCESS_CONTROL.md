# CRM — propriedade e acesso aos vínculos

Novos cadastros pertencem ao usuário autenticado. O servidor gera o ID e as
datas; não aceita o proprietário enviado na criação ou alteração normal.
Usuários comuns acessam somente seus cadastros. Administradores mantêm acesso
à equipe e podem atribuir um responsável no detalhe do cadastro no CRM.

`PATCH /api/leads/{id}/owner` é administrativo e valida o usuário de destino.
Registra a última atribuição e mantém o ID, para que histórico e documentos
vinculados acompanhem o acesso ao cadastro. Não constitui trilha integral de
auditoria. Registros antigos sem proprietário ficam preservados e disponíveis
ao administrador até atribuição explícita; não há migração automática.

## Rotas abrangidas

- Listagem, paginação, contagem, consulta, edição, etapa, exclusão e enriquecimento.
- Histórico de interações, com validação do cadastro antes de ler ou registrar.
- Importação de CRM e inclusão por pesquisa/Trade Intelligence. Deduplicação
  ocorre dentro do escopo autorizado; nunca retorna contatos de outro usuário.
- Métricas de CRM e contagem de documentos no dashboard.
- Anexos vinculados a leads: listagem geral/paginada, filtros, contagem, pastas,
  download, biblioteca de specs e links retornados pelas ofertas.
- Arquivos privados não podem ser republicados por meio do prefixo de upload,
  specs ou certificados. A vinculação privada ao CRM prevalece sobre esses
  caminhos, inclusive depois de uma transferência do cadastro.

Documentos gerais sem vínculo a um lead continuam compartilhados pela equipe
autenticada. As regras dos demais dados operacionais/financeiros ainda não estão
concluídas. Isto não estabelece isolamento geral por workspace.

Pastas explícitas agora registram o criador. Usuários comuns veem suas pastas
e as pastas dos documentos autorizados. Pastas antigas vazias, sem criador e
sem documento visível, ficam disponíveis somente ao administrador. Não são
apagadas. Na exclusão de um lead, anexos são preservados para administração;
usuários comuns não acessam anexos cujo lead deixou de existir.

Chaves internas de criação por pesquisa incluem o proprietário. Edição ou
transferência libera a chave anterior; o ID permanece estável. Não há mesclagem
automática entre registros de responsáveis diferentes. Isso preserva privacidade
sem atualizar ou revelar o cadastro de outra pessoa durante uma importação.

## Validação e liberação

Testes HTTP usam duas contas e uma administrativa, autenticação real do app e
banco isolado. Exercitam IDs forjados, contatos, importação, concorrência na
inclusão por pesquisa, métricas, anexos indiretos, transferência e legado. A
mesma suíte roda no MongoDB descartável do CI. Serviços de pesquisa/storage
externos são substituídos nos testes; nenhuma consulta paga é necessária.

Antes de publicar: revisar os responsáveis do CRM existente; verificar IDs
duplicados/órfãos do legado; planejar a atribuição; conferir índices e custos de
consultas de autorização com o volume real; testar transferência e anexos em
ambiente autorizado. Não integrar diretamente em produção enquanto o deploy
automático e as demais validações de liberação estiverem pendentes.
