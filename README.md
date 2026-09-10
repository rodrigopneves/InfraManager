# InfraManager

Sistema web seguro para gerenciamento de infraestrutura de TI, desenvolvido como projeto aplicado da pós-graduação.

O InfraManager tem como objetivo centralizar informações sobre:

- ativos de TI;
- máquinas virtuais;
- datacenters;
- salas;
- racks;
- usuários;
- autenticação multifator;
- controle de acesso;
- auditoria.

O projeto aplica princípios de **Secure by Design**, **Secure by Default**, OWASP Top 10:2025, Cloud Computing e CI/CD.

---

## Status do Projeto

**Status atual:** fase final de validação dos requisitos acadêmicos e preparação da entrega.

| Área | Situação |
|---|---|
| Planejamento | Concluído |
| Requisitos | Concluído |
| Arquitetura | Concluída |
| Desenvolvimento | Concluído no escopo implementado |
| Segurança da aplicação | Concluída/validada nos controles implementados |
| Testes automatizados | Concluídos para as funcionalidades implementadas |
| OCI | Implantada |
| CI/CD | Implementado: integração contínua; deploy automático pendente |
| Documentação | Em revisão final |
| Validação acadêmica/evidências | Em andamento |

A aplicação entrega Application Factory, persistência e migrations, autenticação,
CSRF, rate limiting, gestão administrativa de usuários, RBAC, MFA TOTP obrigatório,
auditoria, alertas de segurança e CRUDs de Datacenters, Salas, Racks, Ativos e
Máquinas Virtuais. A interface responsiva utiliza Jinja2 e Bootstrap. O Dashboard
consulta dados reais e separa indicadores administrativos conforme o RBAC.
O ponto WSGI é `wsgi:app`; `run.py` atende ao desenvolvimento e aos comandos Flask.

O estado de implantação OCI e as confirmações de GitHub público, 2FA e proteção
das credenciais foram informados pelo responsável pelo projeto nesta revisão.
Código, testes e workflow foram conferidos no repositório. A consolidação das
evidências externas permanece em andamento; o quadro não representa aprovação
integral de todos os requisitos acadêmicos ou de todos os itens previstos no MVP.

Pendências e débitos conhecidos:

1. não existe integração com SIEM;
2. auditoria e alertas não possuem retenção automática;
3. recovery codes ainda não possuem implementação no código atual;
4. deploy automático e suas verificações posteriores não integram a pipeline;
5. faltam comprovações formais de HTTPS/renovação, SSL Labs A e PQC;
6. o `.gitignore` local não contém regras gerais para arquivos de chave
   (`*.pem`, `*.key`, `id_rsa` e `id_ed25519`).

O Flask-Limiter usa `memory://` em desenvolvimento e testes. Produção exige Redis
compartilhado, configurado por `RATELIMIT_STORAGE_URI`, para manter os contadores
entre workers Gunicorn. A aplicação aceita `redis://` e `rediss://`; a URI e suas
credenciais permanecem no ambiente protegido. O repositório fornece o cliente
Python; a operação do servidor Redis pertence à infraestrutura.

O deploy realizado na OCI inclui Nginx, Gunicorn e systemd. A factory aplica
`ProxyFix` somente em produção e confia em exatamente um valor de
`X-Forwarded-For` e de `X-Forwarded-Proto`; Host, porta e prefixo encaminhados não
são confiados. Gunicorn deve permanecer acessível somente pelo proxy local.

O runtime versionado inclui `gunicorn.conf.py` e exemplos de Nginx e systemd em
`deploy/`. Gunicorn está configurado com dois workers síncronos em
`127.0.0.1:8000`; Flask atende os arquivos estáticos; SQLite em arquivo usa foreign
keys, timeout de 30 segundos e WAL. `/health` consulta o banco e retorna resposta
genérica. Logs seguem para stdout/stderr, integrados ao journald pelo systemd.
[DEPLOYMENT.md](DEPLOYMENT.md) contém procedimentos de operação, mas ainda se
apresenta como runbook de preparação: não constitui evidência do deploy realizado.

---

# Objetivo Acadêmico

O projeto foi definido para atender aos requisitos da disciplina **Projeto Aplicado: Práticas de Mercado**.

A atividade exige a construção de uma aplicação web hospedada em nuvem pública utilizando recursos gratuitos, com Ubuntu Server ou Debian, Nginx ou Apache, acesso público pela internet e aplicação de controles de segurança.

Também são requisitos da atividade:

- repositório público no GitHub;
- prevenção de vazamento de credenciais;
- utilização de ambiente de desenvolvimento assistido por IA;
- Login;
- página interna protegida;
- Logout funcional;
- mitigação documentada de pelo menos três categorias da OWASP Top 10:2025;
- CI/CD utilizando GitHub Actions.

---

# Visão Geral

A arquitetura é monolítica modular, com Application Factory e Blueprints. As
rotas validam requisições e chamam services; estes coordenam regras de negócio,
models, persistência pelo SQLAlchemy ORM e auditoria.

```text
                        INTERNET
                           │
                         HTTPS
                           │
                           ▼
                       Nginx
                           │
                           ▼
                       Gunicorn
                           │
                           ▼
                        Flask
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   Autenticação          CRUDs           Auditoria
          │
          ▼
        RBAC
          │
          ▼
      SQLAlchemy
          │
          ▼
        SQLite
```

---

# Tecnologias

## Backend

- Python
- Flask

## Banco de Dados

- SQLite
- SQLAlchemy
- Flask-Migrate
- Alembic

## Segurança

- Flask-Login
- Flask-WTF
- Flask-Limiter
- PyOTP
- qrcode
- cryptography (Fernet para segredos MFA persistidos)
- Redis (contadores compartilhados de rate limiting em produção)
- MFA/TOTP
- CSRF
- RBAC
- Auditoria

## Frontend

- HTML
- Jinja2
- Bootstrap
- CSS

## Testes

- pytest
- Flask Test Client

## Produção

- Oracle Cloud Infrastructure
- Ubuntu Server
- Nginx
- Gunicorn
- systemd
- Fail2Ban
- UFW
- Certbot
- Let's Encrypt

## Desenvolvimento e IA

- Visual Studio Code
- OpenAI Codex
- Git
- GitHub
- GitHub Actions

---

# Ambiente de Desenvolvimento

O ambiente de desenvolvimento utiliza:

```text
Notebook pessoal
      │
      ▼
Visual Studio Code
      │
      ├── Python
      ├── Git
      ├── Terminal
      └── Codex
```

A IA é utilizada como apoio a:

- planejamento;
- implementação;
- criação de testes;
- code review;
- refatoração;
- auditoria de segurança;
- documentação.

## Instalação local

O projeto usa Python 3.14.4 e mantém somente dependências diretas com versões
exatas. Dependências transitivas continuam sendo resolvidas pelo `pip`.

Para executar a aplicação:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Para desenvolvimento, testes e verificações de qualidade:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

Para configurar e iniciar uma instalação local nova, copie `.env.example` para
`.env` e mantenha `FLASK_CONFIG=development`. Preencha `SECRET_KEY` com um valor
aleatório exclusivo e `MFA_ENCRYPTION_KEY` com uma chave Fernet válida, gerados e
armazenados localmente fora do Git. A configuração de desenvolvimento usa SQLite
em `instance/inframanager.db` e rate limiting em memória.

Depois de preencher o ambiente:

```bash
.venv/bin/flask --app run.py db upgrade
.venv/bin/flask --app run.py create-admin
.venv/bin/flask --app run.py run --host 127.0.0.1
```

`create-admin` solicita os dados interativamente, com senha oculta e confirmação.
Acesse `http://127.0.0.1:5000/login` e conclua a configuração TOTP para acessar o
Dashboard. O servidor Flask local é destinado ao desenvolvimento; a operação com
Gunicorn/systemd/Nginx está descrita em [DEPLOYMENT.md](DEPLOYMENT.md).

Validação local recomendada:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m pip_audit -r requirements.txt
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q --cov=app --cov-branch --cov-report=term-missing
```

As versões devem ser atualizadas deliberadamente: criar ambiente limpo, alterar
somente dependências diretas necessárias e executar `pip check`, auditoria, lint,
suíte completa e revisão de segurança antes de consolidar a mudança.

O enunciado da atividade permite Antigravity ou ambiente similar baseado em IA.

---

# Módulos do Sistema

A aplicação contém os seguintes módulos:

```text
InfraManager
│
├── Autenticação
│   ├── Login
│   ├── MFA
│   └── Logout
│
├── Dashboard
│
├── Ativos
│
├── Máquinas Virtuais
│
├── Datacenter
│   ├── Datacenters
│   ├── Salas
│   └── Racks
│
├── Usuários
│
├── RBAC
│
└── Auditoria
```

---

# Autenticação

Fluxo implementado:

```text
Username + Password
        │
        ▼
Credenciais válidas
        │
        ▼
MFA configurado?
     ┌──┴──┐
     │     │
    Não   Sim
     │     │
     ▼     │
Configurar │
e confirmar│
     └──┬──┘
        ▼
       TOTP
        │
        ▼
    Dashboard
```

O MFA é obrigatório para todos os usuários. No primeiro acesso, após a validação da senha, o usuário precisa configurar e confirmar o TOTP antes de acessar o Dashboard. A sessão autenticada definitiva somente é criada depois do código válido.

O MFA é um requisito adicional de segurança adotado pelo InfraManager, e não uma exigência direta do professor ou do enunciado acadêmico.

O fluxo atual exige MFA desde o primeiro acesso. A desativação exige senha e
TOTP, encerra a sessão e obriga a configuração de um novo segundo fator. Os
segredos persistidos são cifrados com Fernet; a chave permanece fora do banco
e do repositório. A reutilização de um timestep TOTP já aceito é rejeitada.

---

# MFA

O sistema utiliza TOTP compatível com aplicativos autenticadores.

Exemplos:

- Microsoft Authenticator;
- Google Authenticator;
- Bitwarden;
- Authy;
- outros aplicativos TOTP.

Os códigos de recuperação de uso único são um requisito ainda pendente: não há
model, rota ou testes desse fluxo no código atual. A implementação prevista exige
aleatoriedade, armazenamento somente em hash e invalidação após o uso.

---

# Perfis de Acesso

O sistema possui três perfis, definidos em `app/models/user.py`.

Os valores persistidos diretamente em `User.role` são `admin`, `operator` e
`viewer`, com os rótulos Administrador, Operador e Visualizador. O padrão de novos
usuários é `viewer`. Não existe entidade ou tabela `Role` separada.

## ADMIN

Pode:

- visualizar;
- cadastrar;
- editar;
- excluir;
- administrar usuários;
- visualizar auditoria.

## OPERATOR

Pode:

- visualizar;
- pesquisar;
- utilizar filtros.

Não pode criar, editar ou excluir recursos de infraestrutura nem executar funções
administrativas.

## VIEWER

Pode:

- visualizar;
- pesquisar;
- utilizar filtros.

Não pode modificar recursos de infraestrutura nem administrar usuários.
A configuração do próprio MFA segue o fluxo autenticado específico de conta.

---

# Gestão de Ativos

O módulo de ativos permite:

- cadastro;
- visualização;
- edição;
- exclusão;
- pesquisa;
- filtros.

Tipos disponíveis:

- Servidor;
- Storage;
- Switch;
- Roteador;
- Firewall;
- Access Point;
- Notebook;
- Desktop;
- Appliance;
- Outro.

---

# Máquinas Virtuais

O módulo permite gerenciamento de:

- hostname;
- IP;
- sistema operacional;
- ambiente;
- vCPU;
- RAM;
- armazenamento;
- host;
- status.

Ambientes disponíveis:

```text
Produção
Homologação
Desenvolvimento
Teste
Outro
```

Toda Máquina Virtual pertence obrigatoriamente a um Ativo do tipo
Servidor. O nome é globalmente único, IPv4 e IPv6 são validados no servidor, e os
recursos são armazenados como vCPU, memória em MB e disco em GB. Os status são Em
execução, Desligada, Suspensa e Manutenção. Somente Administradores podem criar,
editar e excluir; Operadores e Visualizadores possuem leitura.

---

# Datacenter

Estrutura conceitual:

```text
Datacenter
     │
     ▼
   Sala
     │
     ▼
   Rack
     │
     ▼
 Equipamento
```

Todo ativo físico pertence obrigatoriamente a um Rack.

Datacenter, Sala, Rack, Ativo e Máquina Virtual possuem CRUD completo.
Cada Sala pertence obrigatoriamente a um Datacenter e seu código é único dentro
desse Datacenter. Cada Rack pertence a uma Sala, possui capacidade entre 1 e 100 U
e código único nessa Sala. Escritas aplicam autorização server-side, validação,
CSRF, auditoria e verificação de dependências. Datacenters com Salas e Salas com
Racks não podem ser excluídos. Ativos respeitam a capacidade física do Rack e não
podem ocupar intervalos de U sobrepostos. Um Ativo Servidor pode hospedar várias
Máquinas Virtuais e não pode ser excluído enquanto possuir alguma VM.

```text
Datacenter
└── Sala
    └── Rack
        └── Ativo Servidor
            └── Máquina Virtual
```

---

# Dashboard

O Dashboard apresenta dados agregados do ambiente:

```text
Datacenters, Salas e Racks
Ativos físicos e Máquinas Virtuais
Capacidade e ocupação dos Racks

Ativos por status
Máquinas Virtuais por status
Estados vazios dos módulos
```

Administradores também visualizam totais de usuários e atividade recente da
auditoria. Essas consultas ficam em `app/dashboard/services.py`; dados
administrativos não são consultados nem renderizados para os demais perfis.

---

# Segurança

O projeto aplica os seguintes princípios:

```text
Secure by Design
Secure by Default
Least Privilege
Defense in Depth
Deny by Default
```

Os controles implementados incluem:

- password hashing;
- MFA;
- rate limiting;
- CSRF;
- RBAC;
- validação server-side;
- SQLAlchemy ORM;
- cookies seguros;
- timeout de sessão;
- auditoria;
- security headers;
- tratamento seguro de erros;
- proteção de Secrets.

---

# OWASP Top 10:2025

A atividade exige mitigação de pelo menos três categorias OWASP e sua documentação no README final.

O InfraManager implementa controles associados às seguintes categorias:

## A01:2025 — Broken Access Control

Controles:

- autenticação;
- RBAC;
- deny-by-default;
- autorização server-side;
- proteção contra acesso direto.

## A05:2025 — Injection

Controles:

- SQLAlchemy ORM;
- queries parametrizadas;
- validação de entrada;
- escaping de saída.

## A07:2025 — Authentication Failures

Controles:

- password hashing;
- MFA;
- rate limiting;
- sessão segura;
- Logout;
- mensagens genéricas.

## A09:2025 — Security Logging & Alerting Failures

Controles:

- Login Audit;
- MFA Audit;
- CRUD Audit;
- eventos administrativos.

Um mecanismo simples de alertas complementa a auditoria. Falhas de Login/MFA,
contas inativas, bloqueios por rate limiting, acessos administrativos negados e
erros internos dos fluxos sensíveis geram `SecurityAlert` com severidade
`WARNING` ou `ERROR`. Eventos equivalentes são agregados por 15 minutos, com
contagem e estado de revisão, e ficam visíveis somente aos Administradores em
`/admin/security-alerts`. `CRITICAL` está reservado para condições realmente
graves e não é atribuído automaticamente a tentativas individuais.

Referências para a demonstração dos controles implementados:

| Categoria | Código | Testes existentes |
|---|---|---|
| A01 | `app/admin/decorators.py` e rotas dos CRUDs | `tests/test_admin.py`, `tests/test_asset.py` |
| A05 | Services dos CRUDs e templates Jinja2 | `tests/test_listings.py`, `tests/test_forms_ui.py` |
| A07 | `app/auth/`, `app/account/`, `app/mfa_crypto.py` | `tests/test_auth.py`, `tests/test_mfa.py`, `tests/test_rate_limiting.py` |
| A09 | `app/audit/services.py`, `app/security_alerts.py` | `tests/test_audit.py`, `tests/test_security_alerts.py` |

As evidências de execução desses controles estão em consolidação para a entrega.

---

# Auditoria

Na etapa 02.8 foram introduzidos:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
MFA_FAILURE
MFA_SUCCESS
MFA_ENABLED
MFA_DISABLED
LOGOUT

USER_CREATED
USER_UPDATED
USER_ACTIVATED
USER_DEACTIVATED
USER_ROLE_CHANGED
```

Na etapa 03.1 foram introduzidos:

```text
DATACENTER.CREATE
DATACENTER.UPDATE
DATACENTER.DELETE
```

Na etapa 03.2 foram introduzidos:

```text
ROOM.CREATE
ROOM.UPDATE
ROOM.DELETE
```

Na etapa 03.3 foram introduzidos:

```text
RACK.CREATE
RACK.UPDATE
RACK.DELETE
```

Na etapa 03.4 foram introduzidos:

```text
ASSET.CREATE
ASSET.UPDATE
ASSET.DELETE
```

Na etapa 03.5 foram introduzidos:

```text
VM.CREATE
VM.UPDATE
VM.DELETE
```

Cada evento persiste data/hora UTC, ator e alvo opcionais, `remote_addr`, User-Agent
sanitizado e limitado a 255 caracteres e detalhes JSON controlados. A consulta somente leitura
fica disponível para administradores em `/admin/audit`, com eventos mais recentes
primeiro. Em produção, `ProxyFix` normaliza `remote_addr` a partir de exatamente um
proxy confiável; development e testing ignoram `X-Forwarded-For`.

Os campos `resource_type`, `resource_id` e `result` permitem
identificar recursos de infraestrutura. Nos CRUDs de Datacenters, Salas, Racks, Ativos e Máquinas Virtuais, a
alteração e o AuditLog usam a mesma transação; os fluxos anteriores mantêm o
comportamento já existente.

O log não deverá armazenar:

- senha;
- password hash;
- TOTP;
- MFA Secret;
- recovery code;
- token;
- session ID.

O `AuditLog` registra quem fez o quê; o `SecurityAlert` registra possíveis abusos
ou falhas de segurança. Alertas persistem tipo, severidade, usuário opcional,
`remote_addr`, User-Agent limitado, endpoint, primeira/última ocorrência, contagem
e estado, nunca formulário ou cabeçalhos sensíveis. `X-Forwarded-For` somente
influencia esse valor em produção, atrás do único proxy controlado previsto.

A documentação prevê retenção de 90 dias para alertas, sujeita à política institucional.
Não há retenção automática, exportação ou integração com SIEM/syslog remoto
na implementação atual. Isso não se confunde com a coleta dos logs técnicos pelo
journald no serviço systemd.

---

# Estrutura do Projeto

Estrutura atual resumida:

```text
inframanager/
│
├── app/
│   ├── models/
│   ├── auth/
│   ├── dashboard/
│   ├── asset/
│   ├── virtual_machine/
│   ├── datacenter/
│   ├── room/
│   ├── rack/
│   ├── admin/
│   ├── account/
│   ├── audit/
│   ├── templates/
│   └── static/
│
├── deploy/
├── migrations/
├── tests/
├── docs/
├── instance/
│
├── .github/
│   └── workflows/
│
├── .env.example
├── .gitignore
├── AGENTS.md
├── ARCHITECTURE.md
├── PLANEJAMENTO.md
├── REQUIREMENTS.md
├── SECURITY.md
├── README.md
├── DEPLOYMENT.md
├── requirements.txt
├── requirements-dev.txt
├── config.py
├── gunicorn.conf.py
├── run.py
└── wsgi.py
```

---

# Infraestrutura OCI

A OCI já foi implantada, incluindo o deploy com Nginx, Gunicorn e systemd.
A topologia de referência para conferir e organizar as evidências é:

```text
OCI Compartment
└── VCN
    ├── Internet Gateway ◄── Internet
    └── Public Subnet
        └── Security List / NSG
            └── Ubuntu Server + IP público
                ├── UFW
                ├── Fail2Ban
                ├── Nginx
                ├── Gunicorn
                ├── Flask
                └── SQLite
```

As evidências deverão comprovar compartment, VCN, subnet pública, internet gateway, security list e/ou NSG, criação da instância, IP público atribuído e instância no estado `Running`/em execução.

---

# Portas

Somente portas necessárias deverão estar expostas:

```text
22/tcp
80/tcp
443/tcp
```

Gunicorn está configurado para escutar em `127.0.0.1:8000`. A verificação externa
de portas e das regras de firewall deve integrar as evidências da implantação.

---

# SSH

A administração do servidor exige chave SSH, independentemente da autenticação
Git via HTTPS utilizada no ambiente de desenvolvimento.

A desativação da autenticação SSH por senha precisa constar na evidência da
configuração efetiva do servidor.

Fail2Ban deverá utilizar pelo menos a configuração determinada pela atividade:

```text
maxretry = 4
bantime = 24h
```

A configuração ativa e o funcionamento do bloqueio permanecem sujeitos à
comprovação acadêmica.

---

# HTTPS

O requisito HTTPS da entrega utiliza:

```text
Let's Encrypt
+
Certbot >= 5.4
+
Nginx
```

O procedimento previsto exige certificado emitido para o IP público com o perfil `shortlived`, a opção `--ip-address` e um método suportado, preferencialmente `webroot`. O fluxo deverá ser validado primeiro em staging. O procedimento requer configuração explícita no Nginx dos arquivos emitidos para o IP público.

O requisito de renovação automática inclui `deploy-hook` para recarregar o Nginx.
A emissão, o teste em staging, o redirecionamento e a renovação precisam de
evidências formais; os exemplos versionados não comprovam sua execução.

Fluxo:

```text
HTTP
 │
 ▼
301 Redirect
 │
 ▼
HTTPS
```

O servidor deverá ser submetido ao Qualys SSL Labs.

Critérios obrigatórios:

```text
SSL Labs: A
PQC: habilitado
```


---

# GitHub

O repositório é público: [InfraManager](https://github.com/rodrigopneves/InfraManager).
A conta utiliza 2FA habilitado, conforme confirmação do responsável pelo projeto.

O remote `origin` usa HTTPS. A autenticação Git é feita pelo GitHub CLI, configurado
como helper (`gh auth git-credential`), sem usar a senha da conta para push/pull.
O responsável confirmou a ausência de credenciais armazenadas em texto simples
e de credenciais vazadas. Esta revisão documental não constitui uma nova auditoria
do histórico Git ou do armazenamento de credenciais da conta.

O `.gitignore` protege `.env`, variações de ambiente, bancos locais, `instance/`,
ambientes virtuais, logs e artefatos de testes. `.env.example` contém placeholders.
Há uma lacuna na proteção de chaves: o arquivo atual não inclui regras gerais para
`*.pem`, `*.key`, `id_rsa` e `id_ed25519`; portanto, não se afirma que esses nomes
estejam cobertos fora dos diretórios já ignorados. Chaves devem permanecer fora do
repositório. A correção desse arquivo está fora desta revisão exclusiva do README.

---

# Proteção de Segredos

Nunca deverão entrar no Git:

```text
.env
*.pem
*.key
*.db

private keys
passwords
OCI credentials
GitHub tokens
TOTP secrets
real SECRET_KEY
```

---

# CI/CD

GitHub Actions está implementado em [.github/workflows/ci.yml](.github/workflows/ci.yml).
O workflow executa integração contínua em todo `push` (incluindo `main`) e
`pull_request`, com permissão `contents: read`, Ubuntu 24.04 e Python 3.14.4.

Pipeline atual, na ordem do workflow:

```text
Checkout
   ↓
Python Setup
   ↓
Instalação de requirements-dev.txt
   ↓
pip check
   ↓
pip-audit (requirements.txt)
   ↓
Ruff
   ↓
pytest com cobertura de linhas e branches
   ↓
compileall (app e tests)
```

O job de qualidade tem timeout de 15 minutos. Falhas nas verificações impedem sua
conclusão com sucesso. O workflow não utiliza GitHub Secrets e não contém etapas
de deploy, conexão à OCI, migrations remotas, reinício de serviços ou health check
pós-deploy. A implantação realizada na OCI é independente desta pipeline.
O deploy automático permanece pendente para a entrega acadêmica.

---

# Testes

A suíte em `tests/` contém testes para:

- Login;
- Login inválido;
- MFA;
- Logout;
- usuários desabilitados;
- rotas protegidas;
- RBAC;
- CRUD;
- validação;
- CSRF;
- auditoria.

Ferramentas de teste e qualidade:

```text
pytest
pytest-cov
Ruff
pip-audit
```

---

# Documentação Técnica

Arquivos principais:

```text
PLANEJAMENTO.md
```

Visão estratégica e organização do projeto.

```text
REQUIREMENTS.md
```

Requisitos funcionais e não funcionais.

```text
ARCHITECTURE.md
```

Arquitetura técnica.

```text
SECURITY.md
```

Controles e decisões de segurança.

```text
AGENTS.md
```

Instruções para agentes de IA.

```text
DEPLOYMENT.md
```

Runbook de operação, backup, restore e rotação de chave MFA; ainda contém texto
de preparação e não comprova por si só a implantação.

```text
README.md
```

Documento principal do projeto e relatório final da entrega.

---

# Uso de Inteligência Artificial

O projeto utiliza o Codex integrado ao ambiente de desenvolvimento, com revisão
humana das decisões e alterações.

Fluxo:

```text
Requisito
   │
   ▼
Planejamento
   │
   ▼
Codex
   │
   ▼
Implementação
   │
   ▼
Testes
   │
   ▼
Code Review
   │
   ▼
Security Review
   │
   ▼
Revisão humana
```

As principais interações poderão ser documentadas na pasta:

```text
docs/ia/
```

---

# Evidências

A coleta e a organização das evidências estão em andamento. Os caminhos abaixo
são uma organização proposta, não uma relação de arquivos já entregues.

Exemplo:

```text
docs/evidencias/

development/
security/
oci/
github/
cicd/
application/
```

Possíveis evidências:

- VS Code + Codex;
- Login;
- MFA;
- Dashboard;
- RBAC;
- CRUD;
- auditoria;
- OCI;
- SSH;
- Fail2Ban;
- firewall;
- HTTPS;
- SSL Labs;
- PQC;
- GitHub;
- GitHub Actions;
- deploy.

Nenhuma evidência deverá conter segredos.

---

# Roadmap

Itens marcados indicam implementação ou confirmação do responsável; os demais
continuam pendentes de implementação ou comprovação, conforme indicado.

## Fase 0 — Planejamento

- [x] Planejamento geral
- [x] Requirements
- [x] Architecture
- [x] Security
- [x] AGENTS
- [x] README inicial

## Fase 1 — Ambiente

- [x] Python
- [x] Git
- [x] VS Code
- [x] Codex
- [x] ambiente virtual
- [x] repositório GitHub

## Fase 2 — Aplicação Base

- [x] estrutura Flask
- [x] Application Factory
- [x] Blueprints
- [x] SQLAlchemy
- [x] migrations

## Fase 3 — Autenticação

- [x] Users
- [x] Login
- [x] Logout
- [x] password hashing
- [x] sessão

## Fase 4 — MFA

- [x] TOTP
- [x] QR Code
- [ ] Recovery Codes — implementação pendente
- [x] testes
- [x] primeiro acesso bloqueado na configuração antes do Dashboard

## Fase 5 — RBAC

- [x] ADMIN
- [x] OPERATOR
- [x] VIEWER
- [x] testes de autorização

## Fase 6 — CRUD

- [x] Ativos
- [x] Máquinas Virtuais
- [x] CRUD completo de Datacenter
- [x] CRUD completo de Sala
- [x] CRUD completo de Rack

## Fase 7 — Auditoria

- [x] AuditLog
- [x] eventos de autenticação e administração de usuários
- [x] consulta administrativa
- [x] alertas simples de segurança

## Fase 8 — Segurança

- [x] CSRF
- [x] Rate Limiting
- [x] Headers HTTP e cache de respostas sensíveis no Flask
- [ ] Security Review
- [x] Controles OWASP documentados no README

## Fase 9 — OCI

- [x] Implantação OCI realizada, conforme informação do responsável
- [x] Deploy com Nginx, Gunicorn e systemd
- [ ] Consolidar evidências de Compartment, VCN, subnet pública e Internet Gateway
- [ ] Consolidar evidências de Security List/NSG, criação da instância e IP público
- [ ] Registrar instância em execução e sistema operacional
- [ ] Comprovar SSH por chave e autenticação por senha desabilitada
- [ ] Comprovar Fail2Ban (`maxretry = 4`, `bantime = 24h`) e UFW

## Fase 10 — HTTPS

- [ ] Certbot `>= 5.4`
- [ ] certificado Let's Encrypt para IP público
- [ ] renovação automática com recarga do Nginx
- [ ] Let's Encrypt
- [ ] redirect
- [ ] SSL Labs A
- [ ] PQC

## Fase 11 — CI/CD

- [x] GitHub Actions — workflow de CI implementado
- [x] Lint, testes com cobertura e auditoria de dependências na pipeline
- [x] Endpoint `/health` implementado na aplicação
- [ ] Deploy automático pela pipeline
- [ ] Health check pós-deploy na pipeline

O workflow atual não utiliza Secrets; eventual autenticação do deploy ainda
precisa ser implementada com proteção das credenciais.

## Fase 12 — Entrega — em andamento

- [ ] Aprovação do README final
- [ ] Consolidação das evidências
- [ ] Validação acadêmica dos controles OWASP
- [ ] Conclusão do checklist acadêmico
- [ ] Revisão final e entrega

---

# Checklist Acadêmico

Os itens marcados refletem o código/documentação atual ou as confirmações do
responsável identificadas acima. Itens externos sem comprovação formal seguem
pendentes, mesmo quando a implantação geral já foi realizada.

- [ ] aplicação acessível publicamente — registrar evidência de acesso;
- [ ] Ubuntu Server ou Debian — registrar versão da instância;
- [x] Nginx — integra o deploy realizado;
- [ ] SSH por chave — comprovar configuração efetiva;
- [ ] Fail2Ban — comprovar configuração e bloqueio;
- [ ] HTTPS — consolidar evidência do certificado válido;
- [ ] redirect HTTP → HTTPS — comprovar resposta;
- [ ] SSL Labs A;
- [ ] PQC;
- [x] GitHub público — confirmado pelo responsável;
- [x] GitHub 2FA — confirmado pelo responsável;
- [x] autenticação Git via HTTPS com GitHub CLI — helper configurado;
- [x] `.gitignore` — implementado, com lacuna para chaves descrita na seção GitHub;
- [x] ausência de credenciais vazadas — confirmada pelo responsável;
- [x] Login — código e testes em `app/auth/` e `tests/test_auth.py`;
- [x] página interna protegida — Dashboard e testes de acesso;
- [x] Logout — POST protegido e testes de encerramento de sessão;
- [x] IA integrada ao desenvolvimento — VS Code e Codex;
- [x] OWASP documentado — controles e referências técnicas neste README;
- [x] GitHub Actions — `.github/workflows/ci.yml`;
- [ ] deploy automático.

A conclusão acadêmica depende das evidências pendentes e da revisão final dos
critérios da atividade, não apenas da presença do código ou de exemplos de deploy.

---

# Princípio do Projeto

> O InfraManager deverá ser simples o suficiente para ser compreendido integralmente, funcional o suficiente para representar uma aplicação real e seguro o suficiente para demonstrar a aplicação prática de Secure by Design.

Funcionalidades extras somente deverão ser implementadas depois que o MVP estiver integralmente funcional, testado, seguro e implantado.
