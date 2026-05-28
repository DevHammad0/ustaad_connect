import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../core/constants/app_colors.dart';
import '../../providers/onboarding_provider.dart';
import '../../../../shared/widgets/app_text_field.dart';

class ExperienceStep extends ConsumerStatefulWidget {
  const ExperienceStep({super.key});

  @override
  ConsumerState<ExperienceStep> createState() => _ExperienceStepState();
}

class _ExperienceStepState extends ConsumerState<ExperienceStep> {
  late final TextEditingController _expController;
  late final TextEditingController _bioController;

  @override
  void initState() {
    super.initState();
    final draft = ref.read(onboardingProvider).draft;
    _expController = TextEditingController(
      text: draft.experienceYears > 0 ? draft.experienceYears.toString() : '',
    );
    _bioController = TextEditingController(text: draft.shortBio);
  }

  @override
  void dispose() {
    _expController.dispose();
    _bioController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
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
            controller: _expController,
            keyboardType: TextInputType.number,
            hint: 'e.g. 5',
            prefixIcon: Icons.workspace_premium_outlined,
            onChanged: (val) {
              final years = int.tryParse(val) ?? 0;
              notifier.updateDraft(state.draft.copyWith(experienceYears: years));
            },
          ),
          const SizedBox(height: 24),
          AppTextField(
            label: 'Short Bio',
            controller: _bioController,
            maxLines: 4,
            hint: 'Describe your expertise and what makes you great...',
            onChanged: (val) {
              notifier.updateDraft(state.draft.copyWith(shortBio: val));
            },
          ),
        ],
      ),
    );
  }
}
