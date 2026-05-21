import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/status_step_model.dart';
import '../services/service_status_service.dart';

final serviceStatusServiceProvider = Provider<ServiceStatusService>((ref) {
  return ServiceStatusService();
});

class ServiceStatusState {
  final ServiceStatusStep currentStatus;
  final bool isLoading;
  final String? error;
  final bool isJobFinished; // True if completed or cancelled

  const ServiceStatusState({
    this.currentStatus = ServiceStatusStep.accepted,
    this.isLoading = false,
    this.error,
    this.isJobFinished = false,
  });

  ServiceStatusState copyWith({
    ServiceStatusStep? currentStatus,
    bool? isLoading,
    String? error,
    bool? isJobFinished,
    bool clearError = false,
  }) {
    return ServiceStatusState(
      currentStatus: currentStatus ?? this.currentStatus,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      isJobFinished: isJobFinished ?? this.isJobFinished,
    );
  }
}

class ServiceStatusNotifier extends StateNotifier<ServiceStatusState> {
  final ServiceStatusService _service;
  final String bookingId;

  ServiceStatusNotifier(this._service, this.bookingId) : super(const ServiceStatusState());

  Future<void> advanceStatus() async {
    final nextStep = state.currentStatus.nextStep;
    if (nextStep == null) return;
    await _updateToStatus(nextStep);
  }

  Future<void> cancelJob() async {
    await _updateToStatus(ServiceStatusStep.cancelled);
  }

  Future<void> completeJob(double finalCost) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final success = await _service.completeBooking(
        bookingId,
        finalCost: finalCost.round(),
      );
      if (success) {
        state = state.copyWith(
          currentStatus: ServiceStatusStep.completed,
          isLoading: false,
          isJobFinished: true,
        );
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to complete job',
        );
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> _updateToStatus(ServiceStatusStep newStatus) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final success = await _service.updateStatus(bookingId, newStatus);
      if (success) {
        final isFinished = newStatus == ServiceStatusStep.completed || newStatus == ServiceStatusStep.cancelled;
        state = state.copyWith(
          currentStatus: newStatus,
          isLoading: false,
          isJobFinished: isFinished,
        );
      } else {
        state = state.copyWith(isLoading: false, error: 'Failed to update status');
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

// Family provider to instantiate a notifier per booking ID
final serviceStatusProvider = StateNotifierProvider.family<ServiceStatusNotifier, ServiceStatusState, String>((ref, bookingId) {
  final service = ref.watch(serviceStatusServiceProvider);
  return ServiceStatusNotifier(service, bookingId);
});
