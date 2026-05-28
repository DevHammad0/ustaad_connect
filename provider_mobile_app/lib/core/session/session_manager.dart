import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure persistent session manager.
/// Stores the logged-in provider's ID returned by the backend after login.
class SessionManager {
  SessionManager._();
  static final SessionManager instance = SessionManager._();

  static void Function()? onSessionExpired;

  static const _storage = FlutterSecureStorage();

  String? _providerId;
  String? _providerToken;

  String? get providerId => _providerId;
  String? get providerToken => _providerToken;

  bool get isLoggedIn => _providerId != null;

  Future<void> init() async {
    _providerId = await _storage.read(key: 'provider_id');
    _providerToken = await _storage.read(key: 'provider_token');
  }

  Future<void> setSession({required String providerId, String? token}) async {
    _providerId = providerId;
    _providerToken = token;
    await _storage.write(key: 'provider_id', value: providerId);
    if (token != null) {
      await _storage.write(key: 'provider_token', value: token);
    } else {
      await _storage.delete(key: 'provider_token');
    }
  }

  Future<void> clearSession() async {
    _providerId = null;
    _providerToken = null;
    await _storage.delete(key: 'provider_id');
    await _storage.delete(key: 'provider_token');
  }
}
