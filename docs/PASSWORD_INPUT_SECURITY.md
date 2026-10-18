# Validação de senhas no servidor

O bcrypt fixado no projeto trunca entradas após 72 bytes. O servidor agora
rejeita senhas acima desse limite, em UTF-8, antes da verificação ou criação do
hash. Não há truncamento silencioso, remoção de espaços nem normalização Unicode.
Caracteres nulos e senhas vazias também são rejeitados.

Os cadastros público e administrativo usam a mesma regra: no mínimo 8 caracteres
e no máximo 72 bytes. O cadastro público continua desabilitado por padrão.
Login de senhas antigas com menos de 8 caracteres continua permitido, para não
forçar redefinição indiscriminada. Isso não elimina a necessidade de política de
senhas mais fortes, recuperação de conta e autenticação multifator.

Os helpers de hash/verificação aplicam os mesmos limites, inclusive fora de HTTP.
Uma senha administrativa de bootstrap nova ou atualizada precisa obedecer à regra;
entradas inválidas falham sem criar um hash truncado. Antes de publicar, validar
a política do segredo configurado na hospedagem sem exibir seu valor.

Hashes existentes originalmente criados com mais de 72 bytes não permitem
recuperar a senha completa. Essas contas exigem redefinição controlada; não
interpretar o prefixo truncado como uma senha nova nem alterar dados automaticamente.

Respostas 422 de autenticação são genéricas e não repetem o corpo enviado.
As mensagens de outros endpoints mantêm seu contrato atual. Não foi feita uma
auditoria geral de todos os logs ou campos confidenciais do sistema.

O teste HTTP de cadastro também revelou que o driver MongoDB acrescenta `_id`
ao dicionário inserido. Esse identificador interno agora é removido da resposta,
junto com o hash, evitando falha de serialização após criação bem-sucedida.

Cobertura: limite ASCII e multibyte, espaços, caracteres nulos, reprodução do
truncamento, entradas inválidas sem hash/gravação, redaction da resposta, cadastro
e login reais no app isolado e compatibilidade com senha antiga curta.
