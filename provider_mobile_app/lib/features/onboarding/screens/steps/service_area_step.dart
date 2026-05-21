import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../core/constants/app_colors.dart';
import '../../providers/onboarding_provider.dart';

class ServiceAreaStep extends ConsumerWidget {
  const ServiceAreaStep({super.key});

  static const List<String> dummyAreas = [
    'Islamabad',
    'Rawalpindi',
    'G-13',
    'F-10',
    'F-11',
    'Bahria Town',
    'DHA',
    'Peshawar',
    'Hayatabad',
    'University Road',
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
            'Where do you work?',
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Select the areas you are willing to visit.',
            style: GoogleFonts.inter(
              fontSize: 15,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 36),
          Wrap(
            spacing: 10,
            runSpacing: 12,
            children: dummyAreas.map((area) {
              final isSelected = state.draft.serviceAreas.contains(area);
              return FilterChip(
                label: Text(area),
                selected: isSelected,
                selectedColor: AppColors.primary.withValues(alpha: 0.15),
                checkmarkColor: AppColors.primary,
                labelStyle: GoogleFonts.inter(
                  color:
                      isSelected ? AppColors.primary : AppColors.textPrimary,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  fontSize: 14,
                ),
                backgroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(50),
                  side: BorderSide(
                    color: isSelected
                        ? AppColors.primary.withValues(alpha: 0.5)
                        : Colors.black.withValues(alpha: 0.08),
                    width: isSelected ? 1.5 : 1,
                  ),
                ),
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 10),
                onSelected: (selected) {
                  final areas = List<String>.from(state.draft.serviceAreas);
                  if (selected) {
                    areas.add(area);
                  } else {
                    areas.remove(area);
                  }
                  notifier
                      .updateDraft(state.draft.copyWith(serviceAreas: areas));
                },
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
