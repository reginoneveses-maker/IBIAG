# Identidade visual do ExportHub / IBIAG

Referência fornecida pelo usuário: Ibiag Ingredients Presentation EN.pdf,15 páginas, versão recebida em19/10/2026. SHA-256:1edd6e5e78472102d22e677029e95bbb615e98988355b0dc8534f41ecb2827af. O PDF completo e seus contatos não foram copiados para o repositório.

## Elementos aproveitados

- Marca:20 formas vetoriais originais da página3, preservando o desenho e as cores. `frontend/public/brand/ibiag-logo.svg` contém apenas esses caminhos, sem imagem da página, script, fontes ou referências externas. Variante clara troca o azul por branco para uso em fundo escuro, conforme a aplicação clara vista nas páginas1/2; mantém o detalhe verde-lima. O ícone usa as quatro formas do símbolo original.
- Fotografia de açaí:JPEG incorporado à página2, extraído sem recriar conteúdo ou buscar imagens externas. Origem:objeto14 do PDF. Mantida como recurso local, aproximadamente495KiB; elementos decorativos não têm descrição redundante para leitores de tela.
- Cores observadas na marca vetorial:azul#1B4496 e verde-lima#CAD51E. Fundos marfim/oliva claro, texto azul-petróleo#102D3A e diagonais inspiradas na capa. Branco e azul mais escuro garantem contraste no login/navegação. Cores de erro/vencimento continuam semânticas.
- A apresentação contém Calibri e Serotiva SemBd. Essas fontes não foram extraídas nem redistribuídas. A aplicação usa a família Inter já existente, com alternativas locais Segoe UI/sans-serif; títulos mais leves, espaçamento e hierarquia aproximam o estilo sem copiar arquivos de fonte.

## Aplicação

Login com fotografia, marca clara, diagonal e formulário acessível; entrada com bloco institucional/fotografia e módulos existentes; barra lateral azul com marca original, detalhe-lima e cabeçalho claro; cabeçalhos e abas compartilhados e cartões da Gestão com paleta coerente. Título, descrição, idioma e ícone do navegador passam a identificar ExportHub / IBIAG.

No celular, a fotografia vira faixa superior e os blocos empilham; campos têm50px, os rótulos estão associados aos inputs e há nomes acessíveis para abrir/fechar o menu e voltar ao início. O navegador deve conferir ausência de rolagem horizontal em390px, funcionamento do formulário e do menu. Preferência por movimento reduzido é respeitada nos cartões.

Não há alteração nas regras de autenticação, papéis, APIs, permissões, dados ou cobrança. O frontend ainda depende da validação de infraestrutura da etapa1 antes da publicação do candidato completo. Recursos visuais não são prova de homologação operacional.

## Verificação

Suíte de interface e compilação; Chromium com login pelo formulário real, decodificação dos assets, entrada/navegação, menu móvel e fluxo existente completo. Capturas de login, entrada e Gestão em desktop/móvel são geradas usando exclusivamente banco/contas sintéticos. O workflow já existente conserva essas capturas por um dia para revisão visual, sem novo serviço ou credencial.

Evidências concretas de execução e revisão de imagens ficam no PR e no relatório de validação; nenhuma validação visual pode ser declarada apenas pela compilação.
