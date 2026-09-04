# SECURITY.md — InfraManager

## 1. Objetivo

Este documento define os requisitos, controles e decisões de segurança do **InfraManager**.

A aplicação deverá ser desenvolvida seguindo os princípios de:

- Secure by Design;
- Secure by Default;
- Least Privilege;
- Defense in Depth;
- Deny by Default;
- validação server-side;
- mínimo privilégio;
- proteção de credenciais e segredos;
- rastreabilidade de ações críticas.

O projeto deverá atender aos requisitos acadêmicos de segurança da aplicação, infraestrutura, GitHub e CI/CD.

A atividade exige explicitamente:

- SSH por chave;
- autenticação SSH por senha desabilitada;
- Fail2Ban;
- exposição apenas das portas necessárias;
- HTTPS;
- redirecionamento HTTP → HTTPS;
- SSL Labs Nota A;
- suporte a PQC;
- prevenção de exposição de credenciais;
- mitigação de pelo menos três categorias da OWASP Top 10:2025;
- armazenamento seguro dos segredos utilizados no CI/CD. fileciteturn0file0L37-L46 fileciteturn0file0L64-L69 fileciteturn0file0L91-L97

---

# 2. Princípio Geral de Segurança

Nenhuma funcionalidade deverá ser considerada concluída apenas porque funciona.

Para ser considerada concluída, uma funcionalidade deverá:

1. validar os dados recebidos;
2. verificar autenticação;
3. verificar autorização;
4. possuir proteção contra CSRF quando aplicável;
5. tratar erros de maneira segura;
6. gerar auditoria quando necessário;
7. possuir testes;
8. não introduzir segredos no repositório.

Fluxo esperado:

```text
Requisição
    │
    ▼
Autenticação
    │
    ▼
Autorização
    │
    ▼
Validação
    │
    ▼
Regra de negócio
    │
    ▼
Persistência
    │
    ▼
Auditoria
    │
    ▼
Resposta
```

---

# 3. Modelo de Ameaças Inicial

O InfraManager deverá considerar inicialmente os seguintes riscos:

- tentativa de acesso sem autenticação;
- tentativa de elevação de privilégio;
- acesso direto a URLs administrativas;
- tentativa de SQL Injection;
- tentativa de XSS;
- tentativa de CSRF;
- brute force contra Login;
- brute force contra MFA;
- reutilização indevida de sessão;
- exposição de senha;
- exposição de segredo TOTP;
- exposição de chave SSH;
- exposição de GitHub Secrets;
- vazamento de stack trace;
- alteração de parâmetros diretamente na URL;
- exclusão indevida de registros;
- falha de auditoria;
- tentativa de acesso administrativo ao servidor por senha.

O modelo será refinado conforme o desenvolvimento.

---

# 4. Classificação de Dados

## 4.1 Dados Públicos

Exemplos:

- nome do projeto;
- documentação pública;
- código-fonte;
- arquitetura genérica.

---

## 4.2 Dados Internos

Exemplos:

- ativos;
- hostnames;
- inventário de máquinas virtuais;
- datacenters;
- racks;
- sistemas operacionais;
- responsáveis.

Embora o repositório seja público por requisito acadêmico, dados reais de produção não deverão ser utilizados.

Todos os dados apresentados na aplicação acadêmica deverão ser:

- fictícios;
- anonimizados;
- ou criados especificamente para demonstração.

---

## 4.3 Dados Sensíveis

Exemplos:

- password hashes;
- TOTP secrets;
- recovery codes;
- Flask Secret Key;
- chaves SSH;
- credenciais OCI;
- GitHub Secrets.

Esses dados nunca deverão ser enviados para o repositório.

---

# 5. Dados Reais

A aplicação acadêmica não deverá armazenar:

- credenciais reais de ambientes corporativos;
- IPs internos reais quando isso puder representar risco;
- informações confidenciais de empregadores;
- nomes de usuários reais sem necessidade;
- segredos de produção;
- documentação interna real.

Dados de demonstração deverão ser fictícios.

Exemplo:

```text
HOST-LAB-01
VM-APP-DEMO-01
192.0.2.10
admin.demo
```

---

# 6. Autenticação

A autenticação deverá utilizar, para todos os usuários:

```text
Username
   +
Password
   +
MFA TOTP
```

A autenticação completa somente ocorrerá após todas as etapas exigidas.

O MFA obrigatório é um requisito adicional de segurança do InfraManager. Ele não deverá ser descrito como exigência direta do professor ou do enunciado acadêmico.

---

# 7. Senhas

Senhas nunca deverão ser armazenadas em texto puro.

Fluxo:

```text
Password
   │
   ▼
Password Hashing
   │
   ▼
password_hash
```

A aplicação deverá utilizar biblioteca consolidada para geração e verificação de hashes.

O código não deverá implementar algoritmo criptográfico próprio.

É proibido:

```python
password = "admin123"
```

e também:

```text
senha123
admin
password
```

como credenciais permanentes hardcoded.

---

# 8. Política Inicial de Senhas

Para o MVP, a política mínima será:

- tamanho mínimo definido no sistema;
- rejeição de senhas excessivamente curtas;
- armazenamento somente em hash;
- nenhuma recuperação da senha original;
- alteração de senha autenticada;
- redefinição administrativa sem visualização da senha anterior.

Evitar regras artificiais como obrigatoriedade excessiva de símbolos quando não houver justificativa.

O foco será comprimento adequado e armazenamento seguro.

---

# 9. Mensagens de Erro de Login

A aplicação não deverá revelar se:

- usuário existe;
- usuário não existe;
- senha está incorreta.

Mensagem padrão:

```text
Usuário ou senha inválidos.
```

Não utilizar:

```text
Usuário não encontrado.
```

ou:

```text
Senha incorreta para admin.
```

---

# 10. Proteção Contra Brute Force

A rota:

```text
/login
```

deverá possuir rate limiting.

Também deverão ser protegidas:

```text
/mfa
/mfa/recovery
/password/*
```

Os limites definitivos deverão equilibrar segurança e usabilidade.

Tentativas excessivas deverão gerar:

```text
HTTP 429
```

quando apropriado.

Eventos deverão ser registrados.

Configuração atual da etapa 02:

```text
POST /login       → 5 tentativas / 15 minutos
POST /mfa/verify  → 5 tentativas / 5 minutos
```

O backend `memory://` do Flask-Limiter mantém contadores somente no processo local.
Ele não é adequado para produção com múltiplos workers, pois os limites não seriam
compartilhados. Um armazenamento compartilhado deverá ser definido antes da
produção; Redis permanece deliberadamente fora desta etapa.

---

# 11. MFA — Multi-Factor Authentication

O sistema utilizará **TOTP**.

Fluxo:

```text
Login
   │
   ▼
Username + Password
   │
   ▼
Credenciais válidas?
   │
   ▼
MFA configurado?
 ┌─┴──────────┐
 │            │
Não          Sim
 │            │
 ▼            │
Configuração  │
e confirmação │
 └─────┬──────┘
       ▼
Código TOTP
   │
   ▼
Código válido?
   │
   ▼
Sessão autenticada
```

MFA fortalece diretamente o controle relacionado a falhas de autenticação.

MFA é obrigatório para `ADMIN`, `OPERATOR` e `VIEWER`.

Na etapa 02.7, o suporte técnico é introduzido de forma opcional por usuário para
preservar compatibilidade com as contas existentes. A imposição obrigatória para
todos os perfis permanece um requisito do MVP e será aplicada em etapa posterior.
TOTP reduz o risco de comprometimento apenas por senha, mas não constitui proteção
completa contra phishing.

---

# 12. Estado Pré-MFA

Após senha correta, o usuário não deverá receber sessão autenticada definitiva.

Deverá existir apenas estado temporário.

Exemplo conceitual:

```python
session["pending_mfa_user_id"]
```

A chamada:

```python
login_user(user)
```

somente deverá ocorrer depois da validação TOTP.

O estado pré-MFA atual contém somente o identificador do usuário e o instante em
que a senha foi validada. Ele expira em 5 minutos, é protegido pela assinatura da
sessão Flask e é removido no sucesso, na expiração ou quando o fluxo se torna
inválido. Senha, código TOTP e segredo TOTP não integram esse estado.

---

# 13. Ativação do MFA

Fluxo:

```text
Senha validada no primeiro acesso
      │
      ▼
Solicita ativação
      │
      ▼
Sistema gera segredo
      │
      ▼
QR Code
      │
      ▼
Authenticator
      │
      ▼
Código de confirmação
      │
      ▼
MFA ativado
```

O MFA só deverá ser marcado como ativo após um código TOTP válido ser confirmado.

Enquanto a configuração não for confirmada, o usuário permanecerá em estado pré-MFA e não poderá acessar o Dashboard nem outras rotas protegidas.

Na ativação opcional da etapa 02.7, um usuário que já possua sessão
autenticada inicia o setup na área da conta. O QR Code é SVG gerado em memória e
incorporado como `data URI`; nenhum arquivo ou endpoint público é criado. Abrir a
página não ativa MFA. A ativação ocorre somente após validar um código TOTP.

A verificação usa `PyOTP`, janela de tolerância `valid_window=1` e aceita somente
códigos de seis dígitos. A rota de segundo fator permite no máximo 5 tentativas em
5 minutos por origem com o backend de rate limiting configurado.

---

# 14. Segredo TOTP

O segredo TOTP é considerado dado sensível.

Não poderá:

- aparecer em logs;
- aparecer no Git;
- aparecer em stack trace;
- aparecer em mensagens de erro;
- ser incluído em screenshots de evidência.

A estratégia final de armazenamento deverá considerar proteção adicional adequada ao MVP.

Limitação conhecida da etapa 02.7: depois da confirmação, o segredo TOTP é
armazenado no SQLite sem criptografia de campo. Ele não é exibido novamente,
incluído em templates administrativos, mensagens de erro ou logs. Antes de uso em
produção, deverá ser protegido em repouso com criptografia autenticada e chave
externa ao banco e ao repositório, incluindo estratégia segura de rotação.

A desativação pelo titular exige simultaneamente a senha atual e um TOTP válido.
Quando concluída, remove o segredo persistido. Reset administrativo permanece fora
do escopo desta etapa.

---

# 15. Recovery Codes

Códigos de recuperação deverão:

- ser aleatórios;
- ser exibidos somente quando gerados;
- possuir uso único;
- ser invalidados após utilização;
- ser armazenados somente em forma de hash.

Exemplo conceitual:

```text
Código
  │
  ▼
Hash
  │
  ▼
Banco
```

Nunca:

```text
Banco:
ABCD-EFGH
```

---

# 16. Reconfiguração e Reset de MFA

A reconfiguração de MFA deverá exigir confirmação de identidade.

Preferencialmente:

```text
Senha atual
   +
Código TOTP
```

ou procedimento administrativo explicitamente autorizado.

A ação deverá gerar AuditLog. Como o MFA é obrigatório, um reset administrativo não poderá deixar a conta operando sem o segundo fator: no próximo Login, o usuário deverá ser obrigado a configurar e confirmar novo TOTP antes do Dashboard.

---

# 17. Sessão

Sessões deverão possuir configurações seguras.

Em produção:

```text
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
```

ou configuração equivalente compatível com o framework.

A configuração comum explicita `SESSION_PERMANENT=False`. Desenvolvimento local
HTTP não força `Secure`; produção exige `SESSION_COOKIE_SECURE=True` e valida a
presença de `SECRET_KEY` fornecida pelo ambiente.

---

# 18. Timeout de Sessão

Sessões não deverão permanecer indefinidamente válidas.

Deverá ser utilizado timeout adequado.

Após expiração:

```text
Sessão expirada
      │
      ▼
/login
```

O valor definitivo será configurado durante a implementação.

---

# 19. Session Fixation

Após autenticação bem-sucedida, o fluxo deverá evitar reutilização insegura de estado anterior.

Mudanças relevantes de autenticação deverão renovar ou limpar o estado da sessão conforme suporte do framework.

---

# 20. Logout

Logout deverá:

- invalidar a sessão;
- remover estados temporários de MFA;
- redirecionar para Login;
- impedir acesso posterior às rotas protegidas.

---

# 21. Controle de Acesso — RBAC

Perfis:

```text
ADMIN
OPERATOR
VIEWER
```

Autorização deverá ocorrer no backend.

O papel será armazenado diretamente em `User.role`, restrito aos valores técnicos `admin`, `operator` e `viewer`, correspondentes aos perfis ADMIN, OPERATOR e VIEWER. Não haverá entidade ou tabela `Role` separada no MVP.

Nunca apenas:

```text
Esconder botão
```

A ocultação no frontend será somente conveniência visual.

---

# 22. Deny by Default

Se uma permissão não estiver explicitamente concedida, o acesso deverá ser negado.

Exemplo:

```text
Usuário VIEWER
       │
       ▼
POST /assets/new
       │
       ▼
403 Forbidden
```

---

# 23. Matriz de Acesso

## ADMIN

Pode:

- criar;
- visualizar;
- editar;
- excluir;
- administrar usuários;
- consultar auditoria.

## OPERATOR

Pode:

- visualizar;
- criar;
- editar.

Não pode:

- excluir registros críticos;
- administrar usuários;
- consultar funções administrativas restritas.

## VIEWER

Pode:

- visualizar;
- pesquisar;
- filtrar.

Não pode modificar dados.

---

# 24. Acesso Direto por URL

Toda rota deverá validar autorização independentemente da interface.

Exemplo de ataque:

```text
VIEWER
   │
   ▼
POST /assets/15/delete
```

Resultado esperado:

```text
403 Forbidden
```

---

# 25. IDOR / Object-Level Authorization

A existência de um identificador válido não concede permissão.

Exemplo:

```text
/assets/25/edit
```

A aplicação deverá validar:

1. usuário autenticado;
2. papel/permissão;
3. existência do recurso;
4. regra de autorização.

---

# 26. CSRF

Operações que modificam estado deverão possuir proteção CSRF.

Abrange:

- POST;
- PUT, quando utilizado;
- PATCH, quando utilizado;
- DELETE, quando utilizado.

No MVP Flask tradicional, operações de alteração serão preferencialmente realizadas por POST protegido por Flask-WTF/CSRF.

---

# 27. Operações por GET

GET deverá ser considerado seguro e sem efeitos colaterais relevantes.

É proibido implementar:

```text
GET /assets/15/delete
```

Utilizar:

```text
POST /assets/15/delete
```

com:

```text
Autenticação
+
Autorização
+
CSRF
```

---

# 28. Validação Server-Side

Toda entrada deverá ser validada no servidor.

Validação no HTML/JavaScript é complementar.

Nunca deverá ser considerada controle de segurança suficiente.

---

# 29. Validações Previstas

Exemplos:

## IP

Utilizar biblioteca apropriada para validar:

```text
192.168.1.1
```

Rejeitar:

```text
999.999.999.999
```

## E-mail

Validar formato adequado.

## vCPU

Aceitar apenas inteiro dentro de intervalo permitido.

## RAM

Aceitar apenas valor numérico válido.

## Rack Units

Aceitar apenas valores positivos dentro do tamanho físico do rack.

## Enum

Status e tipo deverão ser restritos a valores definidos.

---

# 30. Limitação de Tamanho

Campos deverão possuir tamanho máximo.

Exemplo:

```text
hostname <= limite definido
notes <= limite definido
manufacturer <= limite definido
```

Isso ajuda a evitar:

- entradas inesperadas;
- abuso de armazenamento;
- problemas de renderização;
- cargas excessivas.

---

# 31. SQL Injection

A aplicação deverá utilizar SQLAlchemy ORM.

Não utilizar:

```python
query = "SELECT * FROM asset WHERE hostname = '" + hostname + "'"
```

Utilizar ORM ou parâmetros seguros.

Entradas do usuário nunca deverão ser concatenadas diretamente a SQL.

---

# 32. XSS

Templates deverão utilizar escaping padrão do Jinja2.

Nunca utilizar conteúdo do usuário como HTML confiável sem necessidade.

Evitar:

```text
|safe
```

para dados provenientes do usuário.

Caso seja necessário conteúdo HTML em alguma funcionalidade futura, deverá existir sanitização apropriada.

---

# 33. Template Injection

Entradas de usuários nunca deverão ser interpretadas como templates Jinja.

É proibido utilizar mecanismos como criação dinâmica de templates diretamente a partir de conteúdo controlado pelo usuário.

---

# 34. Command Injection

A aplicação não deverá executar comandos de sistema utilizando diretamente valores fornecidos pelo usuário.

Evitar:

```python
os.system(user_input)
```

ou:

```python
subprocess(..., shell=True)
```

com entrada não confiável.

---

# 35. Upload de Arquivos

Upload de arquivos não fará parte do MVP.

Caso seja adicionado posteriormente, exigirá revisão específica de segurança.

---

# 36. Auditoria

O AuditLog deverá registrar ações relevantes.

Eventos implementados na etapa 02.8:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
LOGOUT
MFA_SUCCESS
MFA_FAILURE
MFA_ENABLED
MFA_DISABLED
USER_CREATED
USER_UPDATED
USER_ACTIVATED
USER_DEACTIVATED
USER_ROLE_CHANGED
```

Eventos implementados na etapa 03.1:

```text
DATACENTER.CREATE
DATACENTER.UPDATE
DATACENTER.DELETE
```

Eventos reservados para etapas futuras:

```text
ASSET.CREATE
ASSET.UPDATE
ASSET.DELETE

VM.CREATE
VM.UPDATE
VM.DELETE

ROOM.CREATE
ROOM.UPDATE
ROOM.DELETE

RACK.CREATE
RACK.UPDATE
RACK.DELETE
```

Datacenter, Sala e Rack possuem CRUD completo. Suas operações de escrita deverão ser auditadas e suas exclusões deverão validar dependências.

---

# 37. Dados de Auditoria

O registro original persistido desde a etapa 02.8 possui:

```text
id
event_type
actor_user_id (opcional)
target_user_id (opcional)
ip_address
user_agent
details
created_at
```

A etapa 03.1 acrescentou os campos opcionais:

```text
resource_type (opcional)
resource_id (opcional)
result (opcional)
```

`details` é um JSON curto com lista branca específica por evento. São permitidos
somente motivo genérico de falha, perfil e status atribuídos, origem CLI, nomes de
campos alterados e transição de perfil. Valores anteriores de username/e-mail não
são armazenados.

Eventos de Datacenter usam `resource_type`, `resource_id` e `result` controlados,
sem copiar nome, localização, descrição ou conteúdo integral do formulário. A
alteração do Datacenter e o respectivo AuditLog são confirmados na mesma transação.

O endereço IP vem exclusivamente de `request.remote_addr`. A aplicação não
interpreta `X-Forwarded-For` nesta fase; a confiança no proxy será configurada e
testada junto com Nginx/ProxyFix. O User-Agent é truncado em 255 caracteres e pode
ser omitido da tabela administrativa.

Nos fluxos anteriores à etapa 03.1, falhas de persistência da auditoria executam
rollback da tentativa, geram erro no Application Log somente com o tipo do evento e
não interrompem a operação principal já concluída. Nas operações de Datacenter, a
alteração e a auditoria pertencem à mesma transação e sofrem rollback em conjunto.
Não existe `try/except: pass` nem inclusão do conteúdo do evento no log técnico.

---

# 38. Dados que Não Devem Ir para Auditoria

Nunca registrar:

- senha;
- password hash;
- código TOTP;
- segredo TOTP;
- recovery code;
- cookie;
- session ID;
- private key;
- GitHub token.

---

# 39. Imutabilidade Lógica

Usuários comuns não deverão possuir acesso para modificar logs de auditoria.

O módulo de Auditoria será somente leitura pela interface.

A rota `GET /admin/audit` é protegida por autorização server-side para `admin`,
ordena os registros do mais recente para o mais antigo e não oferece edição ou
exclusão.

Não há retenção ou remoção automática, exportação, assinatura criptográfica,
integração com SIEM/syslog remoto ou correlação de eventos nesta etapa. Alertas de
segurança continuam como requisito futuro do MVP.

---

# 40. Logs Técnicos

Logs técnicos devem auxiliar diagnóstico, mas não podem expor informações sensíveis.

Produção não deverá registrar:

```text
SECRET_KEY
password
TOTP secret
SSH key
token
Authorization header
```

## Alertas de Segurança

Para atender A09, eventos críticos ou repetidos deverão gerar um alerta simples, além do AuditLog. Gatilhos mínimos:

- múltiplas falhas de Login para a mesma origem ou conta em uma janela curta;
- múltiplas falhas de MFA;
- bloqueio por rate limiting (`429`);
- tentativa de acesso a função administrativa negada (`403`).

O alerta deverá conter somente data/hora, tipo, severidade (`WARNING` ou `CRITICAL`), origem resumida, contagem e estado (`novo` ou `revisado`). Administradores deverão visualizar alertas recentes em tela/consulta própria. Não registrar senha, TOTP, segredo, token, cookie ou session ID. E-mail, SMS e integração com SIEM ficam fora do MVP.

---

# 41. Tratamento de Erros

Produção:

```text
DEBUG = False
```

Nunca exibir:

- traceback;
- query SQL completa com dados sensíveis;
- caminho de filesystem;
- variáveis de ambiente;
- configuração Flask.

---

# 42. Error Handlers

A aplicação deverá possuir páginas para:

```text
400
403
404
429
500
```

Mensagens devem ser genéricas e úteis.

Exemplo:

```text
500

Ocorreu um erro interno.
Tente novamente mais tarde.
```

---

# 43. Security Headers

Deverão ser utilizados, conforme compatibilidade:

```text
Strict-Transport-Security
Content-Security-Policy
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
```

Configuração deverá ser testada antes da entrega.

---

# 44. X-Frame-Options / Clickjacking

A aplicação deverá impedir framing não autorizado.

Isso poderá ser obtido por:

```text
Content-Security-Policy: frame-ancestors
```

e/ou mecanismo equivalente.

---

# 45. HTTPS

Produção deverá utilizar somente HTTPS para tráfego de usuários.

Fluxo:

```text
http://IP
   │
   ▼
Redirect
   │
   ▼
https://IP
```

A atividade exige redirecionamento automático HTTP → HTTPS. fileciteturn0file0L43-L46

---

# 46. Certificado TLS

Será utilizado:

```text
Let's Encrypt
+
Certbot >= 5.4
```

O Certbot deverá solicitar certificado para o IP público usando `--preferred-profile shortlived`, `--ip-address` e um método compatível, preferencialmente `webroot`. O procedimento deverá ser testado primeiro com `--staging`.

Certificados Let's Encrypt para IP público são de curta duração. Como o plugin Nginx do Certbot ainda não instala automaticamente esse tipo de certificado, o Nginx deverá apontar explicitamente para `fullchain.pem` e `privkey.pem` emitidos para o IP.

A renovação deverá ser totalmente automatizada, com `deploy-hook` para recarregar o Nginx após emissão/renovação. Falha de renovação deverá gerar log técnico e alerta administrativo.

---

# 47. SSL Labs

Antes da entrega deverá ser realizado teste no:

```text
Qualys SSL Labs
```

Meta obrigatória:

```text
Nota A
```

e:

```text
PQC habilitado
```

conforme o enunciado. fileciteturn0file0L43-L46

---

# 48. SSH

Acesso administrativo:

```text
Notebook pessoal
      │
      │ chave privada
      ▼
OCI Ubuntu
```

Autenticação SSH por senha deverá estar desabilitada.

O enunciado exige autenticação administrativa via chave SSH. fileciteturn0file0L41-L42

---

# 49. Configuração SSH

Itens esperados:

```text
PasswordAuthentication no
PermitRootLogin no
```

demais configurações deverão ser revisadas conforme a versão do OpenSSH instalada.

---

# 50. Chave Privada SSH

A chave privada:

- ficará somente em local protegido;
- não será enviada ao GitHub;
- não ficará em `docs/`;
- não será incluída em screenshots;
- não será compartilhada com prompts de IA.

---

# 51. Fail2Ban

Obrigatório para SSH.

Configuração mínima conforme atividade:

```text
maxretry = 4
bantime = 24h
```

fileciteturn0file0L41-L42

Será criada evidência da configuração ativa.

---

# 52. Firewall

A aplicação deverá seguir Least Privilege.

Portas esperadas:

```text
22/tcp
80/tcp
443/tcp
```

Nada além disso deverá ser exposto sem justificativa.

---

# 53. Porta 22

Sempre que tecnicamente viável, o acesso SSH deverá ser restrito ao IP administrativo.

Caso o IP do usuário seja dinâmico, a estratégia deverá ser documentada.

Fail2Ban continuará obrigatório.

---

# 54. Gunicorn

Gunicorn não deverá escutar em endereço público acessível pela internet.

O serviço deverá carregar a aplicação pelo ponto de entrada padronizado `wsgi.py` em produção e na documentação do InfraManager.

Utilizar preferencialmente:

```text
127.0.0.1
```

ou:

```text
Unix Socket
```

Nginx será o único componente Web exposto externamente.

---

# 55. SQLite

Arquivo do banco:

```text
instance/inframanager.db
```

deverá:

- estar fora do Git;
- possuir permissões adequadas;
- não ser servido pelo Nginx;
- não estar dentro de pasta pública/static.

---

# 56. Backups

Para o MVP acadêmico será prevista rotina simples de backup do banco antes de operações de manutenção/deploy que possam alterar schema.

Backup não deverá ser incluído no repositório público.

---

# 57. GitHub

O repositório será público por requisito da atividade. fileciteturn0file0L60-L69

Portanto, todo arquivo versionado deverá ser considerado publicamente acessível.

Regra:

> Se uma informação não puder ser pública, ela não poderá estar no Git.

Checklist obrigatório da conta e do acesso:

- 2FA habilitado na conta GitHub;
- operações Git autenticadas por chave SSH protegida ou PAT de escopo mínimo;
- senha da conta não utilizada em push/pull;
- chaves e PATs ausentes do repositório, logs, artefatos e screenshots.

---

# 58. `.gitignore`

Deverá incluir pelo menos:

```gitignore
.env
.env.*
!.env.example

*.pem
*.key

id_rsa
id_ed25519

*.db
*.sqlite
*.sqlite3

instance/

.venv/
venv/

__pycache__/
*.pyc
```

A atividade proíbe commit de `.env`, chaves privadas, credenciais e bancos locais. fileciteturn0file0L64-L69

---

# 59. `.env.example`

Permitido:

```text
SECRET_KEY=
DATABASE_URL=
```

Não permitido:

```text
SECRET_KEY=valor-real
```

O arquivo deverá apenas demonstrar nomes das variáveis necessárias.

---

# 60. Flask Secret Key

A `SECRET_KEY` deverá ser:

- gerada aleatoriamente;
- fornecida por variável de ambiente;
- diferente entre ambientes;
- nunca versionada.

---

# 61. GitHub Secrets

Pipeline deverá utilizar GitHub Secrets para dados confidenciais.

Exemplos:

```text
OCI_HOST
OCI_USER
OCI_SSH_PRIVATE_KEY
DEPLOY_PATH
```

A atividade exige o uso de Secrets para as credenciais usadas pela pipeline. fileciteturn0file0L119-L129

---

# 62. GitHub Actions

Workflow não deverá:

- imprimir Secrets;
- utilizar `echo` de credenciais;
- armazenar chave privada como artefato;
- enviar arquivos `.env` ao log;
- executar comandos perigosos baseados em entrada externa.

---

# 63. CI — Segurança

Antes do deploy deverão ser executados:

```text
Lint
   ↓
Testes
   ↓
Security Checks
   ↓
Deploy
```

Falha crítica deverá interromper o pipeline.

---

# 64. Testes de Segurança

Devem existir testes automatizados para pelo menos:

- acesso sem Login;
- usuário sem permissão;
- Viewer tentando POST;
- Operator tentando Delete;
- Login inválido;
- MFA inválido;
- usuário desabilitado;
- CSRF inválido;
- validação de campos;
- acesso direto por URL.

---

# 65. OWASP Top 10:2025

A atividade exige mitigação e documentação de pelo menos três categorias. fileciteturn0file0L91-L97

O projeto documentará prioritariamente quatro áreas.

---

# 66. A01:2025 — Broken Access Control

Controles implementados:

```text
Flask-Login
+
RBAC
+
Deny by Default
+
Server-Side Authorization
+
CSRF
+
Proteção contra acesso direto
```

## Evidências

- teste de rota protegida;
- teste de VIEWER tentando editar;
- teste de OPERATOR tentando excluir;
- screenshot/resultado 403;
- referência ao decorator ou função de autorização.

---

# 67. A05:2025 — Injection

Controles:

```text
SQLAlchemy ORM
+
Queries parametrizadas
+
Validação server-side
+
Jinja escaping
+
Proibição de SQL concatenado
```

## Evidências

- código utilizando ORM;
- teste com entrada malformada;
- validação de campos;
- security review do Codex.

---

# 68. A07:2025 — Authentication Failures

Controles:

```text
Password Hashing
+
MFA TOTP
+
Rate Limiting
+
Secure Session
+
Logout
+
Generic Error Messages
+
User Disable
```

## Evidências

- tela Login;
- tela MFA;
- teste de senha inválida;
- teste MFA inválido;
- rate limiting;
- cookies seguros em produção.

---

# 69. A09:2025 — Security Logging & Alerting Failures

Controles:

```text
Authentication Logging
+
CRUD Audit
+
MFA Audit
+
Administrative Audit
+
Security Alerts
```

## Evidências

- tela de auditoria;
- evento Login Failure;
- evento Update Asset;
- evento Delete VM;
- teste automatizado do AuditLog.
- alerta gerado por falhas repetidas de Login/MFA, 429 ou tentativa administrativa negada;
- tela administrativa com severidade, contagem e estado do alerta.

---

# 70. Matriz Requisito → Controle → Evidência

| Área | Controle | Evidência |
|---|---|---|
| Login | Hash + sessão | Código + teste |
| MFA | TOTP | Tela + teste |
| Brute force | Rate Limit | Teste 429 |
| RBAC | Decorators server-side | Teste 403 |
| SQL Injection | SQLAlchemy ORM | Código |
| CSRF | Flask-WTF | Teste |
| Auditoria | AuditLog | Tela + banco |
| Alertas A09 | Gatilhos + lista administrativa | Teste + tela |
| Secrets | `.gitignore` | Repositório |
| SSH | Public Key | Configuração |
| Fail2Ban | 4 / 24h | Configuração ativa |
| HTTPS | Certbot `>= 5.4` + certificado para IP público | Navegador + renovação |
| TLS | SSL Labs A | Screenshot |
| PQC | SSL Labs | Screenshot |
| CI/CD | GitHub Actions | Pipeline |
| Secrets CI/CD | GitHub Secrets | Configuração sem exibir valores |

---

# 71. Evidências Acadêmicas de Segurança

Deverão ser coletadas evidências como:

```text
docs/evidencias/security/

01-login.png
02-mfa.png
03-mfa-failure.png
04-rbac-403.png
05-audit-log.png
06-rate-limit.png

07-ssh-config.png
08-fail2ban-config.png
09-fail2ban-status.png
10-firewall.png

11-https.png
12-http-redirect.png
13-ssl-labs-a.png
14-ssl-labs-pqc.png

15-github-gitignore.png
16-github-actions.png
17-security-tests.png
```

Screenshots deverão ocultar qualquer dado sensível.

---

# 72. Uso de IA e Segurança

O Codex deverá ser utilizado também como revisor de segurança.

Exemplo de tarefa:

```text
Analise o módulo de autenticação considerando:

- Authentication Failures;
- Session Management;
- MFA;
- CSRF;
- Brute Force;
- exposição de informações.

Não altere o código.

Liste os achados classificados como:
Critical
High
Medium
Low
Informational.
```

Depois da análise:

```text
Corrija apenas os achados aprovados,
mantendo a arquitetura existente
e adicionando testes de regressão.
```

---

# 73. Restrições para Agentes de IA

Nenhuma IA deverá receber:

- chave privada SSH real;
- token GitHub;
- senha real;
- segredo TOTP real;
- credencial OCI real;
- conteúdo de `.env` de produção.

O agente deverá utilizar placeholders.

Exemplo:

```text
OCI_HOST=<OCI_PUBLIC_IP>
```

---

# 74. Security Review Antes de Commit

Antes de commits importantes, deverá ser feita revisão considerando:

```text
Secrets?
Passwords?
Authorization?
Input Validation?
CSRF?
SQL Injection?
XSS?
Session?
Audit?
Tests?
```

---

# 75. Security Review Antes do Deploy

Checklist:

- [ ] testes aprovados;
- [ ] nenhuma credencial no Git;
- [ ] DEBUG desativado;
- [ ] SECRET_KEY externa;
- [ ] cookies seguros;
- [ ] CSRF ativo;
- [ ] rate limit ativo;
- [ ] RBAC ativo;
- [ ] HTTPS ativo;
- [ ] banco fora de static;
- [ ] logs sem segredos.

---

# 76. Hardening da VM

A VM deverá possuir:

- atualizações instaladas;
- usuário administrativo não root;
- SSH por chave;
- senha SSH desabilitada;
- root login desabilitado;
- Fail2Ban;
- firewall;
- somente serviços necessários;
- Nginx;
- Gunicorn via systemd.

As evidências da OCI deverão incluir: compartment, VCN, subnet pública, internet gateway, security list e/ou NSG, tela de criação da instância, IP público e instância no estado `Running`/em execução. Nenhuma captura poderá expor material secreto.

---

# 77. Least Privilege no Linux

O processo da aplicação não deverá executar como root.

Gunicorn deverá utilizar usuário de serviço apropriado ou usuário dedicado conforme decisão de implantação.

Arquivos deverão possuir somente permissões necessárias.

---

# 78. Systemd

Arquivo de serviço não deverá conter credenciais publicamente legíveis.

Variáveis sensíveis deverão utilizar mecanismo apropriado de ambiente/configuração protegido.

---

# 79. Nginx

Nginx não deverá:

- listar diretórios;
- expor `.env`;
- expor banco SQLite;
- expor arquivos Python;
- funcionar como proxy para portas desnecessárias.

---

# 80. Dependências

Dependências Python deverão ser declaradas.

A pipeline deverá permitir revisão de vulnerabilidades conhecidas.

Dependências não utilizadas deverão ser removidas.

---

# 81. Atualização de Dependências

Não realizar atualizações automáticas cegas em produção.

Mudanças deverão passar por:

```text
Atualização
   ↓
Testes
   ↓
Review
   ↓
Deploy
```

---

# 82. Segurança de Desenvolvimento

O notebook de desenvolvimento deverá:

- manter chave SSH protegida;
- não compartilhar `.env`;
- utilizar Git de maneira controlada;
- evitar credenciais no histórico de terminal;
- utilizar ambiente virtual Python;
- manter ferramentas atualizadas.

---

# 83. Branch Principal

A branch:

```text
main
```

será considerada branch de produção.

Push para `main` deverá disparar o pipeline exigido pela atividade. fileciteturn0file0L123-L129

Durante desenvolvimento, poderão ser utilizadas branches auxiliares.

---

# 84. Critérios de Segurança para Conclusão

O projeto somente poderá ser considerado finalizado quando:

- [ ] senhas estiverem armazenadas somente em hash;
- [ ] MFA estiver funcionando;
- [ ] primeiro acesso exigir configuração e confirmação de MFA antes do Dashboard;
- [ ] recovery codes estiverem protegidos;
- [ ] sessões estiverem configuradas com segurança;
- [ ] rate limiting estiver ativo;
- [ ] RBAC estiver ativo;
- [ ] CSRF estiver ativo;
- [ ] validação server-side estiver ativa;
- [ ] SQLAlchemy estiver sendo utilizado corretamente;
- [ ] XSS estiver mitigado;
- [ ] auditoria estiver funcionando;
- [ ] alertas simples para eventos críticos/repetidos estiverem funcionando;
- [ ] segredos estiverem fora do Git;
- [ ] SSH utilizar chave;
- [ ] senha SSH estiver desabilitada;
- [ ] Fail2Ban estiver configurado;
- [ ] firewall estiver configurado;
- [ ] Gunicorn não estiver exposto;
- [ ] HTTPS estiver ativo;
- [ ] Certbot `>= 5.4` emitir e renovar automaticamente certificado para o IP público;
- [ ] HTTP redirecionar para HTTPS;
- [ ] SSL Labs retornar A;
- [ ] PQC estiver confirmado;
- [ ] GitHub Secrets estiver configurado;
- [ ] GitHub 2FA estiver habilitado e operações Git utilizarem SSH ou PAT de escopo mínimo;
- [ ] testes de segurança estiverem passando;
- [ ] Security Review com IA tiver sido realizado;
- [ ] OWASP estiver documentado no README.

---

# 85. Princípio Final

O InfraManager deverá assumir que:

```text
Toda entrada é não confiável.

Toda ação deve ser autorizada.

Todo segredo deve permanecer secreto.

Toda operação crítica deve ser auditável.

Todo controle de segurança deve ser testável.
```

A segurança não deverá ser adicionada somente ao final do projeto.

Ela deverá fazer parte do projeto desde a primeira linha de código.
