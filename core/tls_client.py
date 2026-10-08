import socket
import ssl


def get_certificate(domain, port=443, timeout=5):
    """Récupère le certificat d'un domaine après validation TLS."""
    context = ssl.create_default_context()

    with socket.create_connection((domain, port), timeout=timeout) as connection:
        with context.wrap_socket(connection, server_hostname=domain) as tls_connection:
            return tls_connection.getpeercert()
