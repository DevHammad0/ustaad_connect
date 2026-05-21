import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/onboarding_provider.dart';
import '../../../shared/widgets/app_primary_button.dart';
import '../../../core/constants/app_colors.dart';

class OnboardingFlowScreen extends ConsumerStatefulWidget {
  final Widget child;
  const OnboardingFlowScreen({super.key, required this.child});

  @override
  ConsumerState<OnboardingFlowScreen> createState() => _OnboardingFlowScreenState();
}

class _OnboardingFlowScreenState extends ConsumerState<OnboardingFlowScreen> {
  final int _totalSteps = 7;

  final List<String> _routes = [
    '/onboarding/personal-info',
    '/onboarding/service-category',
    '/onboarding/service-area',
    '/onboarding/visit-fee',
    '/onboarding/experience',
    '/onboarding/working-hours',
    '/onboarding/review',
  ];

  int _getCurrentStep(BuildContext context) {
    final path = GoRouterState.of(context).uri.path;
    final index = _routes.indexOf(path);
    return index != -1 ? index : 0;
  }

  void _nextStep(int currentStep) {
    final state = ref.read(onboardingProvider);
    final draft = state.draft;

    // Simple Validation before proceeding
    bool canProceed = false;
    switch (currentStep) {
      case 0:
        canProceed = draft.isPersonalInfoValid;
        break;
      case 1:
        canProceed = draft.isServiceCategoryValid;
        break;
      case 2:
        canProceed = draft.isServiceAreaValid;
        break;
      case 3:
        canProceed = draft.isVisitFeeValid;
        break;
      case 4:
        canProceed = draft.isExperienceValid;
        break;
      case 5:
        canProceed = draft.isWorkingHoursValid;
        break;
      case 6:
        canProceed = true; // Review step, handle submit separately
        break;
    }

    if (!canProceed) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill all required fields correctly.')),
      );
      return;
    }

    if (currentStep < _totalSteps - 1) {
      context.push(_routes[currentStep + 1]);
    } else {
      _submit();
    }
  }

  void _previousStep(int currentStep) {
    if (currentStep > 0) {
      context.pop();
    }
  }

  void _submit() {
    ref.read(onboardingProvider.notifier).submitProfile(ref);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(onboardingProvider);
    final currentStep = _getCurrentStep(context);

    ref.listen<OnboardingState>(onboardingProvider, (previous, next) {
      if (next.isSuccess) {
        context.go('/dashboard'); // Navigate to dashboard
      } else if (next.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(next.error!)),
        );
      }
    });

    return Scaffold(
      appBar: AppBar(
        leading: currentStep > 0
            ? IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => _previousStep(currentStep),
              )
            : null,
        title: Row(
          children: List.generate(
            _totalSteps,
            (index) => Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 2),
                height: 4,
                decoration: BoxDecoration(
                  color: index <= currentStep ? AppColors.primary : AppColors.surface,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: widget.child,
            ),
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: AppPrimaryButton(
                text: currentStep == _totalSteps - 1 ? 'Submit Profile' : 'Next',
                isLoading: state.isLoading,
                onPressed: () => _nextStep(currentStep),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
