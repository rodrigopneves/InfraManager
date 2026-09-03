# AGENTS.md — InfraManager

## 1. Objetivo deste arquivo

Este arquivo define as regras que agentes de IA devem seguir ao trabalhar no projeto **InfraManager**.

Antes de modificar qualquer arquivo, o agente deverá ler:

```text
REQUIREMENTS.md
ARCHITECTURE.md
SECURITY.md
AGENTS.md
```

Esses documentos representam as decisões oficiais do projeto.

Nenhuma implementação deverá contradizê-los sem justificativa explícita.

---

# 2. Papel do Agente

O agente deverá atuar como:

- desenvolvedor;
- revisor de código;
- criador de testes;
- analista de segurança;
- assistente de documentação.

O agente NÃO deverá agir como responsável autônomo por decisões arquiteturais importantes.

Decisões relevantes deverão ser apresentadas para revisão antes da implementação.

---

# 3. Princípio Geral

O InfraManager deverá priorizar:

```text
Segurança
   +
Simplicidade
   +
Testabilidade
   +
Manutenibilidade
   +
Aderência aos requisitos
```

Não adicionar complexidade apenas para tornar o projeto aparentemente mais sofisticado.

---

# 4. Stack Oficial

A stack aprovada para o MVP é:

## Backend

```text
Python
Flask
```

## Persistência

```text
SQLAlchemy
SQLite
Flask-Migrate / Alembic
```

## Autenticação e Segurança

```text
Flask-Login
Flask-WTF
Flask-Limiter
PyOTP
```

## Frontend

```text
HTML
Jinja2
Bootstrap
CSS
```

## Testes

```text
pytest
Flask Test Client
```

## Produção

```text
Ubuntu Server
Nginx
Gunicorn
systemd
```

## Cloud

```text
Oracle Cloud Infrastructure
```

## CI/CD

```text
GitHub Actions
```

---

# 5. Tecnologias Não Autorizadas no MVP

O agente NÃO deverá adicionar sem aprovação explícita:

```text
Docker
Kubernetes
Redis
Celery
RabbitMQ
Kafka
React
Angular
Vue
Next.js
PostgreSQL
MySQL
MongoDB
Terraform
Ansible
Microservices
API Gateway
GraphQL
```

Se considerar alguma tecnologia necessária, deverá primeiro explicar:

1. qual problema ela resolve;
2. por que a stack atual não resolve;
3. impacto em segurança;
4. impacto em implantação;
5. impacto em manutenção.

Não deverá implementá-la automaticamente.

---

# 6. Arquitetura Obrigatória

A aplicação deverá seguir:

```text
Application Factory
+
Blueprints
+
Services
+
Models
+
SQLAlchemy ORM
```

Fluxo:

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

Evitar lógica de negócio excessiva diretamente em:

- routes;
- templates;
- models.

---

# 7. Estrutura Esperada

Estrutura base:

```text
inframanager/
│
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   │
│   ├── models/
│   │
│   ├── auth/
│   ├── dashboard/
│   ├── assets/
│   ├── virtual_machines/
│   ├── datacenter/
│   ├── users/
│   ├── audit/
│   │
│   ├── templates/
│   └── static/
│
├── migrations/
├── tests/
├── docs/
├── instance/
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

Não reorganizar a estrutura principal sem aprovação.

---

# 8. Segurança Obrigatória

Toda implementação deverá considerar:

```text
Authentication
Authorization
Input Validation
CSRF
Session Security
Audit Logging
Error Handling
Secrets Protection
Testing
```

Nenhum módulo CRUD deverá ser implementado sem autorização server-side.

---

# 9. Secure by Default

A configuração padrão deverá ser segura.

Exemplo:

Novo usuário:

```text
VIEWER
```

ou outro papel mínimo definido pelo sistema.

Nunca:

```text
ADMIN
```

por padrão.

---

# 10. Deny by Default

Se uma ação não estiver explicitamente permitida, deverá ser negada.

O agente não deverá implementar autorização baseada apenas em ocultação de elementos HTML.

---

# 11. Autenticação

O fluxo obrigatório é:

```text
Username + Password
       │
       ▼
Credenciais válidas
       │
       ▼
MFA já configurado?
   ┌───┴────┐
   │        │
  Não      Sim
   │        │
   ▼        │
Configuração MFA
   │        │
   └───┬────┘
       ▼
Validação TOTP
       │
       ▼
Sessão autenticada
       │
       ▼
Dashboard
```

O MFA é obrigatório para todos os usuários. No primeiro acesso, após a validação da senha, o usuário deverá ser direcionado à configuração do MFA e não poderá acessar o Dashboard antes de confirmar um código TOTP válido.

O MFA é um requisito adicional definido pelo projeto InfraManager para reforçar a segurança. Ele não deverá ser apresentado como exigência direta do professor ou do enunciado acadêmico.

---

# 12. MFA

Utilizar TOTP com biblioteca consolidada.

Previsto:

```text
PyOTP
```

O agente NÃO deverá:

- criar algoritmo TOTP próprio;
- registrar segredo TOTP em logs;
- inserir segredo TOTP no código;
- utilizar segredo fixo para todos os usuários.

---

# 13. Recovery Codes

Recovery codes deverão:

- ser aleatórios;
- ser de uso único;
- ser armazenados apenas em hash;
- ser invalidados após utilização.

Não armazenar os códigos originais no banco.

---

# 14. Senhas

Nunca armazenar senha em texto puro.

Nunca implementar criptografia própria para senha.

Utilizar mecanismo consolidado de password hashing.

O agente não deverá gerar credenciais reais dentro do código.

---

# 15. Secrets

É proibido inserir no repositório:

```text
password
API key
token
SSH private key
OCI credential
GitHub token
TOTP secret
real SECRET_KEY
```

Utilizar variáveis de ambiente.

---

# 16. `.env`

Arquivo real:

```text
.env
```

não deverá ser versionado.

Somente:

```text
.env.example
```

com placeholders.

Exemplo correto:

```text
SECRET_KEY=
DATABASE_URL=
```

---

# 17. Banco de Dados

Para o MVP:

```text
SQLite
```

por meio de:

```text
SQLAlchemy ORM
```

O agente não deverá criar queries SQL concatenando entrada de usuário.

---

# 18. SQL Injection

Proibido:

```python
query = "SELECT * FROM users WHERE name = '" + username + "'"
```

Utilizar:

- ORM;
- parâmetros;
- queries seguras.

Toda pesquisa e filtro deverá respeitar essa regra.

---

# 19. Validação de Entrada

Toda entrada deverá possuir validação server-side.

Exemplos:

- IP;
- e-mail;
- enums;
- inteiros;
- tamanho máximo;
- campos obrigatórios;
- RAM;
- vCPU;
- storage;
- rack units.

Validação HTML não substitui validação no servidor.

---

# 20. XSS

Preservar escaping padrão do Jinja2.

Evitar uso de:

```text
|safe
```

com conteúdo controlado pelo usuário.

Não transformar conteúdo do usuário em HTML confiável sem necessidade.

---

# 21. CSRF

Toda operação de escrita deverá possuir proteção CSRF.

Não implementar exclusões por GET.

Proibido:

```text
GET /asset/10/delete
```

Usar operação POST protegida.

---

# 22. RBAC

Perfis oficiais:

```text
ADMIN
OPERATOR
VIEWER
```

Permissões deverão seguir `REQUIREMENTS.md` e `SECURITY.md`.

Toda autorização deverá ser verificada no servidor.

Os perfis deverão ser armazenados diretamente em `User.role`, usando os valores técnicos `admin`, `operator` e `viewer`. Não criar entidade, tabela ou model `Role` separado no MVP.

---

# 23. Auditoria

Operações importantes deverão gerar AuditLog.

Exemplos:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
MFA_FAILURE
MFA_ENABLED
MFA_DISABLED
LOGOUT

USER_CREATE
USER_UPDATE
USER_DISABLE

ASSET_CREATE
ASSET_UPDATE
ASSET_DELETE

VM_CREATE
VM_UPDATE
VM_DELETE
```

O CRUD completo de Datacenter, Sala e Rack também deverá gerar eventos de criação, consulta quando relevante, atualização e exclusão.

Além do AuditLog, deverá existir um mecanismo simples de alertas de segurança para A09. No MVP, eventos críticos ou repetidos — por exemplo, múltiplas falhas de Login/MFA, bloqueio por rate limit ou tentativa de acesso negado a função administrativa — deverão gerar registro `WARNING`/`CRITICAL` no Application Log e ficar visíveis em uma consulta administrativa de alertas pendentes/recentes. Não é obrigatório integrar e-mail, SMS ou serviço externo.

Nunca registrar:

- senha;
- hash de senha;
- TOTP;
- segredo MFA;
- recovery code;
- token;
- cookie;
- session ID.

---

# 24. Tratamento de Erros

Em produção:

```text
DEBUG=False
```

Nunca expor:

- stack trace;
- SQL interno;
- caminhos do servidor;
- segredos;
- configuração;
- variáveis de ambiente.

---

# 25. Rotas de Erro

Implementar tratamento para:

```text
400
403
404
429
500
```

Mensagens deverão ser seguras e simples.

---

# 26. Logs

Distinguir:

```text
Application Log
```

de:

```text
Audit Log
```

Application Log:

- erro técnico;
- exception;
- falha de banco.

Audit Log:

- ação executada por usuário;
- Login;
- alteração;
- exclusão.

---

# 27. Testes Obrigatórios

Toda funcionalidade relevante deverá possuir testes.

Prioridades:

```text
Authentication
MFA
RBAC
CSRF
CRUD
Validation
Audit
Protected Routes
```

---

# 28. Desenvolvimento Orientado a Testes

Quando apropriado, seguir:

```text
Requisito
   │
   ▼
Teste
   │
   ▼
Implementação
   │
   ▼
Refatoração
```

Não modificar um controle crítico sem atualizar ou adicionar teste.

---

# 29. Testes de Autenticação

Deverão cobrir:

- Login válido;
- Login inválido;
- usuário desabilitado;
- Logout;
- rota protegida sem Login;
- MFA válido;
- MFA inválido;
- recovery code válido;
- recovery code utilizado.

---

# 30. Testes de RBAC

Testar pelo menos:

```text
ADMIN → operação permitida
OPERATOR → operação permitida
OPERATOR → Delete negado
VIEWER → POST negado
VIEWER → acesso de edição negado
```

Resultado esperado para autorização negada:

```text
403
```

quando apropriado.

---

# 31. Testes CRUD

Cada módulo deverá testar:

```text
Create
Read
Update
Delete
Validation
Authorization
Audit
```

Datacenter, Sala e Rack são módulos CRUD completos e cada um deverá possuir testes próprios de Create, Read, Update, Delete, validação, autorização e auditoria.

---

# 32. Processo de Implementação

Para cada nova funcionalidade, o agente deverá seguir:

```text
1. Ler requisito correspondente
2. Ler arquitetura
3. Ler regra de segurança
4. Apresentar plano
5. Implementar
6. Criar testes
7. Executar testes
8. Revisar segurança
9. Resumir alterações
```

---

# 33. Planejamento Antes da Alteração

Para mudanças maiores, antes de editar arquivos o agente deverá responder com:

```text
Objetivo
Arquivos afetados
Estratégia
Riscos
Testes necessários
```

Somente depois iniciar a implementação.

---

# 34. Mudanças Pequenas

Correções triviais poderão ser realizadas diretamente, desde que:

- não alterem arquitetura;
- não alterem segurança;
- possuam baixo risco;
- sejam verificadas.

---

# 35. Não Reescrever Código Sem Necessidade

O agente deverá preservar código existente funcional.

Não realizar refatorações amplas sem benefício concreto.

Evitar:

```text
"Vou reescrever todo o módulo para ficar mais moderno."
```

Preferir alterações incrementais.

---

# 36. Dependências

Antes de adicionar dependência Python, verificar:

1. necessidade;
2. manutenção do pacote;
3. impacto;
4. se biblioteca padrão já resolve;
5. impacto de segurança.

Dependências não utilizadas deverão ser removidas.

---

# 37. `requirements.txt`

Toda dependência necessária deverá estar declarada.

Não adicionar dezenas de pacotes sem justificativa.

---

# 38. Commits

O agente poderá sugerir mensagens de commit.

Padrão recomendado:

```text
feat: add asset creation
fix: validate vm ip address
security: enforce rbac on asset deletion
test: add mfa authentication tests
docs: update security documentation
```

Não realizar commit automaticamente sem solicitação/autorização quando estiver operando localmente.

---

# 39. Branches

Branch principal:

```text
main
```

Push para `main` poderá iniciar produção via GitHub Actions.

Antes de sugerir merge para `main`, verificar:

```text
Tests
Security checks
Documentation
```

---

# 40. GitHub Actions

A pipeline deverá seguir:

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

Falha crítica deverá bloquear o deploy.

---

# 41. Segurança do Workflow

Nunca:

```text
echo $PRIVATE_KEY
```

ou imprimir Secrets.

Não persistir segredos em artefatos.

---

# 42. OCI

Produção utilizará Oracle Cloud Infrastructure.

O agente deverá considerar:

```text
Ubuntu Server
Nginx
Gunicorn
systemd
SQLite
Fail2Ban
UFW
Certbot
```

Não mudar o provedor Cloud sem aprovação.

As evidências da OCI deverão demonstrar separadamente: compartment, VCN, subnet pública, internet gateway, security list e/ou NSG, criação da instância, atribuição do IP público e estado da instância como `Running`/em execução. Screenshots não deverão expor chaves ou outros segredos.

---

# 43. Produção

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

Gunicorn não deverá ser exposto publicamente.

---

# 44. Nginx

Nginx deverá:

- receber HTTPS;
- redirecionar HTTP;
- aplicar headers;
- encaminhar para Gunicorn.

Não servir:

```text
.env
database
Python source
private keys
```

---

# 45. HTTPS

Produção deverá funcionar somente com HTTPS para aplicação.

HTTP deverá redirecionar para HTTPS.

Utilizar Certbot `>= 5.4` para emitir certificado Let's Encrypt destinado ao IP público, com o perfil `shortlived`, a opção `--ip-address` e método compatível, preferencialmente `webroot`. Validar primeiro em staging e não substituir silenciosamente esse requisito por certificado autoassinado.

Como o certificado de IP é de curta duração e o plugin Nginx não faz sua instalação automática, configurar explicitamente os arquivos no Nginx e automatizar a renovação com `deploy-hook` para recarregar o serviço.

O acesso por IP público certificado deverá ser usado de forma coerente nos testes de redirecionamento, renovação, SSL Labs Nota A e verificação de PQC.

---

# 45.1 Segurança da Conta GitHub

Antes de publicar ou configurar o CI/CD, verificar:

- 2FA habilitado na conta GitHub;
- operações Git autenticadas por chave SSH protegida ou Personal Access Token (PAT) de escopo mínimo;
- senha da conta não utilizada como mecanismo de autenticação Git;
- chaves e PATs ausentes do repositório, logs e evidências.

---

# 46. SSH

Acesso administrativo deverá utilizar chave SSH.

Não sugerir habilitar senha SSH como solução permanente.

---

# 47. Fail2Ban

Configuração obrigatória do projeto:

```text
maxretry = 4
bantime = 24h
```

Não alterar esses valores sem justificativa e aprovação.

---

# 48. Firewall

Portas esperadas:

```text
22
80
443
```

Não abrir portas adicionais sem necessidade técnica clara.

---

# 49. Security Review

O agente deverá poder trabalhar em modo de revisão.

Quando solicitado:

```text
Faça um security review.
```

não deverá alterar código imediatamente.

Primeiro produzir achados.

---

# 50. Formato de Security Review

Classificar:

```text
Critical
High
Medium
Low
Informational
```

Cada achado deve informar:

```text
Título
Severidade
Arquivo
Descrição
Impacto
Recomendação
```

---

# 51. Correções de Segurança

Após o review, somente corrigir achados aprovados.

Toda correção deverá incluir teste de regressão quando possível.

---

# 52. OWASP

O projeto deverá evidenciar principalmente:

```text
A01:2025 — Broken Access Control
A05:2025 — Injection
A07:2025 — Authentication Failures
A09:2025 — Security Logging & Alerting Failures
```

Não adicionar controles apenas para “marcar checklist”.

Os controles precisam ser reais e demonstráveis.

---

# 53. Evidências

Ao implementar controles relevantes, sugerir evidências adequadas.

Exemplo:

```text
Controle: RBAC

Evidência:
- teste pytest;
- resultado HTTP 403;
- arquivo/decorator responsável.
```

---

# 54. Documentação

Mudanças arquiteturais deverão atualizar:

```text
ARCHITECTURE.md
```

Mudanças de segurança:

```text
SECURITY.md
```

Mudanças de requisito:

```text
REQUIREMENTS.md
```

Não deixar documentação deliberadamente inconsistente com o código.

---

# 55. README

O README final deverá explicar:

- objetivo;
- arquitetura;
- instalação;
- utilização;
- segurança;
- OWASP;
- OCI;
- CI/CD;
- uso de IA;
- evidências.

O agente poderá ajudar a mantê-lo atualizado.

---

# 56. Uso de Dados Fictícios

Sempre utilizar dados de demonstração.

Exemplo:

```text
DC-LAB-01
RACK-01
HOST-LAB-01
VM-DEMO-01
192.0.2.10
```

Não utilizar informações corporativas reais.

---

# 57. IPs de Documentação

Quando exemplos públicos forem necessários, preferir intervalos reservados para documentação.

Exemplo:

```text
192.0.2.0/24
198.51.100.0/24
203.0.113.0/24
```

---

# 58. Não Expor Informações Sensíveis em Screenshots

Antes de sugerir screenshot para evidência, verificar presença de:

- chave;
- senha;
- token;
- QR Code MFA ativo;
- segredo;
- cookie;
- IP que não deva ser divulgado.

---

# 59. Código Limpo

Código deverá:

- possuir nomes claros;
- evitar funções excessivamente longas;
- evitar duplicação desnecessária;
- usar type hints quando apropriado;
- seguir padrões Python;
- ser legível.

---

# 60. Comentários

Não criar comentários óbvios como:

```python
# Incrementa x
x += 1
```

Comentários devem explicar decisões não óbvias, especialmente de segurança.

---

# 61. Segurança Acima de Conveniência

Se uma solução simples comprometer segurança, não utilizá-la.

Exemplo proibido:

```text
Desabilitar CSRF porque o teste está falhando.
```

O correto é corrigir o teste ou configuração.

---

# 62. Não Desabilitar Controle Para Fazer Funcionar

O agente nunca deverá solucionar erro propondo permanentemente:

```text
DEBUG=True
CSRF disabled
SSL verification disabled
authentication disabled
authorization bypassed
```

em produção.

---

# 63. Falha Segura

Quando ocorrer erro de autorização ou validação, o sistema deverá falhar de forma segura.

Exemplo:

```text
Permissão desconhecida
      ↓
Acesso negado
```

Nunca:

```text
Permissão desconhecida
      ↓
Acesso permitido
```

---

# 64. Health Check

Endpoint:

```text
/health
```

deverá retornar somente informação mínima.

Exemplo:

```json
{
  "status": "ok"
}
```

Não revelar:

- versão do Flask;
- banco;
- sistema operacional;
- Secret Key;
- dependências.

---

# 65. Performance

Performance não deverá ser otimizada prematuramente.

Primeiro:

```text
Correctness
Security
Tests
```

Depois performance, caso exista problema real.

---

# 66. Compatibilidade

Código deverá ser compatível com a versão Python definida oficialmente no início da implementação.

O agente não deverá alterar a versão sem justificar.

---

# 67. Migrações

Mudanças de models deverão gerar migration.

Não editar manualmente banco de produção como estratégia normal.

---

# 68. Exclusão de Dados

Antes de excluir entidade relacionada, verificar dependências.

Exemplo:

```text
Datacenter
   │
 possui
   ▼
Rooms
```

Não excluir silenciosamente causando inconsistência.

---

# 69. Transações

Operações que envolvam mudança de dados e auditoria deverão preferencialmente manter consistência transacional.

Não registrar “sucesso” na auditoria se a operação principal falhou.

---

# 70. Segurança de Atualizações

Não atualizar dependências automaticamente em produção sem testes.

Fluxo:

```text
Update
  ↓
Test
  ↓
Security Review
  ↓
Deploy
```

---

# 71. Antes de Encerrar uma Tarefa

O agente deverá informar:

```text
O que foi alterado
Arquivos modificados
Testes executados
Resultados
Riscos pendentes
Próximo passo sugerido
```

---

# 72. Quando Não Tiver Certeza

Se uma decisão tiver impacto relevante em:

- segurança;
- arquitetura;
- banco;
- infraestrutura;
- requisitos;
- CI/CD;

o agente deverá apresentar alternativas e aguardar decisão.

Não assumir silenciosamente.

---

# 73. Regra de Ouro

O agente deve assumir:

```text
Toda entrada é não confiável.

Todo acesso precisa ser autorizado.

Todo segredo precisa permanecer secreto.

Toda operação crítica precisa ser auditável.

Toda mudança importante precisa ser testada.

Toda complexidade precisa ser justificada.
```

---

# 74. Ordem Oficial de Prioridade

Quando houver conflito entre objetivos:

```text
1. Requisitos acadêmicos obrigatórios
2. Segurança
3. Correção funcional
4. Testabilidade
5. Simplicidade
6. Manutenibilidade
7. Aparência
8. Funcionalidades extras
```

O agente não deverá sacrificar itens superiores para melhorar itens inferiores.

---

# 75. Definição de Pronto

Uma funcionalidade será considerada pronta somente quando:

```text
Requisito atendido
      +
Código implementado
      +
Autorização aplicada
      +
Validação aplicada
      +
Segurança revisada
      +
Testes aprovados
      +
Auditoria quando necessária
      +
Documentação coerente
```

---

# 76. Instrução Inicial Recomendada ao Codex

Ao iniciar o desenvolvimento, utilizar uma instrução semelhante a:

```text
Leia integralmente:

- REQUIREMENTS.md
- ARCHITECTURE.md
- SECURITY.md
- AGENTS.md

Não altere nenhum arquivo ainda.

Analise o projeto InfraManager e produza:

1. resumo da arquitetura;
2. requisitos obrigatórios identificados;
3. controles de segurança obrigatórios;
4. estrutura inicial de diretórios;
5. dependências Python mínimas;
6. ordem recomendada de implementação;
7. riscos ou inconsistências encontrados nos documentos.

Não escreva código nesta etapa.
Não adicione tecnologias fora da stack aprovada.
```

Somente após a revisão dessa resposta deverá começar a geração do código.

---

# 77. Princípio Final

O Codex é uma ferramenta de apoio ao desenvolvimento.

As decisões do projeto pertencem ao responsável pelo InfraManager.

O agente deverá:

```text
Analisar
Propor
Implementar
Testar
Revisar
Documentar
```

mas não deverá alterar decisões fundamentais do projeto sem aprovação.
