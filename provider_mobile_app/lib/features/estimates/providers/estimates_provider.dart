import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/estimate_model.dart';
import '../services/estimates_service.dart';

final estimatesServiceProvider = Provider<EstimatesService>((ref) {
  return EstimatesService();
});

class EstimateState {
  final bool isLoading;
  final String? error;
  final bool isSuccess;

  const EstimateState({
    this.isLoading = false,
    this.error,
    this.isSuccess = false,
  });

  EstimateState copyWith({
    bool? isLoading,
    String? error,
    bool? isSuccess,
    bool clearError = false,
  }) {
    return EstimateState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      isSuccess: isSuccess ?? this.isSuccess,
    );
  }
}

class EstimatesNotifier extends StateNotifier<EstimateState> {
  final EstimatesService _service;

  EstimatesNotifier(this._service) : super(const EstimateState());

  Future<void> submitEstimate(EstimateModel estimate) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final success = await _service.submitEstimate(estimate);
      if (success) {
        state = state.copyWith(isLoading: false, isSuccess: true);
      } else {
        state = state.copyWith(isLoading: false, error: 'Failed to submit estimate');
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<bool> rejectRequest(String requestId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final success = await _service.rejectRequest(requestId);
      state = state.copyWith(isLoading: false);
      return success;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }
}

final estimatesProvider = StateNotifierProvider<EstimatesNotifier, EstimateState>((ref) {
  return EstimatesNotifier(ref.watch(estimatesServiceProvider));
});
