import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/profile_model.dart';
import '../services/profile_service.dart';

final profileServiceProvider = Provider<ProfileService>((ref) {
  return ProfileService();
});

class ProfileNotifier extends StateNotifier<AsyncValue<ProviderProfileModel>> {
  final ProfileService _service;

  ProfileNotifier(this._service) : super(const AsyncValue.loading()) {
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final profile = await _service.getProfile();
      state = AsyncValue.data(profile);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<bool> updateProfile(ProviderProfileModel updatedProfile) async {
    try {
      // Optimistic update
      state = AsyncValue.data(updatedProfile);
      
      final success = await _service.updateProfile(updatedProfile);
      if (!success) {
        // If failed, reload to get original state
        _loadProfile();
        return false;
      }

      // Refresh to get the latest data (including rating and any server-side changes)
      await _loadProfile();
      return true;
    } catch (e) {
      _loadProfile();
      return false;
    }
  }
}

final profileProvider = StateNotifierProvider<ProfileNotifier, AsyncValue<ProviderProfileModel>>((ref) {
  return ProfileNotifier(ref.watch(profileServiceProvider));
});
