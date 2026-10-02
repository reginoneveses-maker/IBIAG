# Backup e recuperação IBIAG

O backup completo inclui as coleções do banco, usuários, metadados, índices e os arquivos PDF armazenados em GridFS. Usa Extended JSON canônico para preservar ObjectId, datas e bytes. O formato antigo `jsonl.gz` baseado em `str(value)` não permite recuperação confiável dos blocos binários e é recusado pelo restaurador novo.

## Download administrativo

Administradores podem usar **Baixar backup completo** no menu. O servidor gera e confere o arquivo antes de entregá-lo; dados não são apagados. Pedidos, compras e ajustes de estoque ficam temporariamente bloqueados durante a geração. Evite importar documentos e alterar outros cadastros enquanto o backup é gerado, pois MongoDB standalone não oferece snapshot entre todas as coleções.

## Verificação e restauração

```bash
python backend/backup.py --verify IBIAG_backup.jsonl.gz
python backend/backup.py --restore IBIAG_backup.jsonl.gz --target-db ibiag_recuperacao
```

A segunda chamada é uma simulação. Para restaurar efetivamente, configure `RESTORE_MONGO_URL` fora do código e acrescente `--execute`. O banco de destino deve estar vazio e ser diferente do banco de origem e de `DB_NAME`. Não há exclusão de dados. Recuperação de produção exige validação em banco isolado antes de mudar o banco utilizado pela aplicação.

A conferência valida manifesto e contagem de registros, sequência e tamanho dos blocos GridFS. A recuperação preserva índices e coleções vazias. O teste automatizado compara bytes, identificadores e datas após restaurar os dados de teste.

## Cópia externa diária

`.github/workflows/backup.yml` está programado para 03:17 UTC. A programação por si só não comprova um backup executado. O envio requer estes Secrets no repositório:

- `IBIAG_MONGO_URL`, `IBIAG_DB_NAME`
- `IBIAG_BACKUP_S3_BUCKET`
- `IBIAG_BACKUP_S3_ACCESS_KEY`, `IBIAG_BACKUP_S3_SECRET_KEY`
- `IBIAG_BACKUP_S3_ENDPOINT`, `IBIAG_BACKUP_S3_REGION` quando exigidos pelo destino

Variáveis opcionais: `IBIAG_BACKUP_S3_PREFIX` (padrão `ibiag/database`), `IBIAG_BACKUP_RETENTION_DAYS` (padrão 30). Campos vazios usam os padrões. O upload verifica tamanho e SHA-256 armazenado nos metadados remotos. Exclusão por retenção permanece desativada por padrão e exige `BACKUP_PRUNE_ENABLED=true`.

Não coloque credenciais no repositório ou em mensagens. A cópia externa e a recuperação de dados reais só devem ser consideradas verificadas após uma execução bem-sucedida e um teste isolado com o arquivo gerado.
