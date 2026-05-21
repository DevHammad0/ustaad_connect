import 'package:flutter/material.dart';
import '../models/status_step_model.dart';
import '../../../shared/widgets/app_primary_button.dart';

class StatusActionButton extends StatelessWidget {
  final ServiceStatusStep currentStatus;
  final bool isLoading;
  final VoidCallback onAdvance;

  const StatusActionButton({
    super.key,
    required this.currentStatus,
    required this.isLoading,
    required this.onAdvance,
  });

  @override
  Widget build(BuildContext context) {
    if (currentStatus == ServiceStatusStep.completed || currentStatus == ServiceStatusStep.cancelled) {
      return const SizedBox.shrink();
    }

    final nextStep = currentStatus.nextStep;
    if (nextStep == null) return const SizedBox.shrink();

    String buttonText = 'Mark as ${nextStep.label}';
    if (nextStep == ServiceStatusStep.enRoute) {
      buttonText = 'Start Journey';
    } else if (nextStep == ServiceStatusStep.completed) {
      buttonText = 'Complete Job';
    }

    return AppPrimaryButton(
      text: buttonText,
      isLoading: isLoading,
      onPressed: onAdvance,
    );
  }
}
