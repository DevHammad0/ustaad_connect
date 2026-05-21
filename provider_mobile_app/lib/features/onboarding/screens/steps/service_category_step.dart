import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../core/constants/app_colors.dart';
import '../../providers/onboarding_provider.dart';

class ServiceCategoryStep extends ConsumerWidget {
  const ServiceCategoryStep({super.key});

  static const List<String> dummyCategories = [
    'AC Repair',
    'Electrician',
    'Plumbing',
    'Cleaning',
    'Appliance Repair',
    'Carpenter',
    'Painter',
  ];

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
            'What services do you provide?',
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Select your primary service category.',
            style: GoogleFonts.inter(
              fontSize: 15,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 36),
          Wrap(
            spacing: 12,
            runSpacing: 14,
            children: dummyCategories.map((category) {
              final isSelected = state.draft.serviceCategory == category;
              return ChoiceChip(
                label: Text(category),
                selected: isSelected,
                selectedColor: AppColors.primary,
                labelStyle: GoogleFonts.inter(
                  color: isSelected ? Colors.white : AppColors.textPrimary,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  fontSize: 14,
                ),
                backgroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(50),
                  side: BorderSide(
                    color: isSelected
                        ? Colors.transparent
                        : Colors.black.withValues(alpha: 0.08),
                  ),
                ),
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 12),
                showCheckmark: false,
                onSelected: (selected) {
                  if (selected) {
                    notifier.updateDraft(
                        state.draft.copyWith(serviceCategory: category));
                  }
                },
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
