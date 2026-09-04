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

O projeto será desenvolvido aplicando princípios de **Secure by Design**, **Secure by Default**, OWASP Top 10:2025, Cloud Computing e CI/CD.

---

## Status do Projeto

**Status atual:** etapa 02 concluída e estabilizada

```text
Planejamento       ✅
Requisitos         ✅
Arquitetura        ✅
Segurança          ✅
AGENTS.md           ✅
Desenvolvimento     🚧
Testes 02 e 03       ✅
OCI                 ⏳
CI/CD               ⏳
Documentação final  ⏳
```

As etapas 02, 03.1, 03.2 e 03.3 entregam Application Factory, persistência e migrations,
autenticação, CSRF, rate limiting, gestão administrativa de usuários, RBAC, MFA
TOTP opcional, auditoria e os CRUDs de Datacenters, Salas e Racks. O ponto WSGI padrão é
`wsgi:app`; `run.py` permanece como entrada de desenvolvimento e para comandos
Flask.

Débitos conhecidos para hardening e produção:

1. `mfa_secret` ainda não possui criptografia de campo em repouso;
2. o Flask-Limiter utiliza `memory://`, inadequado para múltiplos workers;
3. o IP real atrás do proxy ainda não é tratado com `ProxyFix` confiável;
4. não existe armazenamento compartilhado como Redis;
5. não existe integração com SIEM;
6. a auditoria não possui retenção automática;
7. MFA ainda é opcional por usuário;
8. a interface visual permanece básica.

Esses itens não impedem o uso acadêmico atual, mas devem ser tratados nas etapas
correspondentes antes de considerar a aplicação pronta para produção.

---

# Objetivo Acadêmico

O projeto foi definido para atender aos requisitos da disciplina **Projeto Aplicado: Práticas de Mercado**.

A atividade exige a construção de uma aplicação web hospedada em nuvem pública utilizando recursos gratuitos, com Ubuntu Server ou Debian, Nginx ou Apache, acesso público pela internet e aplicação de controles de segurança. fileciteturn0file0L21-L46

Também são requisitos da atividade:

- repositório público no GitHub;
- prevenção de vazamento de credenciais;
- utilização de ambiente de desenvolvimento assistido por IA;
- Login;
- página interna protegida;
- Logout funcional;
- mitigação documentada de pelo menos três categorias da OWASP Top 10:2025;
- CI/CD utilizando GitHub Actions. fileciteturn0file0L50-L69 fileciteturn0file0L73-L97 fileciteturn0file0L101-L129

---

# Visão Geral

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

O ambiente principal previsto é:

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

A IA será utilizada para:

- planejamento;
- implementação;
- criação de testes;
- code review;
- refatoração;
- auditoria de segurança;
- documentação.

O enunciado da atividade permite Antigravity ou ambiente similar baseado em IA. fileciteturn0file0L83-L85

---

# Módulos do Sistema

O MVP será composto pelos seguintes módulos:

```text
InfraManager
│
├── Autenticação
│   ├── Login
│   ├── MFA
│   ├── Recovery Codes
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

Fluxo previsto:

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

O MFA é obrigatório para todos os usuários. No primeiro acesso, após a validação da senha, o usuário deverá configurar e confirmar o TOTP antes de acessar o Dashboard. A sessão autenticada definitiva somente será criada depois do código válido.

O MFA é um requisito adicional de segurança adotado pelo InfraManager, e não uma exigência direta do professor ou do enunciado acadêmico.

Estado incremental: a etapa 02.7 disponibiliza ativação TOTP opcional por usuário
e exige o segundo fator sempre que ele estiver ativo. A obrigatoriedade no primeiro
acesso para todas as contas continua sendo requisito do MVP, mas ainda não está
aplicada nesta etapa.

---

# MFA

O sistema utilizará TOTP compatível com aplicativos autenticadores.

Exemplos:

- Microsoft Authenticator;
- Google Authenticator;
- Bitwarden;
- Authy;
- outros aplicativos TOTP.

Também serão implementados códigos de recuperação de uso único.

---

# Perfis de Acesso

O sistema possuirá inicialmente três perfis.

Os perfis serão armazenados diretamente em `User.role`, restrito a `ADMIN`, `OPERATOR` e `VIEWER`; não haverá entidade ou tabela `Role` separada no MVP.

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
- cadastrar;
- editar.

Não poderá executar determinadas operações administrativas ou exclusões críticas.

## VIEWER

Pode:

- visualizar;
- pesquisar;
- utilizar filtros.

Não poderá modificar dados.

---

# Gestão de Ativos

O módulo de ativos permitirá:

- cadastro;
- visualização;
- edição;
- exclusão;
- pesquisa;
- filtros.

Tipos previstos:

- Servidor;
- Storage;
- Switch;
- Firewall;
- Access Point;
- Notebook;
- Desktop;
- Appliance;
- Outro.

---

# Máquinas Virtuais

O módulo permitirá gerenciamento de:

- hostname;
- IP;
- sistema operacional;
- ambiente;
- vCPU;
- RAM;
- armazenamento;
- host;
- cluster;
- aplicação;
- responsável;
- status.

Ambientes previstos:

```text
Produção
Homologação
Desenvolvimento
Teste
```

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

Um ativo físico poderá opcionalmente estar associado a um rack.

Datacenter, Sala e Rack possuem CRUD completo.
Cada Sala pertence obrigatoriamente a um Datacenter e seu código é único dentro
desse Datacenter. Cada Rack pertence a uma Sala, possui capacidade entre 1 e 100 U
e código único nessa Sala. Escritas aplicam autorização server-side, validação,
CSRF, auditoria e verificação de dependências. Datacenters com Salas e Salas com
Racks não podem ser excluídos.

---

# Dashboard

O Dashboard deverá apresentar indicadores como:

```text
Ativos físicos
Máquinas virtuais
Datacenters
Racks

Ativos ativos
Ativos em manutenção

VMs ligadas
VMs desligadas
```

Também poderá apresentar os últimos registros modificados.

---

# Segurança

O projeto seguirá os seguintes princípios:

```text
Secure by Design
Secure by Default
Least Privilege
Defense in Depth
Deny by Default
```

Serão utilizados controles como:

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

A atividade exige mitigação de pelo menos três categorias OWASP e sua documentação no README final. fileciteturn0file0L91-L97

O InfraManager pretende demonstrar principalmente:

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

Um mecanismo simples de alertas complementará a auditoria. Falhas repetidas de Login/MFA, bloqueios por rate limiting e tentativas de acesso administrativo negadas gerarão alertas `WARNING` ou `CRITICAL`, com data/hora, origem resumida, contagem e estado de revisão, visíveis aos Administradores. Integrações externas não fazem parte do MVP.

A documentação definitiva será atualizada durante o desenvolvimento.

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

Cada evento persiste data/hora UTC, ator e alvo opcionais, `remote_addr`, User-Agent
limitado a 255 caracteres e detalhes JSON controlados. A consulta somente leitura
fica disponível para administradores em `/admin/audit`, com eventos mais recentes
primeiro. Cabeçalhos de proxy não são interpretados até a configuração de
Nginx/ProxyFix.

A etapa 03.1 também acrescentou `resource_type`, `resource_id` e `result` para
identificar recursos de infraestrutura. Nos CRUDs de Datacenters, Salas e Racks, a
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

Não há nesta etapa retenção automática, exportação, integração com SIEM/syslog,
correlação ou alertas. Eventos de ativos, VMs e dos demais módulos de infraestrutura
serão adicionados com os respectivos módulos.

---

# Estrutura do Projeto

Estrutura planejada:

```text
inframanager/
│
├── app/
│   ├── models/
│   ├── auth/
│   ├── dashboard/
│   ├── assets/
│   ├── virtual_machines/
│   ├── datacenter/
│   ├── room/
│   ├── rack/
│   ├── users/
│   ├── audit/
│   ├── templates/
│   └── static/
│
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
├── requirements.txt
└── wsgi.py
```

---

# Infraestrutura OCI

Arquitetura prevista:

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

Gunicorn não será exposto diretamente à internet.

---

# SSH

A administração do servidor será realizada utilizando chave SSH.

Autenticação por senha será desabilitada.

Fail2Ban deverá utilizar pelo menos a configuração determinada pela atividade:

```text
maxretry = 4
bantime = 24h
```

O requisito é explícito no enunciado. fileciteturn0file0L41-L42

---

# HTTPS

Produção deverá utilizar:

```text
Let's Encrypt
+
Certbot >= 5.4
+
Nginx
```

O certificado será emitido para o IP público com o perfil `shortlived`, a opção `--ip-address` e um método suportado, preferencialmente `webroot`. O fluxo deverá ser validado primeiro em staging. O Nginx será configurado explicitamente para usar os arquivos emitidos, pois a instalação automática pelo plugin Nginx não cobre certificados de IP.

Como certificados Let's Encrypt para IP público são de curta duração, a renovação será automatizada e usará `deploy-hook` para recarregar o Nginx.

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

fileciteturn0file0L43-L46

---

# GitHub

O projeto será armazenado em repositório público conforme requisito acadêmico. fileciteturn0file0L60-L69

Nenhuma informação confidencial deverá ser versionada.

Checklist de acesso ao GitHub:

- 2FA habilitado na conta;
- operações Git autenticadas por chave SSH protegida ou PAT de escopo mínimo;
- senha da conta não utilizada para push/pull;
- chaves e tokens ausentes do repositório, logs e evidências.

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

Fluxo de integração e entrega:

```text
VS Code + Codex
       │
       ▼
      Git
       │
       ▼
    GitHub
       │
       ▼
GitHub Actions
       │
       ├── Lint
       ├── Tests
       ├── Security Checks
       │
       └── Deploy
                │
                ▼
               OCI
```

Push para `main` deverá iniciar automaticamente a pipeline, conforme exigência da atividade. fileciteturn0file0L123-L129

---

# Pipeline Prevista

```text
Checkout
   │
   ▼
Python Setup
   │
   ▼
Dependencies
   │
   ▼
Lint
   │
   ▼
Tests
   │
   ▼
Security Checks
   │
   ▼
Deploy
   │
   ▼
Health Check
```

Falha crítica deverá impedir o deploy.

---

# Testes

Serão desenvolvidos testes para:

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

Ferramenta:

```text
pytest
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
README.md
```

Documento principal do projeto e relatório final da entrega.

---

# Uso de Inteligência Artificial

O projeto utilizará o Codex como agente integrado ao ambiente de desenvolvimento.

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

Serão mantidas evidências da execução do projeto.

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

## Fase 0 — Planejamento

- [x] Planejamento geral
- [x] Requirements
- [x] Architecture
- [x] Security
- [x] AGENTS
- [x] README inicial

## Fase 1 — Ambiente

- [ ] Python
- [ ] Git
- [ ] VS Code
- [ ] Codex
- [ ] ambiente virtual
- [ ] repositório GitHub

## Fase 2 — Aplicação Base

- [ ] estrutura Flask
- [ ] Application Factory
- [ ] Blueprints
- [ ] SQLAlchemy
- [ ] migrations

## Fase 3 — Autenticação

- [ ] Users
- [ ] Login
- [ ] Logout
- [ ] password hashing
- [ ] sessão

## Fase 4 — MFA

- [ ] TOTP
- [ ] QR Code
- [ ] Recovery Codes
- [ ] testes
- [ ] primeiro acesso bloqueado na configuração antes do Dashboard

## Fase 5 — RBAC

- [ ] ADMIN
- [ ] OPERATOR
- [ ] VIEWER
- [ ] testes de autorização

## Fase 6 — CRUD

- [ ] Ativos
- [ ] Máquinas Virtuais
- [x] CRUD completo de Datacenter
- [x] CRUD completo de Sala
- [x] CRUD completo de Rack

## Fase 7 — Auditoria

- [x] AuditLog
- [x] eventos de autenticação e administração de usuários
- [x] consulta administrativa
- [ ] alertas simples de segurança

## Fase 8 — Segurança

- [ ] CSRF
- [ ] Rate Limiting
- [ ] Headers
- [ ] Security Review
- [ ] OWASP

## Fase 9 — OCI

- [ ] Compartment
- [ ] VCN
- [ ] Subnet pública
- [ ] Internet Gateway
- [ ] Security List/NSG
- [ ] criação da instância
- [ ] IP público
- [ ] instância em execução
- [ ] VM Ubuntu
- [ ] SSH
- [ ] Fail2Ban
- [ ] UFW
- [ ] Nginx
- [ ] Gunicorn

## Fase 10 — HTTPS

- [ ] Certbot `>= 5.4`
- [ ] certificado Let's Encrypt para IP público
- [ ] renovação automática com recarga do Nginx
- [ ] Let's Encrypt
- [ ] redirect
- [ ] SSL Labs A
- [ ] PQC

## Fase 11 — CI/CD

- [ ] GitHub Actions
- [ ] GitHub Secrets
- [ ] testes
- [ ] deploy
- [ ] health check

## Fase 12 — Entrega

- [ ] README final
- [ ] evidências
- [ ] validação OWASP
- [ ] checklist acadêmico
- [ ] revisão final

---

# Checklist Acadêmico

Antes da entrega deverá ser validado:

- [ ] aplicação acessível publicamente;
- [ ] Ubuntu Server ou Debian;
- [ ] Nginx ou Apache;
- [ ] SSH por chave;
- [ ] Fail2Ban;
- [ ] HTTPS;
- [ ] redirect HTTP → HTTPS;
- [ ] SSL Labs A;
- [ ] PQC;
- [ ] GitHub público;
- [ ] GitHub 2FA;
- [ ] autenticação Git por SSH ou PAT de escopo mínimo;
- [ ] `.gitignore`;
- [ ] nenhuma credencial vazada;
- [ ] Login;
- [ ] página interna;
- [ ] Logout;
- [ ] IA integrada ao desenvolvimento;
- [ ] OWASP documentado;
- [ ] GitHub Actions;
- [ ] deploy automático.

Esse checklist corresponde aos principais critérios finais definidos no enunciado da atividade. fileciteturn0file0L133-L147

---

# Princípio do Projeto

> O InfraManager deverá ser simples o suficiente para ser compreendido integralmente, funcional o suficiente para representar uma aplicação real e seguro o suficiente para demonstrar a aplicação prática de Secure by Design.

Funcionalidades extras somente deverão ser implementadas depois que o MVP estiver integralmente funcional, testado, seguro e implantado.
