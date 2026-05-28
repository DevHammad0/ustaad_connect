import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../../../shared/models/service_booking.dart';
import '../../../core/session/session_manager.dart';
import '../services/job_service.dart';

final jobServiceProvider = Provider<JobService>((ref) {
  return JobService();
});

class ActiveJobState {
  final ServiceBooking? job;
  final bool isLoading;
  final String? error;

  ActiveJobState({
    this.job,
    this.isLoading = false,
    this.error,
  });

  ActiveJobState copyWith({
    ServiceBooking? job,
    bool? isLoading,
    String? error,
    bool clearJob = false,
    bool clearError = false,
  }) {
    return ActiveJobState(
      job: clearJob ? null : (job ?? this.job),
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class ActiveJobNotifier extends StateNotifier<ActiveJobState> {
  final JobService _service;
  Timer? _pollingTimer;

  ActiveJobNotifier(this._service) : super(ActiveJobState()) {
    _startPolling();
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    // Initial fetch
    _poll();
    // Poll every 10 seconds to reduce network load
    _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      _poll();
    });
  }

  Future<void> _poll() async {
    try {
      final job = await _service.getActiveJob();
      if (mounted) {
        state = state.copyWith(job: job, clearJob: job == null, clearError: true);
        if (job != null && job.apiStatus == 'en_route') {
          _sendLocationUpdate();
        }
      }
    } catch (e) {
      if (mounted) {
        state = state.copyWith(error: e.toString());
      }
    }
  }

  Future<void> _sendLocationUpdate() async {
    final providerId = SessionManager.instance.providerId;
    if (providerId == null) return;

    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.whileInUse ||
          permission == LocationPermission.always) {
        final pos = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.best,
            timeLimit: Duration(seconds: 5),
          ),
        );
        await _service.updateLocation(providerId, pos.latitude, pos.longitude);
      }
    } catch (e) {
      // Fail silently to prevent location error toast during polling
    }
  }

  Future<void> forcePoll() async {
    state = state.copyWith(isLoading: true);
    await _poll();
    state = state.copyWith(isLoading: false);
  }

  Future<void> acceptJob({
    required String bookingId,
    required double minCost,
    required double maxCost,
  }) async {
    await _runAction(() => _service.acceptJob(bookingId, minCost, maxCost));
  }

  Future<void> cancelJob(String bookingId) async {
    await _runAction(() => _service.cancelJob(bookingId));
  }

  Future<void> markEnRoute(String bookingId) async {
    await _runAction(() => _service.updateStatus(bookingId, 'en_route'));
  }

  Future<void> markArrived(String bookingId) async {
    await _runAction(() => _service.updateStatus(bookingId, 'arrived'));
  }

  Future<void> completeJob(String bookingId, double finalCost) async {
    await _runAction(() => _service.completeJob(bookingId, finalCost));
  }

  Future<void> _runAction(Future<void> Function() action) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await action();
      await _poll();
      state = state.copyWith(isLoading: false, clearError: true);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final activeJobProvider = StateNotifierProvider.autoDispose<ActiveJobNotifier, ActiveJobState>((ref) {
  return ActiveJobNotifier(ref.watch(jobServiceProvider));
});
