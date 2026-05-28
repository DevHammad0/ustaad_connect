import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/auth_user.dart';
import '../services/auth_service.dart';

// Provider for the AuthService
final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService();
});

// State classes for the AuthNotifier
abstract class AuthState {}

class AuthInitial extends AuthState {}
class AuthLoading extends AuthState {}
class AuthCodeSent extends AuthState {
  final String phone;
  AuthCodeSent(this.phone);
}
class AuthAuthenticated extends AuthState {
  final AuthUser user;
  AuthAuthenticated(this.user);
}
class AuthError extends AuthState {
  final String message;
  AuthError(this.message);
}

// AuthNotifier
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;

  AuthNotifier(this._authService) : super(AuthInitial());

  Future<void> login(String phone) async {
    state = AuthLoading();
    try {
      // For the demo, we call the API to "send" OTP (simulate)
      // and then move to the CodeSent state to trigger navigation to OTP screen.
      await _authService.login(phone);
      state = AuthCodeSent(phone);
    } catch (e) {
      state = AuthError(e.toString());
    }
  }

  Future<void> register({
    required String name,
    required String phone,
    required String serviceType,
    required String city,
    required double visitFee,
    required double lat,
    required double lng,
    String cnic = '',
  }) async {
    state = AuthLoading();
    try {
      final user = await _authService.register(
        name: name,
        phone: phone,
        serviceType: serviceType,
        city: city,
        visitFee: visitFee,
        lat: lat,
        lng: lng,
        cnic: cnic,
      );
      state = AuthAuthenticated(user);
    } catch (e) {
      state = AuthError(e.toString());
    }
  }

  Future<void> verifyOtp(String phone, String otp) async {
    state = AuthLoading();
    try {
      final user = await _authService.verifyOtp(phone, otp);
      state = AuthAuthenticated(user);
    } catch (e) {
      state = AuthError(e.toString());
      // Revert state back to CodeSent so user can try again
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) state = AuthCodeSent(phone);
      });
    }
  }

  void logout() async {
    state = AuthLoading();
    await _authService.logout();
    state = AuthInitial();
  }
}

// Provider for AuthNotifier
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authServiceProvider));
});
