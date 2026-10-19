# Configuração e respostas da API

`CORS_ORIGINS` aceita origens HTTPS exatas. HTTP é permitido somente para loopback
de desenvolvimento. Wildcards, credenciais, caminhos, parâmetros e origens
inválidas causam falha de configuração sem repetir valores potencialmente secretos.
Portas padrão e hosts são canonicalizados. Sem configuração, somente localhost.
Os métodos e headers de preflight são explícitos; autenticação usa bearer, sem cookies.

Respostas da API não são armazenadas em cache. Recebem proteção contra sniffing,
framing e execução de conteúdo, política de referrer e permissões restritas.
Erros inesperados reutilizam a resposta genérica com incidente, sem entregar a
exceção original ao servidor de aplicação para registrar detalhes sensíveis.
Falhas de stream interrompem a resposta com erro genérico; não há como substituir
uma resposta que já começou a ser transmitida.

Downloads são anexos `application/octet-stream`, mesmo quando o MIME armazenado
é HTML ou outro conteúdo ativo, e recebem CSP sandbox. Os bytes não são alterados:
a prévia do frontend continua reconhecendo assinaturas de PDF/imagens e cria blobs
com MIME seguro. Isso não é varredura antivírus nem garantia de conteúdo benigno.

Debug fica falso. Docs/OpenAPI ficam desligados por padrão; `ENABLE_API_DOCS=true`
é uma opção explícita de desenvolvimento e não foi habilitada na hospedagem.
`JWT_SECRET` precisa ter pelo menos 32 caracteres, sem espaços externos; não é
normalizado ou rotacionado automaticamente. O comando do container desliga o
banner e o access log do Uvicorn para não registrar URLs com dados privados.

Antes de publicar, verificar a validade das origens e a política do segredo sem
exibir valores. Uma configuração antiga insegura passará a falhar fechada.
HSTS/TLS e IPs confiáveis devem ser validados no terminador HTTPS real; a API não
confia em cabeçalhos encaminhados arbitrários para decidir essas políticas.
