"""Sanitized database failure categories shared by startup and read-only diagnostics."""

def error_category(exc):
    """Classify internally; never emit raw driver errors (they can contain credentials)."""
    message = str(exc).lower()
    if any(term in message for term in ("dns", "srv", "nameserver", "resolution lifetime", "nxdomain")):
        if any(term in message for term in ("timed out", "timeout", "lifetime")):
            return "dns_srv_resolution_timeout"
        return "dns_srv_resolution_failed"
    if any(term in message for term in ("certificate", "ssl", "tls")):
        return "tls_handshake_failed"
    if getattr(exc, "code", None) == 13:
        return "database_authorization_failed"
    if getattr(exc, "code", None) == 18:
        return "database_authentication_failed"
    if type(exc).__name__ == "ServerSelectionTimeoutError":
        return "database_server_selection_timeout"
    if type(exc).__name__ in ("InvalidURI", "ConfigurationError"):
        return "mongodb_configuration_invalid"
    if isinstance(exc, KeyError):
        return "required_configuration_missing"
    return "diagnostic_unavailable"
