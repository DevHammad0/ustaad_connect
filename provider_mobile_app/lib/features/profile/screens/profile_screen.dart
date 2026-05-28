import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../auth/providers/auth_provider.dart';
import '../providers/profile_provider.dart';
import '../widgets/profile_header.dart';
import '../widgets/settings_tile.dart';
import '../../../core/constants/app_colors.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(profileProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: profileAsync.when(
        data: (profile) {
          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Dark teal header with profile info
                ProfileHeader(profile: profile),

                const SizedBox(height: 24),

                // Section: Settings
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
                  child: Text(
                    'Account Settings',
                    style: GoogleFonts.poppins(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.8,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                SettingsTile(
                  icon: Icons.person_rounded,
                  title: 'Edit Profile',
                  subtitle: 'Update your personal details and bio',
                  onTap: () => context.push('/profile/edit'),
                ),
                const SizedBox(height: 8),
                SettingsTile(
                  icon: Icons.build_circle_rounded,
                  title: 'Service Settings',
                  subtitle: 'Category, fees, and areas',
                  onTap: () => context.push('/profile/service-settings'),
                  iconColor: AppColors.info,
                ),
                const SizedBox(height: 8),
                SettingsTile(
                  icon: Icons.history_rounded,
                  title: 'Booking History',
                  subtitle: 'View your completed and cancelled jobs',
                  onTap: () => context.push('/history'),
                  iconColor: AppColors.primary,
                ),
                const SizedBox(height: 8),
                SettingsTile(
                  icon: Icons.access_time_rounded,
                  title: 'Availability & Schedule',
                  subtitle: profile.isAvailable
                      ? 'Currently Accepting Jobs'
                      : 'Currently Not Available',
                  onTap: () => context.push('/profile/availability'),
                  iconColor: profile.isAvailable
                      ? AppColors.success
                      : AppColors.warning,
                ),
                const SizedBox(height: 8),
                SettingsTile(
                  icon: Icons.notifications_rounded,
                  title: 'Notifications',
                  subtitle: 'Manage alerts and reminders',
                  onTap: () => context.push('/profile/notifications'),
                  iconColor: AppColors.warning,
                ),

                const SizedBox(height: 32),

                // Logout
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: AppColors.error.withValues(alpha: 0.2),
                      ),
                    ),
                    child: Material(
                        color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(16),
                        onTap: () {
                          ref.read(authProvider.notifier).logout();
                          context.go('/login');
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 16),
                          child: Row(
                            children: [
                              Container(
                                width: 40,
                                height: 40,
                                decoration: BoxDecoration(
                                  color: AppColors.error.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(
                                  Icons.logout_rounded,
                                  color: AppColors.error,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Text(
                                'Log Out',
                                style: GoogleFonts.poppins(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                  color: AppColors.error,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 40),
              ],
            ),
          );
        },
        loading: () => const Center(
            child: CircularProgressIndicator(color: AppColors.primary)),
        error: (e, stack) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
