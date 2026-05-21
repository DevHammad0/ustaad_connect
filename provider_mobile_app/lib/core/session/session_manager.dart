/// Simple in-memory session manager.
/// Stores the logged-in provider's ID returned by the backend after login.
/// TODO: Persist using flutter_secure_storage in production.
class SessionManager {
  SessionManager._();
  static final SessionManager instance = SessionManager._();

  String? _providerId;
  String? _providerToken; // reserved for future JWT token support

  String? get providerId => _providerId;
  String? get providerToken => _providerToken;

  bool get isLoggedIn => _providerId != null;

  void setSession({required String providerId, String? token}) {
    _providerId = providerId;
    _providerToken = token;
  }

  void clearSession() {
    _providerId = null;
    _providerToken = null;
  }
}
