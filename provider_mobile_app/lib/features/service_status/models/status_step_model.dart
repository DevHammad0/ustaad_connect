enum ServiceStatusStep {
  accepted('Accepted'),
  enRoute('En Route'),
  arrived('Arrived'),
  workStarted('Work Started'),
  completed('Completed'),
  cancelled('Cancelled');

  final String label;
  const ServiceStatusStep(this.label);
}

extension ServiceStatusStepExtension on ServiceStatusStep {
  ServiceStatusStep? get nextStep {
    switch (this) {
      case ServiceStatusStep.accepted:
        return ServiceStatusStep.enRoute;
      case ServiceStatusStep.enRoute:
        return ServiceStatusStep.arrived;
      case ServiceStatusStep.arrived:
        return ServiceStatusStep.workStarted;
      case ServiceStatusStep.workStarted:
        return ServiceStatusStep.completed;
      case ServiceStatusStep.completed:
      case ServiceStatusStep.cancelled:
        return null;
    }
  }
}
