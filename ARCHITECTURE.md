# ARCHITECTURE.md — InfraManager

## 1. Objetivo

Este documento define a arquitetura técnica inicial do **InfraManager**, sistema web destinado ao gerenciamento de:

- ativos de TI;
- máquinas virtuais;
- datacenters;
- salas;
- racks;
- usuários;
- perfis de acesso;
- autenticação multifator;
- auditoria.

A arquitetura deverá priorizar:

- simplicidade;
- segurança;
- organização;
- testabilidade;
- manutenibilidade;
- aderência aos requisitos acadêmicos;
- facilidade de implantação na Oracle Cloud Infrastructure.

---

# 2. Visão Geral da Arquitetura

O InfraManager utilizará arquitetura web monolítica modular.

```text
                        INTERNET
                           │
                         HTTPS
                           │
                           ▼
                    ┌─────────────┐
                    │    Nginx    │
                    │ Reverse     │
                    │ Proxy       │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Gunicorn   │
                    │ WSGI Server │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Flask    │
                    │ Application │
                    └──────┬──────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
         Blueprints     Segurança     Auditoria
             │
             ▼
          Services
             │
             ▼
           Models
             │
             ▼
        SQLAlchemy ORM
             │
             ▼
           SQLite
```

A aplicação Flask não deverá ser exposta diretamente à internet.

---

# 3. Arquitetura de Produção

A infraestrutura de produção será hospedada na Oracle Cloud Infrastructure.

```text
                        INTERNET
                           │
                           ▼
                   Oracle Cloud
                          │
                     Compartment
                          │
                         VCN
                           │
                 Internet Gateway
                           │
                           ▼
                    Public Subnet
                           │
                           ▼
                    Security List
                         / NSG
                           │
                           ▼
                  ┌─────────────────┐
                  │ Ubuntu Server   │
                  │ IP público      │
                  │                 │
                  │ UFW             │
                  │ Fail2Ban        │
                  │ Nginx           │
                  │ Gunicorn        │
                  │ Flask           │
                  │ SQLite          │
                  └─────────────────┘
```

O servidor deverá possuir IP público para atender ao requisito acadêmico de disponibilidade via internet.

A criação e a operação da infraestrutura deverão ser comprovadas por evidências do compartment, VCN, subnet pública, internet gateway, security list e/ou NSG, tela de criação da instância, IP público atribuído e instância no estado `Running`/em execução.

---

# 4. Componentes Principais

## 4.1 Nginx

Responsabilidades:

- receber conexões HTTP/HTTPS;
- terminar TLS;
- redirecionar HTTP para HTTPS;
- encaminhar requisições para Gunicorn;
- adicionar cabeçalhos de segurança;
- servir arquivos estáticos quando apropriado;
- limitar exposição direta da aplicação.

Fluxo:

```text
Cliente
   │
 HTTPS
   │
   ▼
Nginx
   │
 HTTP local
   ▼
Gunicorn
```

Gunicorn deverá escutar somente na interface local ou socket Unix.

Em produção, o fluxo completo será cliente → Nginx → Gunicorn → Flask. A factory
envolve a aplicação com `ProxyFix`, confiando em exatamente um proxy para
`X-Forwarded-For` e `X-Forwarded-Proto`. `X-Forwarded-Host`, porta e prefixo não
são confiados. Com isso, `request.remote_addr` representa o cliente e o esquema da
requisição representa o HTTPS externo. Development e testing não aplicam o
middleware e ignoram esses cabeçalhos. A configuração real do Nginx permanece para
etapa posterior, e o Gunicorn não poderá ser acessível diretamente pela Internet.

---

# 5. Gunicorn

Gunicorn será utilizado como servidor WSGI.

O módulo `wsgi.py` exporta a aplicação Flask como `wsgi:app`, carregada a partir da
Application Factory. O arquivo `run.py` mantém a entrada de desenvolvimento e pode
ser usado por comandos como `flask --app run.py routes`.

`gunicorn.conf.py` define o bind local `127.0.0.1:8000`, dois workers síncronos e
timeouts conservadores para a VM pequena e o SQLite. Access e error logs usam
stdout/stderr; o formato de acesso omite query string, cookies, Authorization e
corpo. Aumentar workers exige medição, pois as escritas SQLite permanecem
serializadas.

Responsabilidades:

- executar a aplicação Flask;
- gerenciar workers;
- receber requisições encaminhadas pelo Nginx;
- isolar a aplicação da exposição direta à internet.

Exemplo conceitual:

```text
Nginx
  │
  ▼
unix:/run/inframanager.sock
  │
  ▼
Gunicorn
  │
  ▼
Flask
```

---

# 6. Flask

Flask será utilizado como framework principal.

A aplicação será estruturada utilizando:

- Application Factory;
- Blueprints;
- SQLAlchemy;
- Flask-Login;
- Flask-WTF;
- Flask-Limiter;
- Flask-Migrate.

A aplicação não deverá concentrar toda a lógica em um único arquivo.

---

# 7. Application Factory

A aplicação deverá utilizar o padrão Application Factory.

Exemplo conceitual:

```python
def create_app(config_name=None):
    app = Flask(__name__)

    configure_app(app)
    initialize_extensions(app)
    register_blueprints(app)

    return app
```

Benefícios:

- facilita testes;
- facilita ambientes diferentes;
- evita objetos globais desnecessários;
- melhora modularização.

---

# 8. Blueprints

O sistema será dividido inicialmente nos seguintes Blueprints:

```text
auth
account
dashboard
asset
virtual_machine
datacenter
room
rack
users
audit
```

Estrutura conceitual:

```text
app/
│
├── auth/
├── account/
├── dashboard/
├── asset/
├── virtual_machine/
├── datacenter/
├── room/
├── rack/
├── users/
└── audit/
```

---

# 9. Estrutura de Diretórios

Estrutura inicial proposta:

```text
inframanager/
│
├── app/
│   │
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   │   ├── user.py
│   │   ├── asset.py
│   │   ├── virtual_machine.py
│   │   ├── datacenter.py
│   │   ├── room.py
│   │   ├── rack.py
│   │   ├── audit_log.py
│   │   └── security_alert.py
│   │
│   ├── auth/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   ├── services.py
│   │   └── decorators.py
│   │
│   ├── account/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── dashboard/
│   │   └── routes.py
│   │
│   ├── asset/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── virtual_machine/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── datacenter/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── room/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── rack/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── users/
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── services.py
│   │
│   ├── audit/
│   │   ├── routes.py
│   │   └── services.py
│   │
│   ├── templates/
│   │
│   └── static/
│
├── migrations/
│
├── tests/
│
├── docs/
│
├── instance/
│
├── .github/
│   └── workflows/
│
├── .env.example
├── .gitignore
├── AGENTS.md
├── ARCHITECTURE.md
├── REQUIREMENTS.md
├── SECURITY.md
├── README.md
├── requirements.txt
└── wsgi.py
```

---

# 10. Camadas da Aplicação

O projeto utilizará separação simples entre responsabilidades.

```text
Route
  │
  ▼
Service
  │
  ▼
Model
  │
  ▼
Database
```

## Route

Responsável por:

- receber requisição;
- verificar autenticação;
- verificar autorização;
- validar formulário;
- chamar Service;
- devolver resposta.

---

## Service

Responsável por:

- regras de negócio;
- operações complexas;
- auditoria;
- validações adicionais;
- coordenação entre Models.

---

## Model

Responsável por:

- representar entidades;
- relacionamentos;
- constraints;
- persistência.

A lógica complexa de negócio não deverá ficar diretamente nos templates.

---

# 11. Banco de Dados

O MVP utilizará:

```text
SQLite
+
SQLAlchemy ORM
+
Alembic / Flask-Migrate
```

O banco deverá permanecer fora do repositório Git.

Exemplo:

```text
instance/
└── inframanager.db
```

O arquivo deverá estar presente no `.gitignore`.

Em produção, o path recomendado é
`/var/lib/inframanager/inframanager.db`, fornecido por `DATABASE_URL`. Todas as
conexões SQLite habilitam foreign keys e timeout de 30 segundos. Bancos em arquivo
também usam WAL, permitindo leitores durante uma escrita sem remover a
serialização do escritor. PostgreSQL permanece uma evolução futura caso carga e
concorrência ultrapassem o perfil do MVP.

---

# 12. Entidades Principais

O banco possuirá inicialmente:

```text
User
Asset
VirtualMachine
Datacenter
Room
Rack
AuditLog
RecoveryCode
```

---

# 13. Modelo User

Campos iniciais:

```text
id
name
username
email
password_hash
role
is_active
mfa_enabled
mfa_secret
mfa_last_used_step
created_at
updated_at
last_login_at
```

Possíveis perfis:

```text
ADMIN
OPERATOR
VIEWER
```

O RBAC será representado diretamente pelo campo `User.role`, validado contra os valores técnicos `admin`, `operator` e `viewer`, correspondentes aos perfis ADMIN, OPERATOR e VIEWER. O MVP não possuirá entidade, tabela, relacionamento ou model `Role` separado.

O campo `password_hash` nunca armazenará senha em texto puro.

---

# 14. Modelo RecoveryCode

Campos:

```text
id
user_id
code_hash
used
created_at
used_at
```

Relacionamento:

```text
User
 │
 └── RecoveryCode
```

Os códigos não deverão ser armazenados em texto puro.

---

# 15. Modelo Asset

Implementado na etapa 03.4 com os campos:

```text
id
rack_id
name
asset_tag
serial_number
manufacturer
model
asset_type
rack_unit_start
rack_units
description
status
created_at
updated_at
```

Todo Ativo pertence obrigatoriamente a um Rack. `asset_tag` é normalizado para
maiúsculas e possui unicidade global. Os tipos são controlados e abrangem servidor,
switch, roteador, firewall, storage, appliance, access point, notebook, desktop e
outro. A posição física usa o intervalo inclusivo iniciado por `rack_unit_start` e
com tamanho `rack_units`.

O service rejeita posições além de `Rack.capacity_u` e sobreposições com outros
Ativos do mesmo Rack. A FK usa `ON DELETE RESTRICT`, não há cascade, e Racks com
Ativos não podem ser excluídos. O Blueprint `/assets` pagina 20 itens e carrega a
hierarquia completa sem N+1.

---

# 16. Modelo VirtualMachine

Implementado na etapa 03.5 com os campos:

```text
id
host_asset_id
name
hostname
ip_address
operating_system
environment
vcpu
memory_mb
disk_gb
status
description
created_at
updated_at
```

Relacionamento desejado:

```text
Asset (Host físico)
        │
        ├── VM-01
        ├── VM-02
        └── VM-03
```

O relacionamento com o host é obrigatório e aceita somente Ativos cujo tipo seja
`server`. A FK usa `ON DELETE RESTRICT`, não há cascade, e um Ativo que hospede VMs
não pode ser excluído. O nome da VM possui unicidade global. Endereços IPv4 e IPv6
são validados com a biblioteca padrão `ipaddress`. Recursos são persistidos como
vCPU, memória em MB e disco em GB; não existe controle agregado de capacidade do
host nesta etapa.

O Blueprint `/virtual-machines` pagina 20 registros e carrega antecipadamente a
hierarquia Asset → Rack → Room → Datacenter. Escritas são restritas a
Administradores e persistem `VM.CREATE`, `VM.UPDATE` ou `VM.DELETE` na mesma
transação da alteração.

---

# 17. Modelo Datacenter

Implementado na etapa 03.1 com os campos:

```text
id
name
code
location
description
status
created_at
updated_at
```

`code` é normalizado para maiúsculas e possui unicidade no banco. `status` aceita
somente `active` e `inactive`, com `active` como valor padrão. O Blueprint usa o
prefixo `/datacenters`, pagina as listagens e restringe todas as escritas a
administradores.

---

# 18. Modelo Room

Implementado na etapa 03.2 com os campos:

```text
id
datacenter_id
name
code
description
status
created_at
updated_at
```

Toda Sala pertence obrigatoriamente a um Datacenter. `code` é normalizado para
maiúsculas e possui unicidade composta por `(datacenter_id, code)`. `status` aceita
`active` e `inactive`. O relacionamento `Datacenter.rooms` é 1:N, sem cascade de
exclusão, e a FK SQLite usa `ON DELETE RESTRICT` com `PRAGMA foreign_keys=ON` em
todas as conexões SQLite.

O Blueprint usa o prefixo `/rooms`, lista globalmente com paginação de 20 itens e
restringe escritas a administradores. A tela do Datacenter exibe suas Salas e sua
listagem apresenta a respectiva quantidade sem consultas N+1.

Relacionamento:

```text
Datacenter
    │
    ├── Sala 01
    └── Sala 02
```

---

# 19. Modelo Rack

Implementado na etapa 03.3 com os campos:

```text
id
room_id
name
code
capacity_u
description
status
created_at
updated_at
```

Todo Rack pertence obrigatoriamente a uma Sala. `code` é normalizado para
maiúsculas e possui unicidade composta por `(room_id, code)`. `capacity_u` aceita
inteiros entre 1 e 100, com validação na aplicação e constraint no banco. O
relacionamento `Room.racks` é 1:N, sem cascade de exclusão, e a FK utiliza
`ON DELETE RESTRICT`.

O Blueprint usa o prefixo `/racks`, pagina 20 itens e restringe escritas a
administradores. A listagem carrega Rack, Sala e Datacenter sem N+1; as telas de
Sala mostram os Racks associados e bloqueiam a exclusão quando houver dependências.

Relacionamento:

```text
Datacenter
    │
    ▼
Room
    │
    ▼
Rack
```

---

# 20. Ativo e Rack

Na etapa 03.4, todo Ativo está obrigatoriamente associado a um Rack.

Será previsto no Asset:

```text
rack_id
rack_unit_start
rack_units
```

Essa associação é obrigatória no model atual.

Exemplo:

```text
RACK-01

U42 ─ Switch Core
U41 ─ Switch Core
...
U30 ─ Host VMware
U29 ─ Host VMware
```

O inventário visual completo de rack não faz parte do MVP.

---

# 21. Modelo AuditLog

Campos originais implementados na etapa 02.8:

```text
id
event_type
actor_user_id
target_user_id
ip_address
user_agent
details
created_at
```

Campos opcionais acrescentados na etapa 03.1:

```text
resource_type
resource_id
result
```

`actor_user_id` e `target_user_id` são relacionamentos opcionais distintos com
`User`. Isso permite registrar falhas anônimas de autenticação e identificar o
usuário afetado por uma ação administrativa. A interface trata relações ausentes
sem impedir a consulta.

`details` utiliza JSON compatível com SQLite, limitado a metadados permitidos por
evento. Não recebe objetos arbitrários, formulários, requisições ou sessões. Os
campos opcionais `resource_type`, `resource_id` e `result`, acrescentados na etapa
03.1, identificam recursos de infraestrutura sem alterar eventos anteriores.

Índices simples são mantidos em `event_type`, `created_at`, `actor_user_id` e
`target_user_id`.

Exemplo atual:

```text
event_type: LOGIN_FAILURE
actor_user_id: null
target_user_id: null
ip_address: 192.0.2.10
details: {"reason": "authentication_failed"}
```

As operações de Datacenter, Sala, Rack, Ativo e Máquina Virtual persistem a mudança
e seu evento de auditoria na mesma transação.

---

# 22. Relacionamentos

Modelo conceitual:

```text
User
 │
 ├──────────────┐
 │              │
 ▼              ▼
AuditLog   RecoveryCode


Datacenter
    │
    ▼
Room
    │
    ▼
Rack
    │
    ▼
Asset
    │
    ▼
VirtualMachine
```

Os relacionamentos da hierarquia de infraestrutura são obrigatórios: toda Máquina
Virtual possui um host do tipo Servidor, todo Ativo pertence a um Rack, todo Rack
pertence a uma Sala e toda Sala pertence a um Datacenter.

---

# 23. Fluxo de Autenticação

Fluxo principal:

```text
/login
   │
   ▼
username + password
   │
   ▼
Credenciais válidas?
   │
 ┌─┴──────────────┐
 │                │
Não              Sim
 │                │
 ▼                ▼
Erro       MFA configurado?
                  │
            ┌─────┴─────┐
            │           │
           Não         Sim
            │           │
            ▼           ▼
       /mfa/setup     /mfa
            │           │
       Confirmar      Código TOTP
       código TOTP       │
            └─────┬─────┘
                  ▼
              login_user()
                  │
                  ▼
              Dashboard
```

O MFA é obrigatório para todos os usuários. O primeiro acesso deverá conduzir à configuração e confirmação do TOTP antes do Dashboard. Esse endurecimento é requisito adicional do InfraManager e não exigência direta do professor.

---

# 24. Estado Pré-MFA

Após senha correta e antes da validação MFA, o usuário NÃO deverá ser considerado autenticado.

Deverá existir estado temporário limitado.

Exemplo conceitual:

```text
session["pending_mfa_user_id"]
```

Somente após código TOTP válido:

```python
login_user(user)
```

Isso evita que a primeira etapa seja confundida com autenticação completa.

Esse estado possui somente `user_id` e timestamp, expira após 5 minutos e é
validado novamente contra status e existência do usuário antes da configuração ou
validação do segundo fator. A integridade do estado mantido no cliente depende da
assinatura da sessão Flask.

---

# 25. MFA TOTP

Tecnologia prevista:

```text
PyOTP
```

Ativação:

```text
Usuário
   │
   ▼
Gerar segredo
   │
   ▼
URI TOTP
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

O segredo TOTP deverá receber proteção adequada definida no `SECURITY.md`.

O fluxo usa `PyOTP` com tolerância de uma janela temporal. O QR Code é gerado em
memória como SVG e entregue somente durante o setup autorizado pelo estado pré-MFA.
O Blueprint `account` concentra ativação e desativação; o Blueprint `auth`
concentra a verificação que conclui o login.

O MFA é obrigatório para todos os usuários, sem política de exceção por perfil. O
segredo persistido usa criptografia autenticada Fernet com chave externa ao banco e
ao repositório. O último timestep aceito fica em `mfa_last_used_step`; a atualização
condicional desse campo rejeita timesteps iguais ou anteriores, inclusive diante de
requisições concorrentes.

---

# 26. Controle de Acesso

RBAC será validado no backend.

Possível estrutura:

```python
@roles_required("ADMIN")
def delete_user():
    ...
```

ou:

```python
@permission_required("assets.delete")
```

Para o MVP será utilizado modelo simples baseado em roles.

---

# 27. Matriz de Permissões

| Recurso | Administrador | Operador | Consulta |
|---|---:|---:|---:|
| Dashboard | Sim | Sim | Sim |
| Visualizar ativos | Sim | Sim | Sim |
| Criar ativos | Sim | Não | Não |
| Editar ativos | Sim | Não | Não |
| Excluir ativos | Sim | Não | Não |
| Visualizar VMs | Sim | Sim | Sim |
| Criar VMs | Sim | Não | Não |
| Editar VMs | Sim | Não | Não |
| Excluir VMs | Sim | Não | Não |
| Ver Datacenter | Sim | Sim | Sim |
| Criar/editar Datacenter | Sim | Não | Não |
| Excluir Datacenter | Sim | Não | Não |
| Ver Salas | Sim | Sim | Sim |
| Criar/editar Salas | Sim | Não | Não |
| Excluir Salas | Sim | Não | Não |
| Ver Racks | Sim | Sim | Sim |
| Criar/editar Racks | Sim | Não | Não |
| Excluir Racks | Sim | Não | Não |
| Usuários | Sim | Não | Não |
| Auditoria | Sim | Não | Não |

Datacenter, Sala, Rack, Ativo e Máquina Virtual possuem CRUD completo. Exclusões
respeitam as dependências existentes e todas as operações de escrita aplicam
autorização, validação, CSRF e auditoria.

---

# 28. CSRF

Todos os formulários de alteração utilizarão proteção CSRF.

Rotas sensíveis não deverão executar alterações por GET.

Exemplo proibido:

```text
GET /assets/10/delete
```

Forma desejada:

```text
POST /assets/10/delete
```

com:

- CSRF válido;
- autenticação;
- autorização.

---

# 29. Exclusões

Operações de exclusão deverão exigir:

```text
Usuário autenticado
        +
Permissão adequada
        +
POST
        +
CSRF
        +
Confirmação
```

Sempre que possível, dados importantes deverão ser desativados em vez de fisicamente excluídos.

---

# 30. Validação de Entrada

Validação deverá ocorrer no servidor.

Exemplo de endereço IP:

```text
192.168.10.20
```

deve ser aceito.

Entrada inválida:

```text
999.999.999.999
```

deverá ser rejeitada.

Outras validações:

- tamanho máximo;
- campos obrigatórios;
- enums;
- e-mail;
- inteiros;
- intervalos;
- endereços IP.

---

# 31. Paginação

Listagens deverão possuir arquitetura preparada para paginação.

Exemplo:

```text
/assets?page=2
```

Mesmo que o volume inicial seja pequeno.

---

# 32. Pesquisa e Filtros

Pesquisas deverão utilizar SQLAlchemy.

Nunca deverão montar consultas SQL concatenando diretamente entrada do usuário.

Exemplo:

```text
/assets?q=server
```

Filtros poderão utilizar query parameters:

```text
/assets?status=active&type=server
```

---

# 33. Auditoria de CRUD

Services deverão registrar operações relevantes.

Fluxo conceitual:

```text
Usuário altera VM
       │
       ▼
Authorization
       │
       ▼
Validation
       │
       ▼
Update
       │
       ▼
Commit
       │
       ▼
AuditLog
```

O registro de auditoria deverá ocorrer preferencialmente no mesmo fluxo transacional.

---

# 34. Templates

Frontend utilizará:

```text
Jinja2
+
Bootstrap
+
CSS próprio mínimo
```

Estrutura:

```text
templates/
│
├── base.html
│
├── account/
│   ├── mfa_disable.html
│   └── mfa_setup.html
│
├── admin/
│   ├── audit.html
│   ├── user_form.html
│   └── users.html
│
├── auth/
│   ├── login.html
│   ├── mfa_verify.html
│   └── dashboard.html
│
├── errors/
│   ├── 400.html
│   ├── 403.html
│   ├── 404.html
│   ├── 429.html
│   ├── 500.html
│   └── csrf.html
│
├── macros/
│   └── ui.html
│
├── asset/
├── virtual_machine/
├── datacenter/
├── room/
└── rack/
```

O Dashboard é renderizado por `auth/dashboard.html`; suas consultas agregadas
ficam isoladas em `app/dashboard/services.py`. Componentes repetidos de
listagens, formulários, paginação, estados vazios e páginas de erro utilizam
`templates/macros/ui.html`. Os estilos responsivos e de acessibilidade ficam
centralizados em `static/css/app.css`.

---

# 35. Layout Base

`base.html` deverá concentrar:

- navegação;
- menu;
- mensagens flash;
- imports CSS;
- scripts comuns;
- token CSRF quando necessário.

Páginas deverão utilizar herança Jinja.

---

# 36. Navegação

Menu conceitual:

```text
InfraManager

Dashboard

Infraestrutura
├── Ativos
├── Máquinas Virtuais
└── Datacenter

Administração
├── Usuários
└── Auditoria

Conta
├── Perfil
├── MFA
└── Logout
```

Itens administrativos poderão ser ocultados visualmente conforme o perfil.

Isso NÃO substitui a autorização server-side.

---

# 37. Configuração

A aplicação deverá possuir configurações separadas.

Exemplo:

```text
config.py

DevelopmentConfig
TestingConfig
ProductionConfig
```

Variáveis sensíveis deverão vir de ambiente.

Exemplo:

```text
SECRET_KEY
DATABASE_URL
```

Nunca deverão ser hardcoded com valores de produção.

---

# 38. Ambientes

## Desenvolvimento

```text
Flask development
SQLite
DEBUG controlado
```

## Testes

```text
TestingConfig
Database temporário
CSRF adaptado quando necessário
```

## Produção

```text
Ubuntu
Nginx
Gunicorn
SQLite
HTTPS
DEBUG=False
```

---

# 39. Logging da Aplicação

Logs técnicos deverão ser separados conceitualmente dos AuditLogs.

## Application Log

Exemplos:

- exception;
- erro de banco;
- erro interno;
- inicialização.

## Audit Log

Exemplos:

- usuário realizou login;
- ativo foi alterado;
- VM foi excluída.

Os dois possuem finalidades diferentes.

`LOG_LEVEL` aceita `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`, com `INFO`
como padrão de produção. O nível de log não altera `DEBUG=False`. Flask e Gunicorn
escrevem em stdout/stderr, destinados ao journald pelo exemplo de systemd, sem
arquivos locais obrigatórios ou handlers adicionados repetidamente.

## Alertas de Segurança

O `SecurityAlert` é separado do `AuditLog`: auditoria responde “quem fez o quê”,
enquanto o alerta registra indícios de abuso ou falhas em controles de segurança.
O serviço central abre o alerta na primeira ocorrência e correlaciona eventos com
o mesmo tipo, severidade, usuário, IP e endpoint em uma janela persistente de 15
minutos. Enquanto o alerta estiver
`new`, novas ocorrências incrementam a contagem e atualizam a última ocorrência;
após revisão administrativa, uma nova ocorrência abre outro alerta.

Os níveis persistidos são `WARNING`, `ERROR` e `CRITICAL`; esta etapa não gera
`CRITICAL` automaticamente, reservando-o para condições futuras realmente graves.
A consulta paginada e a revisão ficam em `/admin/security-alerts`, somente para
administradores. Não há e-mail, SMS, SIEM ou expurgo automático no MVP.

---

# 40. Tratamento de Erros

A aplicação deverá possuir handlers para:

```text
400
403
404
429
500
```

Exemplo:

```text
403
Você não possui permissão para executar esta ação.
```

Nenhum stack trace deverá ser exibido em produção.

---

# 41. Rate Limiting

Flask-Limiter poderá ser utilizado.

Rotas prioritárias:

```text
/login
/mfa
/password
```

Limites definitivos serão documentados no `SECURITY.md`.

Na etapa 02, `POST /login` utiliza 5 tentativas em 15 minutos e `POST
/mfa/verify` utiliza 5 tentativas em 5 minutos. Desenvolvimento e testes utilizam
`memory://`. Produção exige Redis compartilhado por meio de
`RATELIMIT_STORAGE_URI`, com esquema `redis://` ou `rediss://`, para manter os
contadores consistentes entre futuros workers Gunicorn. A URI e eventuais
credenciais permanecem fora do Git. Esta etapa adiciona o cliente Python e a
configuração da aplicação, mas não instala nem configura o servidor Redis.

---

# 42. Testes

Estrutura:

```text
tests/
│
├── conftest.py
├── test_auth.py
├── test_mfa.py
├── test_rbac.py
├── test_asset.py
├── test_asset_migration.py
├── test_virtual_machine.py
├── test_virtual_machine_migration.py
├── test_datacenter.py
├── test_room.py
├── test_room_migration.py
├── test_rack.py
├── test_rack_migration.py
└── test_audit.py
```

Serão utilizados:

```text
pytest
Flask Test Client
```

---

# 43. Fixtures

Fixtures deverão permitir:

```text
admin_user
operator_user
viewer_user
authenticated_admin
sample_asset
sample_vm
sample_datacenter
sample_room
sample_rack
```

Isso facilitará testes de autorização e CRUD.

---

# 44. CI/CD

Arquitetura de integração:

```text
Notebook pessoal
       │
       │ git push
       ▼
GitHub
       │
       ▼
GitHub Actions
       │
       ├── lint
       ├── testes
       ├── security checks
       │
       └── deploy
                │
                ▼
               OCI
```

A atividade exige GitHub Actions como mecanismo de CI/CD. fileciteturn0file0L101-L129

---

# 45. Estratégia Inicial de Deploy

GitHub Actions deverá conectar-se à instância OCI por SSH.

Fluxo conceitual:

```text
GitHub Actions
      │
      │ SSH
      ▼
OCI Server
      │
      ├── git pull/deploy
      ├── atualizar dependências
      ├── migration
      ├── restart Gunicorn
      └── health check
```

A chave utilizada deverá ficar protegida por GitHub Secrets.

---

# 46. Serviço Systemd

Gunicorn deverá ser gerenciado pelo systemd.

Exemplo conceitual:

```text
inframanager.service
```

Responsabilidades:

- iniciar no boot;
- reiniciar em falha quando adequado;
- permitir restart durante deploy;
- centralizar logs operacionais.

O exemplo versionado em `deploy/systemd/` usa usuário sem privilégio,
`NoNewPrivileges`, `PrivateTmp`, filesystem somente leitura, home protegido e
`UMask=0027`. Apenas `/var/lib/inframanager` é liberado para escrita.

---

# 47. Health Check

A aplicação deverá possuir endpoint simples:

```text
/health
```

Resposta esperada:

```json
{
  "status": "ok"
}
```

O endpoint não deverá revelar:

- versão detalhada de dependências;
- banco utilizado;
- variáveis;
- configuração interna.

O endpoint executa `SELECT 1`: sucesso retorna 200 com `{"status":"ok"}` e falha
de banco retorna 503 com `{"status":"unavailable"}`. Redis não participa desse
health check e indisponibilidade externa é detectada no uso do rate limiting.

---

# 48. HTTPS

Produção:

```text
HTTP :80
   │
   ▼
Redirect
   │
   ▼
HTTPS :443
```

Nginx será responsável pelo TLS.

O trabalho exige HTTPS, redirecionamento automático e avaliação no SSL Labs. fileciteturn0file0L43-L46

Será utilizado Certbot `>= 5.4` para solicitar à Let's Encrypt um certificado de curta duração para o IP público, por meio do perfil `shortlived`, da opção `--ip-address` e de um método compatível, preferencialmente `webroot`. Como o instalador Nginx do Certbot ainda não configura certificados de IP automaticamente, o Nginx deverá apontar explicitamente para os arquivos emitidos.

A renovação frequente deverá ser totalmente automatizada e recarregar o Nginx por `deploy-hook`. O procedimento será validado primeiro em staging e depois em produção.

---

# 49. SSH

Fluxo administrativo:

```text
Notebook pessoal
      │
      │ SSH Private Key
      ▼
OCI Ubuntu
```

Senha SSH deverá estar desabilitada conforme requisito acadêmico. fileciteturn0file0L41-L42

---

# 50. Fail2Ban

Proteção SSH:

```text
4 falhas
   │
   ▼
Banimento
   │
   ▼
24 horas
```

Configuração final deverá cumprir exatamente o critério da atividade. fileciteturn0file0L41-L42

---

# 51. Portas

Produção deverá expor apenas:

```text
22/tcp
80/tcp
443/tcp
```

A porta do Gunicorn não deverá ser publicada externamente.

---

# 52. Cabeçalhos de Segurança

Um hook global `after_request`, implementado em `app/http_security.py`, aplica no
Flask a política de defesa em profundidade a páginas normais, erros e conteúdo
estático:

```text
X-Content-Type-Options
Content-Security-Policy
X-Frame-Options
Referrer-Policy
Permissions-Policy
Cross-Origin-Opener-Policy
```

O mesmo hook aplica `no-store`, `Pragma: no-cache` e `Expires: 0` quando a resposta
pertence a uma sessão autenticada ou aos fluxos públicos sensíveis de autenticação
e conta. O endpoint `static` é excluído dessa regra para permitir cache de CSS e
outros assets.

O Nginx continuará responsável por TLS, redirecionamento HTTPS e HSTS. O Flask não
emite `Strict-Transport-Security`, evitando comportamento divergente entre o HTTP
local e o esquema externo antes da configuração confiável do proxy. Os valores
detalhados da CSP e dos demais headers estão definidos em `SECURITY.md`.

---

# 53. Segurança do Repositório

Nunca deverão ser versionados:

```text
.env
*.pem
*.key
*.db
private keys
tokens
credentials
TOTP secrets
```

A atividade proíbe explicitamente a exposição de credenciais e bancos locais no repositório. fileciteturn0file0L64-L69

A conta GitHub deverá utilizar 2FA. As operações Git deverão usar chave SSH protegida ou PAT de escopo mínimo, nunca a senha da conta. Chaves e tokens não poderão aparecer no repositório, logs ou evidências.

---

# 54. Segurança por Padrão

O InfraManager deverá seguir:

```text
Deny by Default
Secure by Default
Least Privilege
Server-Side Validation
Defense in Depth
```

Exemplo:

Um novo usuário não deverá receber permissões administrativas automaticamente.

---

# 55. Decisões de Arquitetura

## DEC-001

**Arquitetura monolítica modular.**

Motivo:

- menor complexidade;
- adequada ao escopo;
- fácil implantação;
- suficiente para o projeto acadêmico.

---

## DEC-002

**Flask em vez de arquitetura SPA.**

Motivo:

- simplicidade;
- Jinja atende ao projeto;
- reduz dependências;
- reduz superfície de ataque;
- facilita publicação.

---

## DEC-003

**SQLite no MVP.**

Motivo:

- não exige serviço de banco separado;
- não exige exposição de porta;
- suficiente para volume acadêmico;
- simplifica OCI Free Tier.

---

## DEC-004

**SQLAlchemy ORM.**

Motivo:

- organização;
- migrations;
- abstração de banco;
- redução do risco de SQL Injection quando utilizado adequadamente.

---

## DEC-005

**Nginx + Gunicorn.**

Motivo:

- arquitetura consolidada para Flask;
- separação entre web server e application server;
- suporte adequado a TLS.

---

## DEC-006

**MFA TOTP.**

Motivo:

- padrão amplamente suportado;
- não exige serviço externo;
- compatível com aplicativos autenticadores;
- fortalece Authentication Failures.

---

## DEC-007

**RBAC simples.**

Perfis:

```text
ADMIN
OPERATOR
VIEWER
```

Motivo:

- suficiente para demonstrar controle de acesso;
- fácil de testar;
- fácil de explicar.

---

# 56. Itens Explicitamente Fora da Arquitetura MVP

Não farão parte do MVP:

```text
Microservices
Kubernetes
Docker Swarm
Redis
Celery
React
Angular
API Gateway
Message Broker
PostgreSQL remoto
Elasticsearch
```

A inclusão futura deverá possuir justificativa técnica.

---

# 57. Critérios Arquiteturais de Aceite

A arquitetura será considerada corretamente implementada quando:

- [ ] Flask utilizar Application Factory;
- [ ] funcionalidades estiverem separadas por Blueprints;
- [ ] SQLAlchemy for utilizado;
- [ ] migrations estiverem funcionando;
- [ ] autenticação estiver isolada;
- [ ] MFA funcionar antes da criação da sessão autenticada;
- [ ] primeiro acesso sem MFA configurado ser bloqueado no fluxo de configuração antes do Dashboard;
- [ ] RBAC for validado no servidor;
- [ ] CSRF proteger operações de escrita;
- [ ] auditoria registrar operações críticas;
- [ ] Nginx estiver na frente do Gunicorn;
- [ ] Gunicorn não estiver exposto publicamente;
- [ ] produção utilizar HTTPS;
- [ ] Certbot `>= 5.4` emitir e renovar automaticamente o certificado do IP público;
- [ ] segredos não estiverem no Git;
- [ ] testes automatizados estiverem integrados à pipeline.

Os controles OWASP serão referenciados uniformemente como:

```text
A01:2025 — Broken Access Control
A05:2025 — Injection
A07:2025 — Authentication Failures
A09:2025 — Security Logging & Alerting Failures
```

---

# 58. Fluxo Completo do Projeto

```text
Usuário
  │
HTTPS
  ▼
Nginx
  │
  ▼
Gunicorn
  │
  ▼
Flask
  │
  ├── Auth
  │     ├── Password
  │     └── MFA
  │
  ├── RBAC
  │
  ├── Dashboard
  │
  ├── Assets
  │
  ├── Virtual Machines
  │
  ├── Datacenter
  │
  ├── Users
  │
  └── Audit
  │
  ▼
SQLAlchemy
  │
  ▼
SQLite
```

Desenvolvimento e implantação:

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
       ▼
      OCI
       │
       ▼
Ubuntu + Nginx + Gunicorn + Flask
```

---

# 59. Princípio Arquitetural

Toda decisão deverá responder às seguintes perguntas:

1. Isso é necessário para atender aos requisitos?
2. Isso melhora segurança ou confiabilidade?
3. Isso pode ser testado?
4. Isso mantém o projeto compreensível?
5. Isso adiciona complexidade desnecessária?

Quando duas soluções atenderem igualmente ao requisito, deverá ser escolhida a mais simples.

> O objetivo do InfraManager não é demonstrar quantidade de tecnologias, mas demonstrar uma aplicação funcional, segura, organizada e corretamente implantada.
