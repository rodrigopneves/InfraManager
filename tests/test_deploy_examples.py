from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_nginx_example_preserves_proxy_security_contract() -> None:
    content = (
        PROJECT_ROOT / "deploy/nginx/inframanager.conf.example"
    ).read_text()

    assert "proxy_pass http://127.0.0.1:8000;" in content
    assert "proxy_set_header Host $host;" in content
    assert "proxy_set_header X-Real-IP $remote_addr;" in content
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in content
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in content
    assert "client_max_body_size 64k;" in content
    assert "0.0.0.0" not in content
    assert "preload" not in _active_nginx_lines(content)
    assert "includeSubDomains" not in _active_nginx_lines(content)


def test_systemd_example_keeps_runtime_local_and_data_writable() -> None:
    content = (
        PROJECT_ROOT / "deploy/systemd/inframanager.service.example"
    ).read_text()

    assert "User=inframanager" in content
    assert "Group=inframanager" in content
    assert "EnvironmentFile=/etc/inframanager/inframanager.env" in content
    assert "wsgi:app" in content
    assert "NoNewPrivileges=true" in content
    assert "PrivateTmp=true" in content
    assert "ProtectSystem=strict" in content
    assert "ProtectHome=true" in content
    assert "ReadWritePaths=/var/lib/inframanager" in content
    assert "UMask=0027" in content
    assert "0.0.0.0" not in content


def test_deploy_examples_contain_no_secret_values_or_personal_paths() -> None:
    paths = [
        PROJECT_ROOT / "gunicorn.conf.py",
        PROJECT_ROOT / "deploy/nginx/inframanager.conf.example",
        PROJECT_ROOT / "deploy/systemd/inframanager.service.example",
        PROJECT_ROOT / "DEPLOYMENT.md",
    ]
    content = "\n".join(path.read_text() for path in paths)

    assert "/home/" not in content
    assert "BEGIN PRIVATE KEY" not in content
    assert "SECRET_KEY=<RANDOM_SECRET>" in content
    assert "MFA_ENCRYPTION_KEY=<FERNET_KEY>" in content


def _active_nginx_lines(content: str) -> str:
    return "\n".join(
        line for line in content.splitlines() if not line.lstrip().startswith("#")
    )
