# Recuperação operacional de acesso

## Escopo e autoridade

Recuperação de senha esquecida de conta comum e emergência de administrador por operador que já administra o servidor e o banco. Não é um endpoint público, recuperação por e-mail, concessão de acesso remoto ao servidor, MFA ou prova automática de identidade. Não depende de serviço pago, links de redefinição, segredo compartilhado de emergência ou redefinição no startup. Troca autenticada na interface continua disponível separadamente.

Somente o responsável autorizado pela IBIAG pode executar, depois de conferir a identidade do titular por canal confiável já conhecido. Nome/e-mail enviado por desconhecido não comprova titularidade. Caso de administrador requer o responsável pela operação. A segurança desse procedimento depende da segurança do acesso administrativo ao host/banco; o comando não protege contra operador ou servidor comprometido. Não ativar acesso SSH ou abrir MongoDB publicamente para usá-lo.

## Execução revisável

Usar a versão testada no servidor correto, com o ambiente MONGO_URL/DB_NAME já configurado. O comando não carrega .env, não importa server, não roda startup e não imprime URI, conta, senha ou hash. Confirmar ambiente/alvo no painel administrativo autorizado, sem copiar dados pessoais para tickets públicos. O case-id é referência não confidencial da verificação; nunca incluir nome, e-mail, documento ou credencial nele.

Verificação sem gravação, sem prompts de senha:

```sh
python recover_access.py --account-id ID_DA_CONTA --expected-role user --reason lost-password --case-id CASO_INTERNO
```

No checkout, usar backend/recover_access.py. No container, o script está no diretório /app. Para emergência de administrador, usar expected-role admin e reason admin-emergency. A razão lost-password também exige papel explícito e correspondente; nunca promove conta.

Aplicação intencional no terminal privado do operador:

```sh
python recover_access.py --account-id ID_DA_CONTA --expected-role user --reason lost-password --case-id CASO_INTERNO --apply
```

Exige stdin/stdout/stderr interativos, confirmação digitada RECUPERAR seguida do ID exato e duas entradas ocultas iguais. Nunca passar senha em argumento, variável de ambiente, arquivo, pipe, chat ou ticket. Se getpass não puder ocultar, aborta antes do fallback com eco. Preferir que o titular digite a nova senha no terminal privado autorizado; qualquer transmissão entre operador e titular precisa de canal confidencial acordado, não fornecido por este comando. Em terminal gravado, a política da gravação precisa ser avaliada pelo operador.

Aplica a mesma política de senha da aplicação: pelo menos oito caracteres, no máximo 72 bytes UTF-8, sem NUL e diferente da atual. Suspensão não é removida. Papel/identidade/dados comerciais não mudam. Conta ausente, papel inesperado, ID/e-mail duplicado, identidade/generation inválida e histórico inconsistente/cheio são recusados. Não faz upsert ou limpeza de legado. Duplicidades são verificadas no momento da leitura; a manutenção exige controle de escritores administrativos concorrentes, não substitui índice único global para IDs.

## Atomicidade, auditoria e resultado

A gravação compara _id, ID, e-mail, hash anterior, geração, papel, estado e histórico lidos antes dos prompts. Rotação, suspensão ou alteração concorrente impedem sobrescrita. Uma única gravação altera hash/data, incrementa session_version e acrescenta evento sem credenciais (UUID, data, host-operator, razão e referência). A conexão CLI exige confirmação majority e journal. Revoga todos os JWTs anteriores, inclusive legados; requer novo login. Trabalho já autorizado/em execução não é cancelado retroativamente.

O histórico embutido permite até 100 recuperações e recusa a próxima; não apaga eventos para liberar espaço. Não é log externo imutável nem prova da identidade pessoal do operador. Arquivamento/retention e auditoria independente são decisões operacionais separadas. Não há remoção automática de rate limits, contas suspensas ou registros comerciais.

Falha/interrupção/timeout pode deixar uma gravação aplicada sem confirmação. O erro é estático e não imprime exceção interna; verificar por novo login antes de repetir, sem redefinir novamente por tentativa automática. Depois, conferir senha antiga/token anterior recusados e nova senha aceita; registrar somente resultado e referência interna, nunca credenciais.

## Evidência e liberação

Testes de recuperação/negação/replay/concorrência repetem em mock e MongoDB descartável real. CLI testa dry-run, TTY, confirmação, fechamento do client e mensagens redigidas. Não foi executado contra conta ou banco publicado. Este procedimento entrega recuperação manual operacional; recuperação pública, e-mail e MFA não foram ativados. A validação de um caso autorizado na hospedagem e a segurança do acesso administrativo real continuam necessárias antes de declarar a etapa 1 encerrada.

Referências oficiais consultadas: [Python 3.12 getpass](https://docs.python.org/3.12/library/getpass.html) e [PyMongo 4.6.3 MongoClient](https://pymongo.readthedocs.io/en/4.6.3/api/pymongo/mongo_client.html). O fallback de getpass pode ecoar entradas; por isso o warning é fatal antes da leitura alternativa. Majority/journal exigem suporte/configuração efetiva do servidor, não comprovam persistência do volume ou recuperação de desastre.
