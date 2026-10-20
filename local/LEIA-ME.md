# IBIAG no Windows — primeira instalação local

Este pacote reutiliza CRM, fornecedores/produtos/ofertas, calculadora, cotações, pedidos, documentos/pastas, financeiro, Invoice e Packing List do candidato de desenvolvimento. As funções novas de amostras, leitura por IA, rastreabilidade por lote e Siscomex do esboço ainda não foram implementadas por este pacote.

## Abrir

1. Instale/abra o Docker Desktop com Linux containers. Exige Docker Engine 28+ e Compose 2.24+; o iniciador verifica versões e recusa contextos remotos. Consulte os termos do Docker Desktop aplicáveis à empresa.
2. Extraia o ZIP para uma pasta permanente no seu computador, fora de uma pasta sincronizada com terceiros. Não execute dentro do ZIP.
3. Dê dois cliques em **Iniciar IBIAG.cmd**. A primeira abertura baixa imagens/dependências e compila a interface; requer internet e pode demorar.
4. Somente na primeira abertura, informe seu e-mail e crie uma senha (12 a 72 bytes). A senha não aparece enquanto digita e não é salva em texto; fica somente o hash.
5. O navegador abre em http://127.0.0.1:8787. Um atalho IBIAG é criado na área de trabalho quando permitido. Não é preciso repetir blocos de PowerShell.

Não execute o pacote como administrador se o Docker Desktop já estiver disponível para seu usuário. Caso o Windows marque o arquivo como baixado, confira a origem antes de desbloquear pelo menu Propriedades. O iniciador aplica a política Bypass somente ao processo que executa este arquivo, não muda a política do computador.

## Onde ficam os dados

Banco e arquivos enviados usam MongoDB/GridFS no volume Docker **ibiag-local_mongo_data**, no disco deste computador. Não ficam dentro da pasta de código. Fechar o navegador não encerra o serviço. **Parar IBIAG.cmd** encerra os containers mantendo o volume; a próxima abertura conserva os registros.

As três chaves técnicas aleatórias ficam em **%LOCALAPPDATA%\\IBIAG\\Local\\.env.local**, com acesso limitado ao usuário Windows. Não são senhas da Railway ou da sua conta IBIAG. Não envie esse arquivo por chat/e-mail ou para GitHub. Administradores do computador continuam tendo capacidade de acesso ao disco/Docker; a proteção depende também da conta Windows.

Não apagar o volume nem usar comandos Docker com remoção de volumes. Reset de fábrica/desinstalação do Docker, perda do disco ou exclusão manual podem remover os dados. Persistência no computador não é cópia de segurança externa. Nenhum backup recorrente foi ativado.

## Isolamento

Somente a interface publica uma porta, vinculada a 127.0.0.1. Banco e backend não publicam portas. O banco exige autenticação; a aplicação usa usuário readWrite apenas no banco ibiag_local, sem usuário root. Backend e navegador usam a mesma origem. Cadastro público, documentação de API e descoberta paga ficam desativados. Não são copiadas chaves de serviços online.

O pacote não instala nem altera serviços Railway, não reinicia o Mongo remoto e não importa os dados atuais. Começa com uma base local vazia e conta própria, sem cadastros demonstrativos. Importar seu Excel/arquivos pode ser feito após conferir o funcionamento. A cópia da Railway é assunto separado.

## Uso

Login → cadastre/importa empresas → fornecedores/produtos/ofertas → cálculo salvo → cotação → pedido → documentos → embarque/recebimento. Aprovações são explícitas. Nunca use confirmação de venda ou recebimento financeiro apenas para testar com dados reais.

Siscomex, pesquisas de mercado, e-mail e outros serviços externos exigem conexão e configuração própria. Não estão integrados automaticamente. O núcleo local não precisa da Railway em execução. Recursos/fontes/imagens ainda apontados a sites externos podem ficar indisponíveis sem internet; sua consolidação para uso integral offline requer revisão específica.

## Problemas

- Docker não encontrado: instalar e abrir Docker Desktop; repetir o clique.
- Porta 8787 ocupada: não encerre programas desconhecidos; identifique o aplicativo antes de mudar a configuração.
- Dados existem e arquivo de configuração sumiu: o iniciador bloqueia a geração de outras chaves; recuperar a configuração original.
- Senha esquecida: não edite o .env.local nem recrie o banco. A recuperação de acesso existente no projeto exige execução administrativa controlada.
- Erro de inicialização: a janela permanece aberta com mensagem; não apaga dados nem repete migração.

## Futuro acesso de funcionário

A lógica e o banco continuam separados da interface. Migrar para uma máquina central exigirá transferência validada do volume/dados, HTTPS, acesso individual e revisão de permissões. Não libere a porta no roteador nem troque 127.0.0.1 por 0.0.0.0 como atalho. Não sincronize o diretório de um Mongo ativo via OneDrive.

## Validação

A pipeline específica deve comprovar: build real dos containers, autenticação, criação de usuário/CRM, upload e download privado, permanência dos dados após recriar containers, bloqueio de cadastro público/docs, porta restrita e parsing do iniciador no PowerShell. O resultado da execução fica no PR; preparação de teste não significa que ele passou. A instalação no computador do usuário ainda precisa ocorrer.
