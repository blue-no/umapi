class ConnectionError(Exception):
    """接続に関する例外クラス."""
    def __init__(self, message):
        super().__init__(message)


class SensingError(Exception):
    """センシングに関する例外クラス."""
    def __init__(self, message):
        super().__init__(message)


class MonitoringError(Exception):
    """モニタリングに関する例外クラス."""
    def __init__(self, message):
        super().__init__(message)
