from socket import error

class TeamspeakConnectionError(error):
    pass

class TeamspeakConnectionLost(TeamspeakConnectionError):
    pass

class TeamspeakConnectionTelnetEOF(TeamspeakConnectionLost):
    pass

class TeamspeakConnectionFailed(TeamspeakConnectionError):
    pass
