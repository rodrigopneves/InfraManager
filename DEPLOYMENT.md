# Implantação do InfraManager

Este documento é um runbook de preparação. Ele não registra uma implantação já
realizada e não substitui a validação da infraestrutura da Etapa 06.

## 1. Arquitetura de runtime

```text
Internet
   |
 HTTPS
   |
 Nginx
   |
 Gunicorn
   |
 Flask
  /   \
SQLite Redis
```

- Nginx termina TLS, aplica HSTS após validação, sobrescreve os cabeçalhos de
  proxy e encaminha somente para o Gunicorn local.
- Gunicorn executa `wsgi:app` com workers síncronos.
- Flask implementa aplicação, autenticação, MFA, RBAC, headers e auditoria.
- SQLite mantém os dados do MVP.
- Redis compartilha os contadores de rate limiting entre workers.
- systemd controla o processo e envia stdout/stderr ao journald.

## 2. Pré-requisitos

- Ubuntu Server compatível com Python 3.14.4;
- usuário administrativo não root com sudo;
- Nginx, Redis e ferramentas SQLite instalados e protegidos;
- código obtido de fonte versionada confiável;
- DNS ou IP público e certificado ainda a serem definidos na Etapa 06.

Os serviços não devem ser expostos além das portas previstas. Gunicorn e Redis
devem aceitar somente conexões locais; nenhum deles deve ficar acessível pela
Internet.

## 3. Diretórios, usuário e permissões

Estrutura recomendada:

```text
/opt/inframanager                         código e virtualenv
/var/lib/inframanager                    banco SQLite e backups
/etc/inframanager/inframanager.env       configuração e secrets
```

Recomendações:

```text
/opt/inframanager                     root:inframanager 0750
/var/lib/inframanager                 inframanager:inframanager 0750
/etc/inframanager                     root:inframanager 0750
/etc/inframanager/inframanager.env    root:inframanager 0640
```

O usuário `inframanager` não deve possuir privilégios administrativos. O código e
a virtualenv devem ser legíveis, mas não graváveis pelo serviço. Somente
`/var/lib/inframanager` precisa ser gravável. Não aplique permissões sem revisar os
paths efetivos no servidor.

## 4. Virtualenv e dependências

No diretório do código, crie a virtualenv com Python 3.14.4 e instale apenas as
dependências versionadas:

```bash
python3.14 -m venv /opt/inframanager/.venv
/opt/inframanager/.venv/bin/python -m pip install -r /opt/inframanager/requirements.txt
/opt/inframanager/.venv/bin/python -m pip check
```

Não atualize dependências diretamente em produção sem executar a suíte e a
auditoria na versão candidata.

## 5. EnvironmentFile

Crie `/etc/inframanager/inframanager.env` a partir dos nomes documentados em
`.env.example`, sem copiar valores reais para o Git:

```text
FLASK_CONFIG=production
SECRET_KEY=<RANDOM_SECRET>
DATABASE_URL=sqlite:////var/lib/inframanager/inframanager.db
MFA_ENCRYPTION_KEY=<FERNET_KEY>
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
LOG_LEVEL=INFO
```

Se Redis exigir credencial, ela fica somente nesse arquivo protegido. Não passe
secrets como argumentos, não os imprima e não inclua o EnvironmentFile em
evidências.

Configuração ausente, vazia ou inválida bloqueia o startup. Uma indisponibilidade
transitória do Redis não bloqueia o import: ela aparece quando uma operação de
rate limiting usa o backend. `/health` verifica apenas o banco nesta etapa.

## 6. SQLite

SQLite é adequado ao volume do MVP. Ele permite múltiplos leitores, mas mantém
escritas serializadas; aumentar workers não aumenta linearmente a capacidade de
escrita e pode elevar a contenção. O ponto inicial é de dois workers.

A aplicação configura:

```text
foreign_keys=ON
busy_timeout=30000
journal_mode=WAL para bancos em arquivo
timeout de conexão=30 segundos
```

WAL melhora a convivência entre leitores e um escritor, mas não remove a
serialização das escritas. Bancos em memória usados nos testes não recebem WAL.
Não coloque o banco em filesystem de rede. Se a carga ou concorrência crescer,
PostgreSQL deve ser avaliado como evolução futura, não como alteração direta do
MVP.

## 7. Redis

Produção aceita somente `redis://` ou `rediss://` em
`RATELIMIT_STORAGE_URI`. `memory://` fica restrito a development/testing. Antes de
ativar a aplicação, valide que o Redis local está protegido, não possui porta
pública e aplica a política de autenticação escolhida.

Este repositório contém apenas o cliente Python. Instalação, configuração,
persistência e supervisão do servidor Redis pertencem à implantação.

## 8. Migrações e dados MFA legados

Com o serviço parado e um backup validado, carregue o ambiente protegido e execute:

```bash
sudo -u inframanager bash -c 'set -a; source /etc/inframanager/inframanager.env; exec /opt/inframanager/.venv/bin/flask --app wsgi db upgrade'
sudo -u inframanager bash -c 'set -a; source /etc/inframanager/inframanager.env; exec /opt/inframanager/.venv/bin/flask --app wsgi encrypt-mfa-secrets'
```

O segundo comando é idempotente e necessário somente quando houver valores MFA
legados. Não troque a chave Fernet antes de converter esses valores.

## 9. Gunicorn

`gunicorn.conf.py` usa:

```text
bind=127.0.0.1:8000
workers=2
worker_class=sync
timeout=30
graceful_timeout=30
keepalive=5
```

O bind loopback impede acesso externo direto e é simples para a primeira
integração com Nginx. Access e error logs vão para stdout/stderr. O access log
registra IP, método, path sem query string, status, tamanho e duração; não registra
cookies, Authorization, corpo ou query string.

Validação manual antes do serviço:

```bash
/opt/inframanager/.venv/bin/gunicorn -c /opt/inframanager/gunicorn.conf.py wsgi:app
```

## 10. systemd

Copie `deploy/systemd/inframanager.service.example` para a área de units somente
depois de revisar usuário, grupo e paths. O exemplo executa diretamente o Gunicorn,
reinicia apenas em falha e envia logs ao journald.

Após instalar ou alterar a unit:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now inframanager
sudo systemctl status inframanager
sudo journalctl -u inframanager
```

Não copie saídas que contenham dados sensíveis para evidências.

## 11. Nginx e arquivos estáticos

`deploy/nginx/inframanager.conf.example` contém os blocos HTTP e HTTPS. Substitua
os placeholders somente no servidor e valide com `nginx -t` antes de recarregar.

O Nginx deve sobrescrever `Host`, `X-Real-IP`, `X-Forwarded-For` e
`X-Forwarded-Proto`. A aplicação confia em exatamente um proxy. Gunicorn deve
continuar em loopback; essa restrição é parte do controle de segurança do
ProxyFix.

Nesta versão, `/static` continua sendo servido pelo Flask através do proxy. Isso
evita duplicar configuração e mantém a política de cache já testada. O limite de
corpo no Nginx é `64k`, coerente com `MAX_CONTENT_LENGTH` da aplicação.

## 12. HTTPS e HSTS

Use Certbot conforme os requisitos do projeto e valide primeiro em staging. Os
paths do certificado no exemplo são placeholders. HTTP deve permanecer disponível
para o desafio ACME e redirecionar as demais requisições para HTTPS.

O HSTS está comentado no exemplo. Habilite-o somente depois de confirmar certificado,
renovação, redirecionamento e acesso HTTPS de ponta a ponta. A política inicial usa
`max-age=31536000`, sem `preload` e sem `includeSubDomains`.

## 13. Health check

Após iniciar os componentes:

```bash
curl --fail --silent https://<SERVER_NAME>/health
```

Resposta saudável:

```json
{"status":"ok"}
```

Falha na consulta mínima ao banco retorna HTTP 503 e
`{"status":"unavailable"}`. A resposta não contém URL, path, SQL detalhado ou
exceção. Redis não integra esse health check nesta etapa.

## 14. Backup SQLite

Crie o diretório de backups com as mesmas restrições dos dados. Para backup online,
use a API de backup do SQLite por meio do comando `.backup`, que considera o estado
WAL melhor que uma cópia crua durante escrita:

```bash
sudo -u inframanager sqlite3 /var/lib/inframanager/inframanager.db ".backup '/var/lib/inframanager/backups/inframanager.db.backup'"
sudo -u inframanager sqlite3 /var/lib/inframanager/backups/inframanager.db.backup "PRAGMA integrity_check;"
```

O resultado da validação deve ser `ok`. Preserve owner, grupo e modo do backup,
proteja sua retenção e nunca o envie ao repositório.

Antes de migration ou rotação Fernet, prefira parar o serviço e gerar um backup
validado. Não copie apenas o arquivo `.db` durante escrita ativa, principalmente
quando existirem arquivos `-wal` e `-shm`.

## 15. Restore SQLite

1. Pare o serviço.
2. Valide o backup com `PRAGMA integrity_check`.
3. Preserve uma cópia protegida do banco atual para reversão.
4. Restaure o backup para `/var/lib/inframanager/inframanager.db`.
5. Reaplique owner `inframanager:inframanager` e o modo restritivo definido.
6. Execute `flask db upgrade` somente se a versão do código exigir.
7. Inicie o serviço, consulte `/health` e execute o smoke test autenticado.

Teste periodicamente uma restauração em ambiente isolado. Um backup nunca testado
não deve ser considerado recuperável.

## 16. Rotação da chave Fernet

O comando é:

```text
flask --app wsgi rotate-mfa-key
```

Procedimento:

1. Prepare uma nova chave Fernet fora do repositório.
2. Pare a aplicação para impedir escritas concorrentes.
3. Faça e valide o backup SQLite.
4. Execute o comando com o EnvironmentFile atual carregado.
5. Informe a chave atual e a nova nos prompts ocultos; não use argumentos de shell.
6. Após sucesso, substitua `MFA_ENCRYPTION_KEY` no EnvironmentFile protegido.
7. Inicie o serviço e valide Login/MFA com conta fictícia de teste.
8. Remova com segurança cópias desnecessárias da chave antiga após o período de
   rollback definido.

O comando valida ambas as chaves antes de alterar dados, bloqueia segredos legados,
descriptografa todo o conjunto com a chave antiga, cifra com a nova e confirma uma
única transação. Chave antiga incorreta, chave nova inválida ou falha de banco
causam rollback completo. As chaves não são registradas nem exibidas.

Se o comando falhar, o banco e o EnvironmentFile permanecem com a chave antiga. Se
ele concluir mas o smoke test falhar, mantenha o serviço parado e restaure juntos o
backup do banco e o EnvironmentFile anterior.

## 17. Atualização segura

1. Confirme a versão candidata e os testes da CI.
2. Faça backup do SQLite e valide sua integridade.
3. Pare ou controle o serviço durante mudanças de schema.
4. Atualize o código a partir da referência versionada esperada.
5. Atualize a virtualenv com `requirements.txt`.
6. Execute `pip check` e as migrations.
7. Execute testes aplicáveis e um startup check local.
8. Reinicie o serviço.
9. Verifique `/health`, logs e um smoke test funcional.
10. Em falha, pare o serviço e restaure código, banco e configuração compatíveis.

Não execute downgrade destrutivo de migration sem avaliar os dados afetados.

## 18. Troubleshooting básico

- Startup bloqueado: confira apenas a presença e o formato das variáveis; não as
  imprima no terminal ou nos logs.
- HTTP 503 em `/health`: verifique permissões do diretório, existência do banco,
  espaço livre, locks e migrations.
- Erro no rate limiting: confirme processo Redis, URI protegida e conectividade
  local. A ausência do Redis não deve ser contornada com `memory://` em produção.
- IP incorreto: confirme que somente Nginx alcança Gunicorn e que o proxy
  sobrescreve os cabeçalhos conforme o exemplo.
- Falha de MFA após rotação: pare o serviço; não repita rotações às cegas. Restaure
  o par consistente banco/configuração e investigue sem expor as chaves.
- Erro de inicialização: consulte `journalctl -u inframanager` sem publicar dados
  sensíveis.
