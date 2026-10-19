# Segredos fora do contexto Docker

Os Dockerfiles copiam backend/ e frontend/. A proteção do Git não determina quais arquivos um build Docker local envia/copia. Sem .dockerignore, arquivos locais ignorados pelo Git, como .env, poderiam entrar nas camadas da imagem. Não foi comprovado que alguma imagem publicada tenha incluído segredo; a mudança elimina essa possibilidade para os padrões cobertos em novos builds com contexto na raiz.

O .dockerignore na raiz agora exclui arquivos de ambiente, chaves/certificados privados, configurações locais de registry/cloud/SSH, JSONs de credenciais/tokens, metadados Git, caches, gravações, logs, backups e fixtures de teste. Preserva fontes, manifests, Dockerfiles, configuração nginx e scripts operacionais necessários. Builds existentes devem usar a raiz do repositório como contexto, conforme os COPY atuais; Dockerfile-specific ignore files futuros precisam da mesma política.

Não colocar segredo em argumento de build, REACT_APP_*, Dockerfile ou código fonte. O único argumento atual do frontend é a URL pública do backend. Segredos de runtime continuam na hospedagem; dependências privadas futuras devem usar secret mounts, não COPY de .npmrc/credenciais. Nomes arbitrários de arquivos com segredos não são detectados por padrão/glob: revisão de código, auditoria de histórico e política de secrets continuam necessárias.

O teste usa o matcher real do Docker e um COPY para imagem FROM scratch, com network=none, sem executar container ou instalar software no build. Em contexto temporário, cria apenas canários sintéticos e copia uma amostra explícita de arquivos públicos da aplicação; exporta a imagem para conferir ausência de 26 caminhos privados e presença dos dez arquivos necessários. Nunca lê .env/credenciais reais. Remove somente imagem/container com UUID criados pelo teste. Não constrói/publica as imagens completas da aplicação nem valida imagens antigas/camadas já distribuídas.

Localmente o teste depende de Docker; sem o binário ele é ignorado. O runner backend do CI possui Docker para o MongoDB descartável e precisa executar esse teste, sem skip, antes de integrar. Nenhum build/deploy da hospedagem, segredo, volume ou backup de produção é alterado.

Referências oficiais: [Build context e dockerignore](https://docs.docker.com/build/concepts/context/) e [Build secrets](https://docs.docker.com/build/building/secrets/).
