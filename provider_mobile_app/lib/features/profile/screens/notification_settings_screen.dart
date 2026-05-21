import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/profile_provider.dart';
import '../../../core/constants/app_colors.dart';

class NotificationSettingsScreen extends ConsumerWidget {
  const NotificationSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(profileProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        slivers: [
          // ── Header ────────────────────────────────────────────────
          SliverAppBar(
            pinned: true,
            expandedHeight: 130,
            backgroundColor: AppColors.darkTeal,
            elevation: 0,
            scrolledUnderElevation: 0,
            leading: GestureDetector(
              onTap: () => context.pop(),
              child: Container(
                margin: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.arrow_back_ios_new_rounded,
                    color: Colors.white, size: 16),
              ),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: AppColors.primaryGradient,
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text('Notifications',
                            style: GoogleFonts.poppins(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                            )),
                        Text('Choose what alerts you receive',
                            style: GoogleFonts.inter(
                              color: AppColors.textOnDarkMuted,
                              fontSize: 12,
                            )),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

          // ── Content ───────────────────────────────────────────────
          profileAsync.when(
            data: (profile) => SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  _NotifCard(
                    icon: Icons.add_alert_rounded,
                    title: 'New Service Requests',
                    subtitle: 'Get notified when a customer sends a request',
                    value: profile.notifyNewRequests,
                    color: AppColors.warning,
                    onChanged: (val) => ref
                        .read(profileProvider.notifier)
                        .updateProfile(
                            profile.copyWith(notifyNewRequests: val)),
                  ),
                  const SizedBox(height: 10),
                  _NotifCard(
                    icon: Icons.check_circle_rounded,
                    title: 'Booking Confirmations',
                    subtitle: 'Alert when a customer accepts your estimate',
                    value: profile.notifyConfirmations,
                    color: AppColors.success,
                    onChanged: (val) => ref
                        .read(profileProvider.notifier)
                        .updateProfile(
                            profile.copyWith(notifyConfirmations: val)),
                  ),
                  const SizedBox(height: 10),
                  _NotifCard(
                    icon: Icons.access_time_filled_rounded,
                    title: 'Reminders',
                    subtitle: 'Upcoming visit reminders before your job',
                    value: profile.notifyReminders,
                    color: AppColors.info,
                    onChanged: (val) => ref
                        .read(profileProvider.notifier)
                        .updateProfile(
                            profile.copyWith(notifyReminders: val)),
                  ),
                  const SizedBox(height: 10),
                  _NotifCard(
                    icon: Icons.info_rounded,
                    title: 'Service Updates',
                    subtitle: 'Status changes and general app updates',
                    value: profile.notifyServiceUpdates,
                    color: AppColors.primary,
                    onChanged: (val) => ref
                        .read(profileProvider.notifier)
                        .updateProfile(
                            profile.copyWith(notifyServiceUpdates: val)),
                  ),
                ]),
              ),
            ),
            loading: () => const SliverFillRemaining(
              child: Center(
                  child:
                      CircularProgressIndicator(color: AppColors.primary)),
            ),
            error: (e, _) => SliverFillRemaining(
              child: Center(child: Text('Error: $e')),
            ),
          ),
        ],
      ),
    );
  }
}

class _NotifCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final Color color;
  final ValueChanged<bool> onChanged;

  const _NotifCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.color,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: value
              ? color.withValues(alpha: 0.25)
              : Colors.black.withValues(alpha: 0.06),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.poppins(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  subtitle,
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: color,
          ),
        ],
      ),
    );
  }
}
