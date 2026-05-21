import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../core/constants/app_colors.dart';
import '../../providers/onboarding_provider.dart';
import '../../../../shared/widgets/app_text_field.dart';

class ExperienceStep extends ConsumerWidget {
  const ExperienceStep({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(onboardingProvider);
    final notifier = ref.read(onboardingProvider.notifier);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(28.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Experience & Bio',
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tell customers about your skills and experience.',
            style: GoogleFonts.inter(
              fontSize: 15,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 36),
          AppTextField(
            label: 'Years of Experience',
            controller: TextEditingController(
                text: state.draft.experienceYears > 0
                    ? state.draft.experienceYears.toString()
                    : '')
              ..selection = TextSelection.collapsed(
                  offset: state.draft.experienceYears > 0
                      ? state.draft.experienceYears.toString().length
                      : 0),
            keyboardType: TextInputType.number,
            hint: 'e.g. 5',
            prefixIcon: Icons.workspace_premium_outlined,
          ),
          const SizedBox(height: 24),
          AppTextField(
            label: 'Short Bio',
            controller: TextEditingController(text: state.draft.shortBio)
              ..selection = TextSelection.collapsed(
                  offset: state.draft.shortBio.length),
            maxLines: 4,
            hint: 'Describe your expertise and what makes you great...',
          ),
        ],
      ),
    );
  }
}
