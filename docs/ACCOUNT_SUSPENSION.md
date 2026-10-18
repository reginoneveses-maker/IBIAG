# Suspensão e reativação de contas

Administradores encontram **Acesso da equipe** no menu. A tela lista contas e
permite suspender/reativar contas de papel `user`, após confirmação. Não altera
senhas, papéis ou responsáveis e não apaga dados. Não permite suspender a própria
conta administrativa nem outro administrador; a operação atômica no banco inclui
o papel no filtro para impedir contornar essa restrição por mudança concorrente.

`PATCH /api/auth/users/{id}/active` exige admin e um booleano JSON estrito. Campos
adicionais, como papel e versão de sessão, são rejeitados. O servidor registra
último ator/data e incrementa atomicamente a geração de sessões. Não há histórico
integral de auditoria neste controle.

Login recusa contas suspensas com a mesma resposta de credencial inválida. Cada
requisição autenticada verifica o estado e a geração atuais no banco. Todos os
tokens anteriores são recusados, inclusive depois da reativação. Contas e tokens
legados sem versão usam geração zero até a primeira mudança. Repetir uma alteração
também incrementa a geração, preservando a invalidação em concorrência. Nenhuma
migração ou rotação de segredo é necessária.

Tarefas/leads existentes permanecem com o responsável original; um admin pode
revisar e transferir. Novas atribuições a contas suspensas são recusadas e a tela
retira essas contas das opções. A suspensão não desfaz requisições já autorizadas
em andamento, não cancela jobs antigos nem remove arquivos do dispositivo.

Validação: sete testes HTTP repetidos com MongoDB descartável no CI, quatro testes
de interação da tela e fluxo no navegador que suspende uma conta sintética,
nega login/replay, reativa e exige novo login. Os testes não alteram contas reais.
Recuperação de senha e procedimentos de emergência administrativos são controles
separados ainda pendentes; o bootstrap existente precisa revisão antes do deploy.
Nenhuma conta ou configuração de produção foi alterada por esta implementação.
