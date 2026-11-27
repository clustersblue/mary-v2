import ssl
from unittest.mock import patch

from app.db.session import database_connection


def test_plain_database_url_has_no_ssl_argument():
    url, connect_args = database_connection(
        "mysql+aiomysql://user:secret@127.0.0.1:3306/mary"
    )

    assert url.host == "127.0.0.1"
    assert connect_args == {}


def test_certificate_path_becomes_an_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    with patch("app.db.session.ssl.create_default_context", return_value=context) as create:
        url, connect_args = database_connection(
            "mysql+aiomysql://user:secret@db.example:25060/mary"
            "?ssl_ca=/etc/ssl/certs/do-mysql-ca.crt&ssl-mode=REQUIRED"
        )

    create.assert_called_once_with(cafile="/etc/ssl/certs/do-mysql-ca.crt")
    assert "ssl_ca" not in url.query
    assert "ssl-mode" not in url.query
    assert connect_args["ssl"] is context
    assert context.check_hostname is False
    assert context.verify_mode == ssl.CERT_REQUIRED
