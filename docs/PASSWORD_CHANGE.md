# Troca autenticada de senha

O menu **Alterar senha** permite a qualquer conta ativa trocar a própria senha.
Exige senha atual, nova senha e confirmação na tela. O servidor exige nova senha
de no mínimo 8 caracteres, no máximo 72 bytes UTF-8, sem NUL, e rejeita repetição
da senha atual. Campos extras e entradas inválidas retornam erro de autenticação
genérico, sem repetir senhas ou detalhes internos.

`POST /api/auth/password` exige sessão válida. A confirmação da senha atual tem
contador compartilhado no MongoDB, por conta/janela de 15 minutos, limitado a cinco
tentativas, inclusive entre sessões e workers. O contador não contém identificador
em texto nem senha e usa o TTL existente de login. Não basta roubar um token para
alterar a senha sem saber a credencial atual.

A gravação compara hash e geração lidos, altera o hash e incrementa a geração
atomicamente. Alteração concorrente ou suspensão impede sobrescrever o estado
mais recente. Todos os tokens anteriores ficam inválidos; a tela limpa os campos
e encerra a sessão local confirmada. Senhas não são persistidas no navegador.
Uma resposta de rede perdida pode deixar a alteração aplicada sem confirmação;
nesse caso é necessário verificar o acesso com novo login.

O bootstrap administrativo agora é somente criação: se o e-mail já existir, não
substitui senha, papel, suspensão ou geração, inclusive após um reinício. O índice
único antecede a criação e o upsert concorrente não modifica conta existente.
Mudar `ADMIN_PASSWORD` deixou de redefinir uma conta existente. A senha corrente
do banco permanece válida; não há alteração automática de credenciais na publicação.

Testes HTTP são repetidos com MongoDB descartável; testes da tela/contexto cobrem
limpeza dos campos/sessão e respostas atrasadas. O navegador troca a senha de um
admin sintético, nega replay/senha antiga e aceita novo login. Não há acesso a
senhas/contas de produção nem envio de mensagens, custos externos ou backups.

Isto não implementa recuperação de senha esquecida nem recuperação emergencial
de administrador: esses fluxos precisam identidade e canal autorizados. Os demais
seeds/migrações de startup continuam exigindo revisão antes de publicar.
