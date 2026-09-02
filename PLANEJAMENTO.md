# Planejamento Inicial — Projeto Final da Pós-Graduação

## 1. Identificação do Projeto

**Nome provisório:** InfraManager  
**Tipo:** Aplicação Web para Gestão de Infraestrutura de TI  
**Disciplina:** Projeto Aplicado: Práticas de Mercado  
**Foco:** Segurança da Informação, Cloud Computing, Desenvolvimento Seguro e CI/CD  
**Linguagem principal:** Python  
**Framework:** Flask  
**Cloud:** Oracle Cloud Infrastructure — OCI  
**Ambiente de desenvolvimento:** Visual Studio Code + OpenAI Codex  
**Versionamento:** Git + GitHub  
**CI/CD:** GitHub Actions  

---

# 2. Objetivo do Projeto

Desenvolver uma aplicação web funcional para gerenciamento de infraestrutura de TI, permitindo o controle de ativos físicos, máquinas virtuais e recursos de datacenter.

O projeto deverá aplicar conceitos de:

- Secure by Design;
- Secure by Default;
- OWASP Top 10:2025;
- autenticação segura;
- MFA;
- controle de acesso;
- proteção de dados;
- Cloud Computing;
- CI/CD;
- versionamento;
- desenvolvimento assistido por Inteligência Artificial.

Além de cumprir os requisitos acadêmicos, o sistema deverá representar uma aplicação plausível para utilização em ambientes reais de infraestrutura de TI.

---

# 3. Contexto da Atividade

A atividade está dividida em quatro grandes áreas:

1. Infraestrutura em Cloud;
2. Repositório e versionamento;
3. Desenvolvimento da aplicação;
4. Integração e entrega contínuas — CI/CD.

O projeto deve ser hospedado em nuvem pública utilizando recursos gratuitos, com Ubuntu Server ou Debian, servidor Web Nginx ou Apache e acesso público via internet.

A aplicação deverá possuir obrigatoriamente:

- tela de Login;
- página interna protegida;
- Logout funcional;
- desenvolvimento assistido por IA;
- mitigação documentada de pelo menos três categorias da OWASP Top 10:2025.

---

# 4. Visão Geral da Solução

O InfraManager será dividido inicialmente nos seguintes módulos:

```text
InfraManager
│
├── Autenticação
│   ├── Login
│   ├── MFA
│   ├── Logout
│   └── Recuperação de acesso
│
├── Dashboard
│
├── Ativos de TI
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
├── Auditoria
│
└── Configurações
```

O desenvolvimento será realizado de forma incremental, priorizando inicialmente os recursos obrigatórios da atividade.

---

# 5. Arquitetura Inicial

```text
                        INTERNET
                           │
                         HTTPS
                           │
                           ▼
                    ┌─────────────┐
                    │    Nginx    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Gunicorn   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Flask    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        Autenticação     CRUDs       Auditoria
              │
              ▼
         SQLAlchemy
              │
              ▼
           SQLite
```

Ambiente de produção:

```text
Oracle Cloud Infrastructure
│
├── VCN
├── Subnet pública
├── Internet Gateway
├── Security List / NSG
│
└── VM Ubuntu Server
     │
     ├── SSH
     ├── Fail2Ban
     ├── UFW
     ├── Nginx
     ├── Gunicorn
     ├── Python
     ├── Flask
     └── SQLite
```

---

# 6. Ambiente de Desenvolvimento

O ambiente principal será:

```text
Windows
   │
   ▼
Visual Studio Code
   │
   ├── Python
   ├── Git
   ├── Terminal
   └── Codex
```

O Codex será utilizado de forma integrada ao ambiente de desenvolvimento para:

- planejamento;
- geração de código;
- revisão de código;
- refatoração;
- criação de testes;
- investigação de erros;
- auditoria de segurança;
- documentação.

O uso do VS Code integrado ao Codex será tratado como ambiente similar baseado em IA, conforme permitido pelo enunciado da atividade.

---

# 7. Estratégia de Utilização de IA

A IA não deverá simplesmente desenvolver toda a solução automaticamente.

Será utilizado um processo controlado:

```text
Planejamento
     ↓
Prompt
     ↓
Análise da IA
     ↓
Revisão humana
     ↓
Implementação
     ↓
Testes
     ↓
Security Review
     ↓
Correções
```

As principais interações com IA poderão ser documentadas em:

```text
docs/
└── ia/
    ├── 01-planejamento.md
    ├── 02-arquitetura.md
    ├── 03-desenvolvimento.md
    ├── 04-testes.md
    └── 05-security-review.md
```

Isso permitirá comprovar o uso de IA durante o desenvolvimento e a auditoria do código.

---

# 8. Módulo de Autenticação

## 8.1 Login

Autenticação utilizando:

- usuário;
- senha;
- armazenamento seguro de senha utilizando hash;
- mensagens genéricas em caso de falha;
- proteção contra brute force;
- rate limiting.

Fluxo:

```text
Usuário + senha
      │
      ▼
Validação
      │
      ├── inválido → erro
      │
      └── válido
             │
             ▼
            MFA
```

---

# 9. MFA

Será implementado MFA obrigatório para todos os usuários utilizando TOTP.

No primeiro acesso, após a validação de usuário e senha, quem ainda não tiver MFA configurado será direcionado à configuração e confirmação do TOTP. O Dashboard permanecerá inacessível até a conclusão dessa etapa.

O MFA é um requisito adicional de segurança adotado pelo InfraManager; não é uma exigência direta do professor ou do enunciado da atividade.

Compatibilidade prevista:

- Google Authenticator;
- Microsoft Authenticator;
- Authy;
- Bitwarden;
- outros aplicativos compatíveis com TOTP.

Fluxo:

```text
Login
  │
  ▼
Usuário + senha
  │
  ▼
Credenciais válidas
  │
  ▼
Código TOTP
  │
  ▼
Autenticação concluída
  │
  ▼
Dashboard
```

Também serão avaliados:

- QR Code para ativação;
- códigos de recuperação;
- armazenamento seguro do segredo MFA;
- logs de ativação/desativação do MFA.

---

# 10. Controle de Acesso

Inicialmente serão utilizados três perfis.

## Administrador

Pode:

- visualizar;
- cadastrar;
- editar;
- excluir;
- administrar usuários;
- visualizar auditoria.

## Operador

Pode:

- visualizar;
- cadastrar;
- editar.

Não poderá excluir registros críticos nem administrar usuários.

## Consulta

Pode apenas:

- visualizar dados;
- pesquisar;
- utilizar filtros.

Esse modelo permitirá demonstrar RBAC — Role-Based Access Control.

---

# 11. Dashboard

O dashboard deverá apresentar uma visão geral da infraestrutura.

Exemplo:

```text
INFRA MANAGER

Ativos físicos           85
Máquinas virtuais       120
Hosts                     12
Racks                      8

VMs ligadas              104
VMs desligadas            16

Ativos em manutenção       5
```

Também poderão ser apresentados:

- VMs por ambiente;
- equipamentos por tipo;
- ativos por status;
- últimos registros cadastrados;
- últimas alterações.

Gráficos serão considerados uma evolução, e não requisito inicial.

---

# 12. Gestão de Ativos de TI

Será implementado CRUD completo.

## Funcionalidades

- cadastrar;
- visualizar;
- editar;
- excluir;
- pesquisar;
- filtrar.

## Campos iniciais

- patrimônio;
- hostname;
- tipo;
- fabricante;
- modelo;
- número de série;
- endereço IP;
- sistema operacional;
- setor;
- responsável;
- localização;
- status;
- observações.

## Tipos de ativos

- servidor;
- storage;
- switch;
- firewall;
- notebook;
- desktop;
- access point;
- appliance;
- outros.

---

# 13. Gestão de Máquinas Virtuais

CRUD completo para máquinas virtuais.

## Campos iniciais

- nome;
- hostname;
- endereço IP;
- sistema operacional;
- ambiente;
- vCPU;
- memória RAM;
- armazenamento;
- aplicação;
- responsável;
- cluster;
- host;
- status;
- observações.

## Ambientes

- Produção;
- Homologação;
- Desenvolvimento;
- Teste.

## Status

- Ligada;
- Desligada;
- Manutenção;
- Descomissionada.

---

# 14. Inventário de Datacenter

Estrutura prevista:

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
Equipamentos
```

Datacenter, Sala e Rack terão CRUD completo: cadastro, listagem, visualização de detalhes, edição e exclusão. Todas as operações de escrita deverão aplicar autorização server-side, validação, CSRF, auditoria e verificação de dependências.

## Informações do Datacenter

- nome;
- localização;
- descrição.

## Informações do Rack

- nome;
- datacenter;
- sala;
- quantidade de U;
- observações.

Posteriormente poderá ser desenvolvido um mapa visual dos racks, caso o escopo principal já esteja concluído.

---

# 15. Banco de Dados

Tecnologias:

```text
Flask
  │
  ▼
SQLAlchemy
  │
  ▼
SQLite
```

Será utilizado:

- SQLAlchemy ORM;
- Flask-Migrate;
- Alembic.

A utilização de ORM também contribuirá para a proteção contra SQL Injection.

---

# 16. Modelo Inicial de Dados

Entidades previstas:

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

Os perfis `ADMIN`, `OPERATOR` e `VIEWER` serão armazenados diretamente no campo `User.role`. Não será criada entidade ou tabela `Role` separada no MVP.

Relacionamento conceitual:

```text
Datacenter
    │
    └── Room
          │
          └── Rack
                │
                └── Asset
                      │
                      └── VirtualMachine
```

O modelo definitivo será definido antes da implementação.

---

# 17. Segurança da Aplicação

A aplicação deverá aplicar Secure by Design desde seu início.

Controles previstos:

- hash seguro de senhas;
- MFA;
- rate limiting;
- proteção contra brute force;
- CSRF;
- validação server-side;
- SQLAlchemy ORM;
- escaping de conteúdo;
- cookies HttpOnly;
- cookies Secure;
- SameSite;
- sessão com timeout;
- RBAC;
- proteção de rotas;
- security headers;
- logs de auditoria;
- tratamento seguro de erros;
- ausência de segredos hardcoded.

---

# 18. OWASP Top 10:2025

A atividade exige a mitigação de pelo menos três vulnerabilidades da OWASP Top 10:2025 e sua documentação no README.

Inicialmente serão trabalhadas quatro categorias.

## A01:2025 — Broken Access Control

Mitigações previstas:

- autenticação obrigatória;
- RBAC;
- proteção das rotas;
- validação server-side;
- deny-by-default;
- controle de ações CRUD de acordo com o perfil.

---

## A05:2025 — Injection

Mitigações:

- SQLAlchemy;
- queries parametrizadas;
- validação dos inputs;
- escaping de conteúdo;
- proibição de SQL concatenado.

---

## A07:2025 — Authentication Failures

Mitigações:

- senha utilizando hash;
- MFA;
- rate limiting;
- limitação de tentativas de login;
- sessão segura;
- timeout;
- logout funcional;
- cookies seguros.

---

## A09:2025 — Security Logging & Alerting Failures

Serão registrados eventos como:

- login bem-sucedido;
- login falho;
- falha de MFA;
- ativação de MFA;
- alteração de usuário;
- inclusão de ativo;
- alteração de ativo;
- exclusão de ativo;
- alteração de VM;
- exclusão de VM.

Também será implementado um mecanismo simples de alertas: falhas repetidas de Login/MFA, bloqueios por rate limiting e tentativas de acesso administrativo negadas gerarão alertas `WARNING` ou `CRITICAL`, com data/hora, origem resumida, contagem e estado de revisão, disponíveis aos Administradores. E-mail, SMS e SIEM não são necessários no MVP.

---

# 19. Auditoria

O sistema possuirá um histórico de eventos administrativos.

Exemplo:

```text
31/08/2026 17:30
Usuário: admin
Ação: UPDATE
Objeto: VirtualMachine
Registro: VM-APP-01
IP: xxx.xxx.xxx.xxx
```

Somente administradores poderão consultar o módulo completo de auditoria.

---

# 20. Infraestrutura OCI

O projeto será hospedado utilizando recursos gratuitos da Oracle Cloud Infrastructure.

Estrutura prevista:

```text
OCI
│
├── Compartment
├── VCN
├── Internet Gateway
├── Public Subnet
├── Security List / NSG
│
└── Compute Instance
     ├── Public IP
     └── State: Running
```

Sistema operacional:

**Ubuntu Server — versão estável atual disponível no momento da criação da instância.**

Serão preservadas evidências separadas do compartment, VCN, subnet pública, internet gateway, security list e/ou NSG, fluxo de criação da instância, IP público atribuído e tela da instância em execução.

---

# 21. Segurança da Infraestrutura

O enunciado exige controles específicos de infraestrutura.

Deverão ser configurados:

## SSH

- autenticação somente por chave SSH;
- autenticação por senha desabilitada;
- acesso root remoto desabilitado.

## Fail2Ban

Configuração obrigatória:

```text
Tentativas: 4
Banimento: 24 horas
```

## Firewall

Somente portas necessárias deverão ser expostas:

```text
TCP 22
TCP 80
TCP 443
```

Sempre que possível, a porta SSH deverá ser limitada ao endereço IP administrativo.

---

# 22. Servidor Web

Será utilizado:

**Nginx**

Arquitetura:

```text
Internet
   │
   ▼
Nginx
   │
   ▼
Gunicorn
   │
   ▼
Flask
```

A aplicação Flask não ficará diretamente exposta à internet.

---

# 23. HTTPS

Será configurado HTTPS utilizando:

- Let's Encrypt;
- Certbot `>= 5.4`;
- certificado de curta duração para IP público, usando o perfil `shortlived` e `--ip-address`;
- validação por método compatível, preferencialmente `webroot`;
- configuração explícita dos arquivos do certificado no Nginx;
- renovação automática com `deploy-hook` para recarregar o Nginx.

O fluxo deverá ser validado primeiro no ambiente staging da Let's Encrypt. Como o certificado para IP é de curta duração, a automação de renovação é obrigatória.

Todo acesso HTTP deverá ser redirecionado automaticamente para HTTPS.

```text
HTTP
 │
 ▼
301
 │
 ▼
HTTPS
```

---

# 24. SSL Labs

Após implantação, o servidor deverá ser submetido ao teste:

**Qualys SSL Labs — SSL Server Test**

Critérios da atividade:

- Nota A;
- suporte a PQC ativo.

Esses resultados serão registrados como evidências do projeto.

---

# 25. GitHub

O código será armazenado em repositório público no GitHub, conforme exigido pela atividade.

Repositório previsto:

```text
inframanager
```

Boas práticas:

- autenticação segura;
- 2FA na conta GitHub;
- autenticação das operações Git por chave SSH protegida ou PAT de escopo mínimo;
- não utilizar a senha da conta para push/pull;
- commits frequentes;
- mensagens de commit organizadas;
- nenhuma credencial no repositório.

---

# 26. Proteção Contra Vazamento de Segredos

Será criado `.gitignore`.

Arquivos que nunca deverão entrar no repositório:

```text
.env
*.pem
*.key
id_rsa
id_ed25519
instance/*.db
__pycache__/
.venv/
```

Também não poderão existir:

- senhas hardcoded;
- tokens;
- private keys;
- credenciais OCI;
- segredos MFA;
- Flask Secret Key real.

Um `.env.example` poderá ser disponibilizado sem valores sensíveis.

---

# 27. CI/CD

O fluxo exigido pela atividade será implementado utilizando GitHub Actions.

Fluxo:

```text
VS Code
   │
git push origin main
   │
   ▼
GitHub
   │
   ▼
GitHub Actions
   │
   ├── checkout
   ├── instalação Python
   ├── dependências
   ├── lint
   ├── testes
   ├── security checks
   └── deploy
           │
           ▼
          OCI
```

---

# 28. Estratégia de Deploy

A pipeline deverá:

1. detectar push na branch `main`;
2. executar os testes;
3. executar verificações de qualidade;
4. executar verificações de segurança;
5. interromper o deploy em caso de falha;
6. conectar ao servidor OCI;
7. atualizar o código;
8. aplicar migrations;
9. reiniciar o serviço;
10. executar health check.

Fluxo:

```text
Push
 │
 ▼
Testes
 │
 ├── Falha → STOP
 │
 └── Sucesso
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

---

# 29. GitHub Secrets

Credenciais de deploy deverão utilizar GitHub Secrets.

Exemplos:

```text
OCI_HOST
OCI_USER
OCI_SSH_PRIVATE_KEY
DEPLOY_PATH
```

Nenhuma dessas informações deverá estar presente no workflow em texto puro.

---

# 30. Testes

Serão desenvolvidos testes automatizados para funções críticas.

Prioridades:

- Login;
- Logout;
- MFA;
- RBAC;
- proteção de rotas;
- CRUD de ativos;
- CRUD de VMs;
- validação de formulários;
- tentativas de acesso não autorizado.

Ferramenta prevista:

```text
pytest
```

---

# 31. Estrutura Inicial do Repositório

```text
inframanager/
│
├── app/
│   ├── auth/
│   ├── assets/
│   ├── virtual_machines/
│   ├── datacenter/
│   ├── audit/
│   ├── users/
│   ├── templates/
│   └── static/
│
├── migrations/
│
├── tests/
│
├── docs/
│   ├── architecture/
│   ├── security/
│   ├── evidencias/
│   └── ia/
│
├── instance/
│
├── .github/
│   └── workflows/
│       └── deploy.yml
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

Essa estrutura ainda poderá ser ajustada antes do início do desenvolvimento.

---

# 32. Documentação do Projeto

Serão mantidos inicialmente:

## `PLANEJAMENTO.md`

Visão geral e estratégia do projeto.

## `REQUIREMENTS.md`

Requisitos funcionais e não funcionais.

## `ARCHITECTURE.md`

Arquitetura técnica.

## `SECURITY.md`

Decisões e controles de segurança.

## `AGENTS.md`

Instruções para agentes de IA como Codex.

## `README.md`

Documento principal da entrega acadêmica.

---

# 33. Evidências

Será criada a pasta:

```text
docs/evidencias/
```

Possíveis evidências:

```text
01-vscode-codex.png
02-codex-planejamento.png
03-codex-desenvolvimento.png

04-oci-compartment.png
05-oci-vcn.png
06-oci-subnet.png
07-oci-internet-gateway.png
08-oci-security-list-nsg.png
09-oci-instance-create.png
10-oci-public-ip.png
11-oci-instance-running.png

12-ssh-key.png
13-fail2ban.png
14-ufw.png

15-nginx.png
16-https.png

17-ssl-labs-a.png
18-ssl-labs-pqc.png

19-login.png
20-mfa.png
21-dashboard.png
22-crud-ativos.png
23-crud-vms.png

24-github.png
25-github-actions.png
26-deploy-success.png
```

---

# 34. Escopo MVP

O seguinte conjunto será considerado obrigatório antes de qualquer funcionalidade extra.

## Aplicação

- [ ] Login
- [ ] MFA
- [ ] Logout
- [ ] RBAC
- [ ] Dashboard
- [ ] CRUD Ativos
- [ ] CRUD Máquinas Virtuais
- [ ] CRUD completo de Datacenter
- [ ] CRUD completo de Sala
- [ ] CRUD completo de Rack
- [ ] Pesquisa
- [ ] Filtros

## Segurança

- [ ] Hash de senha
- [ ] Rate limiting
- [ ] CSRF
- [ ] Secure cookies
- [ ] Session timeout
- [ ] RBAC
- [ ] Logs de auditoria
- [ ] Validação server-side

## OWASP

- [ ] A01:2025 — Broken Access Control
- [ ] A05:2025 — Injection
- [ ] A07:2025 — Authentication Failures
- [ ] A09:2025 — Security Logging & Alerting Failures

## Cloud

- [ ] OCI Free Tier
- [ ] Ubuntu
- [ ] Public IP
- [ ] evidências completas de criação e estado `Running`
- [ ] SSH por chave
- [ ] Fail2Ban
- [ ] Firewall
- [ ] Nginx
- [ ] Gunicorn

## HTTPS

- [ ] Certbot `>= 5.4`
- [ ] certificado Let's Encrypt para IP público
- [ ] renovação automática e recarga do Nginx
- [ ] Let's Encrypt
- [ ] HTTP → HTTPS
- [ ] SSL Labs A
- [ ] PQC

## GitHub

- [ ] Repositório público
- [ ] `.gitignore`
- [ ] nenhum segredo exposto
- [ ] GitHub Secrets
- [ ] GitHub 2FA
- [ ] autenticação Git por SSH ou PAT de escopo mínimo

## CI/CD

- [ ] GitHub Actions
- [ ] testes automáticos
- [ ] deploy automático
- [ ] health check

## IA

- [ ] VS Code + Codex
- [ ] geração assistida
- [ ] testes assistidos
- [ ] security review com IA
- [ ] evidências de uso

---

# 35. Funcionalidades Futuras — Fora do MVP

Somente serão avaliadas após a conclusão integral do MVP.

- gráficos avançados;
- exportação CSV;
- exportação PDF;
- inventário visual de racks;
- histórico detalhado de alterações;
- API REST;
- PostgreSQL;
- integração VMware/vCenter;
- importação automática de ativos;
- descoberta de máquinas;
- monitoramento;
- Docker;
- Ansible;
- Terraform;
- Kubernetes.

Esses itens não devem aumentar o risco da entrega acadêmica.

---

# 36. Etapas do Projeto

## Fase 0 — Planejamento

- [ ] analisar atividade;
- [ ] definir escopo;
- [ ] definir stack;
- [ ] definir arquitetura;
- [ ] criar documentação.

## Fase 1 — Preparação

- [ ] instalar VS Code;
- [ ] configurar Python;
- [ ] configurar Git;
- [ ] configurar Codex;
- [ ] criar repositório GitHub.

## Fase 2 — Base da Aplicação

- [ ] estrutura Flask;
- [ ] configuração;
- [ ] SQLAlchemy;
- [ ] migrations;
- [ ] layout base.

## Fase 3 — Autenticação

- [ ] usuários;
- [ ] login;
- [ ] logout;
- [ ] hash de senha;
- [ ] proteção de sessão.

## Fase 4 — MFA

- [ ] TOTP;
- [ ] QR Code;
- [ ] validação;
- [ ] recovery codes.
- [ ] primeiro acesso bloqueado na configuração antes do Dashboard.

## Fase 5 — RBAC

- [ ] Administrador;
- [ ] Operador;
- [ ] Consulta;
- [ ] proteção de rotas.

## Fase 6 — Ativos

- [ ] model;
- [ ] CRUD;
- [ ] filtros;
- [ ] testes.

## Fase 7 — VMs

- [ ] model;
- [ ] CRUD;
- [ ] filtros;
- [ ] testes.

## Fase 8 — Datacenter

- [ ] CRUD completo de Datacenter;
- [ ] CRUD completo de Sala;
- [ ] CRUD completo de Rack;
- [ ] relacionamentos.

## Fase 9 — Auditoria

- [ ] eventos;
- [ ] tela administrativa;
- [ ] filtros.
- [ ] alertas simples de segurança.

## Fase 10 — Security Review

- [ ] OWASP;
- [ ] Codex Review;
- [ ] correções;
- [ ] testes de segurança.

## Fase 11 — OCI

- [ ] compartment;
- [ ] VCN;
- [ ] subnet;
- [ ] internet gateway;
- [ ] security list/NSG;
- [ ] criação da instância;
- [ ] VM;
- [ ] IP público;
- [ ] instância em execução;
- [ ] SSH.

## Fase 12 — Hardening

- [ ] SSH;
- [ ] UFW;
- [ ] Fail2Ban;
- [ ] atualizações.

## Fase 13 — Produção

- [ ] Gunicorn;
- [ ] Nginx;
- [ ] aplicação.

## Fase 14 — HTTPS

- [ ] Certbot `>= 5.4`;
- [ ] certificado;
- [ ] certificado para IP público com perfil `shortlived`;
- [ ] renovação automática;
- [ ] redirect;
- [ ] SSL Labs;
- [ ] PQC.

## Fase 15 — CI/CD

- [ ] GitHub Actions;
- [ ] Secrets;
- [ ] testes;
- [ ] deploy;
- [ ] health check.

## Fase 16 — Documentação

- [ ] README;
- [ ] arquitetura;
- [ ] OWASP;
- [ ] evidências;
- [ ] uso de IA.

## Fase 17 — Validação Final

Executar integralmente o checklist exigido pela atividade.

---

# 37. Critério para Considerar o Projeto Concluído

O projeto somente deverá ser considerado finalizado quando:

- a aplicação estiver acessível publicamente;
- autenticação e MFA estiverem funcionando;
- primeiro acesso exigir configuração do MFA antes do Dashboard;
- CRUD completo de Datacenter, Sala e Rack estiver funcional;
- perfis de acesso estiverem funcionando;
- não houver credenciais no GitHub;
- testes estiverem aprovados;
- GitHub Actions estiver realizando deploy;
- HTTPS estiver funcional;
- HTTP redirecionar para HTTPS;
- SSL Labs apresentar Nota A;
- PQC estiver confirmado;
- SSH utilizar apenas chave;
- Fail2Ban estiver configurado;
- OWASP estiver documentado;
- README estiver completo;
- evidências estiverem organizadas.

---

# 38. Princípio do Projeto

Durante todo o desenvolvimento será adotada a seguinte regra:

> Primeiro garantir uma solução simples, segura, funcional, testada e aderente aos critérios acadêmicos. Somente após a conclusão do MVP serão adicionadas funcionalidades extras.

O InfraManager deverá demonstrar domínio do processo completo:

```text
Planejar
   ↓
Desenvolver
   ↓
Versionar
   ↓
Testar
   ↓
Proteger
   ↓
Automatizar
   ↓
Publicar
   ↓
Validar
   ↓
Documentar
```

Esse será o princípio orientador de todas as próximas etapas do projeto.
