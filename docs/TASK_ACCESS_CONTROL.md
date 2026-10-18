# Tarefas — isolamento por proprietário

Uma tarefa pertence ao usuário autenticado que a criou. O servidor gera o ID,
define `owner_id` e a data de criação, ignorando valores desses campos enviados
pelo navegador. Usuários comuns listam e alteram somente as próprias tarefas.
Administradores podem consultar, concluir, excluir e atribuir tarefas da equipe.
O papel de administrador vem do cadastro consultado pelo servidor.

Listagem, conclusão e exclusão aplicam o escopo na própria consulta ao MongoDB.
Tentar alterar uma tarefa alheia recebe o mesmo 404 de um ID inexistente.
A conclusão é uma atualização atômica: cliques concorrentes não perdem alterações.

## Tarefas existentes e responsáveis

Não há migração automática nem atribuição ao primeiro usuário que acessa.
Tarefas sem proprietário continuam preservadas e visíveis ao administrador.
Na página Tarefas, o administrador pode selecionar um responsável para cada
tarefa, inclusive as concluídas. A lista de usuários não é consultada pela
interface de usuários comuns.

`PATCH /api/tasks/{id}/owner` recebe `{"owner_id":"ID_DO_USUARIO"}`. Somente
administradores podem executar a operação; o usuário de destino deve existir.
A atualização registra `owner_updated_by` e `owner_updated_at`. Isso registra
a última atribuição, não constitui um histórico completo de auditoria.
Após transferência, o proprietário anterior perde o acesso de usuário comum.

## Validação e publicação

- Testes HTTP usam duas contas comuns e uma administrativa, sem substituir a
  dependência de autenticação: tokens reais são conferidos contra o banco isolado.
- Cobertura inclui ID/proprietário falsificados, negação de acesso entre contas,
  ausência de autenticação, legado, transferência e conclusão concorrente.
- A mesma suíte roda no MongoDB descartável do CI quando `TEST_MONGO_URL` aponta
  para um host local permitido. Nenhum banco de produção é usado nesses testes.
- Testes de interface cobrem o painel administrativo, ausência do controle para
  usuários comuns e preservação do responsável quando a API rejeita a alteração.

Antes de publicar, conferir os responsáveis das tarefas existentes e validar o
fluxo com contas de teste autorizadas. Esta mudança não altera registros existentes
até que um administrador atribua explicitamente um responsável.

Este controle cobre apenas tarefas. CRM, documentos e demais módulos ainda exigem
suas próprias regras de compartilhamento e escopo. Não estabelece isolamento geral
por workspace e não torna a etapa 1 inteira concluída.
