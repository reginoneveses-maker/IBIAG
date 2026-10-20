# IBIAG local no Windows — entrega e evidência

20/10/2026, America/Fortaleza. Autorização atual do usuário: começar pela versão local com módulos essenciais, deixando funcionalidades adicionais, Siscomex e acesso de funcionário para etapas posteriores. Essa direção substitui a publicação online como primeira entrega; não autoriza apagar dados existentes.

## Pacote

PR54: https://github.com/reginoneveses-maker/IBIAG/pull/54 .
Branch local/windows-first-20261020, commit final 8ba65562c41a334568f849c9726280e594eb804d.
Base PR52, commit43715ff26f66666b130d2a67c9d18ef68a8beab4.
Download fixo: https://github.com/reginoneveses-maker/IBIAG/archive/8ba65562c41a334568f849c9726280e594eb804d.zip .

Reutiliza os módulos existentes: CRM, fornecedores/produtos/ofertas, calculadora/cálculos salvos, cotações, pedidos, documentos/pastas, financeiro, Invoice, Packing List, embarques e histórico. Não implementa neste pacote os novos módulos de amostras, IA, rastreabilidade por lote ou integração governamental do esboço.

Iniciar IBIAG.cmd e Parar IBIAG.cmd chamam o iniciador PowerShell. Requer Docker Desktop local com Linux containers, Engine28+ e Compose2.24+. Primeira abertura precisa internet para baixar imagens/dependências e compilar; não é instalador nativo independente ou pacote pré-compilado offline. A conta inicial pede e-mail e senha; somente hash da senha vai ao banco. Não existe senha padrão.

Volume Docker ibiag-local_mongo_data conserva Mongo/GridFS no computador. Chaves técnicas aleatórias ficam fora do repositório, em %LOCALAPPDATA%\IBIAG\Local\.env.local, com ACL do usuário. Atalho na área de trabalho quando permitido. Configuração ausente com volume existente bloqueia geração de novas credenciais. Parar não remove o volume. Não foi ativado backup recorrente.

A interface publica somente127.0.0.1:8787; backend/banco sem portas publicadas. Usuário Mongo da aplicação limitado a readWrite no banco local; root separado. Cadastro público, docs e descoberta paga desligados. Proxy de mesma origem não confia em cabeçalhos encaminhados. Fontes externas removidas da montagem local, com fallback do sistema.

## Evidência final

CI local39472079671: https://github.com/reginoneveses-maker/IBIAG/actions/runs/39472079671 — dois jobs concluídos com sucesso no SHA final.

- Windows job118798428546: parser PowerShell5.1 e execução do iniciador com Docker simulado em runner Windows. Confirma primeira geração de três chaves64hex, ACL protegida, URL local, parar/abrir sem rotação e ausência de remoção de volume. Não é instalação real de Docker Desktop na máquina do usuário.
- Linux job118798428201: build real das imagens e Mongo7 autenticado em volume descartável. Login real; navegador Chromium com rede externa bloqueada; CRM; upload/download GridFS privado; bloqueio de leitura anônima do banco e de privilégio administrativo do usuário da aplicação; bloqueio de CRM sem login e cadastro público; portas permitidas.
- Remoção/recriação dos containers sem remoção de volume preservou conta, senha, registro de CRM e bytes do arquivo por SHA256. Nova execução do assistente preservou a senha. Cleanup remove somente o volume aleatório da fixture CI, sem dados reais.

CI geral39472079768: https://github.com/reginoneveses-maker/IBIAG/actions/runs/39472079768 — backend/frontend com sucesso. Backend554 testes +56 subtestes aprovados; frontend334 testes/21 suítes, build e percurso Chromium existente completo. Fixture Mongo descartável e dados sintéticos.

Uma revisão intermediária47a81f0 falhou na remoção parcial do import de fontes CSS; corrigida no commit final para remover a linha inteira. O resultado final não depende dessa execução falha.

## Limites e próximo uso

Pacote ainda não instalado ou homologado no computador do usuário. Extraia em pasta permanente, tenha Docker Desktop aberto e use Iniciar IBIAG.cmd; manual local/LEIA-ME.md incluído.

Começa com base vazia, sem importar os dados da Railway. Não acessou banco real, não transferiu cópia comercial, não reiniciou/reconfigurou produção, não fez merge na main, não criou recursos pagos nem ativou backup. A preservação/recuperação do Mongo antigo continua separada e pendente.

Persistência do Docker não protege contra perda do disco, reset/desinstalação do Docker ou remoção do volume. Administradores locais podem acessar disco/Docker. Integrações externas exigem internet e configuração. Compartilhamento futuro exige migração validada, HTTPS e permissões, não apenas abrir a porta local.

A validação automatizada demonstra o pacote testado, não conclusão do escopo total do ExportHub ou do esboço comparativo.

## Correção após primeira abertura no computador do usuário

A captura do usuário mostrou erro nativo do Docker "no such volume" antes de criar a configuração. O iniciador anterior usava volume inspect com redirecionamento de stderr e ErrorActionPreference=Stop; no Windows PowerShell5.1 a ausência esperada do volume virou erro terminante. O teste anterior com função simulada não reproduzia stderr nativo.

Corrigido: usar volume ls --format '{{.Name}}', que conclui com saída vazia em instalação nova. Falha da consulta bloqueia criação de configuração; volume existente sem configuração continua protegido. Não cria volume manualmente, não apaga dados e não modifica credenciais existentes.

Pacote corrigido: commit79a885f37e605c65aaec3ca2cd5c6be208c81bae.
Download: https://github.com/reginoneveses-maker/IBIAG/archive/79a885f37e605c65aaec3ca2cd5c6be208c81bae.zip .

Validação Windows final: job118815317048 no workflow39476966137 concluído SUCCESS. Teste adicional usa docker.cmd nativo em processos PowerShell5.1 separados: primeira instalação vazia passa; existência de volume e falha de listagem recusam criação de configuração. Testes anteriores de ACL/parar/abrir também passaram. O teste teve duas correções no próprio harness para propagar o exit do filho e retornar sucesso após falhas esperadas; não foram suprimidas as verificações de preservação.

A montagem Linux e a regressão geral desse novo SHA ainda estavam em execução na emissão deste adendo. A alteração de funcionamento é exclusiva do iniciador Windows; aplicação/compose/contêineres continuam com o código já validado acima. O novo pacote ainda precisa ser aberto no computador do usuário. A captura não comprova criação do banco nem instalação concluída.
