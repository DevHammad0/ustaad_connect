import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/onboarding_provider.dart';
import '../../../../core/constants/app_colors.dart';

class OnboardingReviewStep extends ConsumerWidget {
  const OnboardingReviewStep({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(onboardingProvider);
    final draft = state.draft;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(28.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Review Profile',
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Ensure all your details are correct before submitting.',
            style: GoogleFonts.inter(
              fontSize: 15,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 36),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.06),
              ),
            ),
            child: Column(
              children: [
                _ReviewSection(
                  icon: Icons.person_outline_rounded,
                  title: 'Personal Info',
                  content: draft.fullName,
                  isFirst: true,
                ),
                _ReviewSection(
                  icon: Icons.build_circle_outlined,
                  title: 'Service Category',
                  content: draft.serviceCategory,
                ),
                _ReviewSection(
                  icon: Icons.map_outlined,
                  title: 'Service Areas',
                  content: draft.serviceAreas.join(', '),
                ),
                _ReviewSection(
                  icon: Icons.payments_outlined,
                  title: 'Visit Fee',
                  content: 'Rs ${draft.visitFee.toStringAsFixed(0)}',
                ),
                _ReviewSection(
                  icon: Icons.workspace_premium_outlined,
                  title: 'Experience',
                  content: '${draft.experienceYears} Years',
                ),
                _ReviewSection(
                  icon: Icons.description_outlined,
                  title: 'Bio',
                  content: draft.shortBio,
                ),
                _ReviewSection(
                  icon: Icons.access_time_rounded,
                  title: 'Working Schedule',
                  content:
                      '${draft.workingDays.join(', ')}\n${draft.startTime} - ${draft.endTime}',
                  isLast: true,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReviewSection extends StatelessWidget {
  final IconData icon;
  final String title;
  final String content;
  final bool isFirst;
  final bool isLast;

  const _ReviewSection({
    required this.icon,
    required this.title,
    required this.content,
    this.isFirst = false,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 20, color: AppColors.primary),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      content.isEmpty ? 'Not Provided' : content,
                      style: GoogleFonts.poppins(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        if (!isLast)
          Divider(
            height: 1,
            thickness: 1,
            color: Colors.black.withValues(alpha: 0.06),
            indent: 66,
          ),
      ],
    );
  }
}
