import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/onboarding_model.dart';
import '../services/onboarding_service.dart';
import '../../auth/providers/auth_provider.dart';

final onboardingServiceProvider = Provider<OnboardingService>((ref) {
  return OnboardingService();
});

class OnboardingState {
  final ProviderProfileDraft draft;
  final bool isLoading;
  final String? error;
  final bool isSuccess;

  OnboardingState({
    this.draft = const ProviderProfileDraft(),
    this.isLoading = false,
    this.error,
    this.isSuccess = false,
  });

  OnboardingState copyWith({
    ProviderProfileDraft? draft,
    bool? isLoading,
    String? error,
    bool? isSuccess,
    bool clearError = false,
  }) {
    return OnboardingState(
      draft: draft ?? this.draft,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      isSuccess: isSuccess ?? this.isSuccess,
    );
  }
}

class OnboardingNotifier extends StateNotifier<OnboardingState> {
  final OnboardingService _service;
  final StateNotifierProvider<AuthNotifier, AuthState> _authProvider;

  OnboardingNotifier(this._service, this._authProvider) : super(OnboardingState());

  void updateDraft(ProviderProfileDraft newDraft) {
    state = state.copyWith(draft: newDraft, clearError: true);
  }

  Future<void> submitProfile(WidgetRef ref) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final authState = ref.read(_authProvider);
      final phone = authState is AuthAuthenticated
          ? authState.user.phone
          : '';
      final success = await _service.saveProviderProfile(
        state.draft,
        phone: phone,
      );
      if (success) {
        state = state.copyWith(isLoading: false, isSuccess: true);
      } else {
        state = state.copyWith(isLoading: false, error: 'Failed to save profile. Please try again.');
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final onboardingProvider = StateNotifierProvider<OnboardingNotifier, OnboardingState>((ref) {
  return OnboardingNotifier(
    ref.watch(onboardingServiceProvider),
    authProvider,
  );
});
