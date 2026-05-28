class ProviderProfileDraft {
  final String fullName;
  final String? profilePhotoUrl;
  final String serviceCategory;
  final List<String> serviceAreas;
  final double visitFee;
  final int experienceYears;
  final String shortBio;
  final String cnic;
  final String? cnicFrontUrl;
  final String? cnicBackUrl;
  final List<String> workingDays;
  final String startTime;
  final String endTime;
  final bool isAvailable;

  const ProviderProfileDraft({
    this.fullName = '',
    this.profilePhotoUrl,
    this.serviceCategory = '',
    this.serviceAreas = const [],
    this.visitFee = 0.0,
    this.experienceYears = 0,
    this.shortBio = '',
    this.cnic = '',
    this.cnicFrontUrl,
    this.cnicBackUrl,
    this.workingDays = const [],
    this.startTime = '09:00 AM',
    this.endTime = '05:00 PM',
    this.isAvailable = true,
  });

  ProviderProfileDraft copyWith({
    String? fullName,
    String? profilePhotoUrl,
    String? serviceCategory,
    List<String>? serviceAreas,
    double? visitFee,
    int? experienceYears,
    String? shortBio,
    String? cnic,
    String? cnicFrontUrl,
    String? cnicBackUrl,
    List<String>? workingDays,
    String? startTime,
    String? endTime,
    bool? isAvailable,
  }) {
    return ProviderProfileDraft(
      fullName: fullName ?? this.fullName,
      profilePhotoUrl: profilePhotoUrl ?? this.profilePhotoUrl,
      serviceCategory: serviceCategory ?? this.serviceCategory,
      serviceAreas: serviceAreas ?? this.serviceAreas,
      visitFee: visitFee ?? this.visitFee,
      experienceYears: experienceYears ?? this.experienceYears,
      shortBio: shortBio ?? this.shortBio,
      cnic: cnic ?? this.cnic,
      cnicFrontUrl: cnicFrontUrl ?? this.cnicFrontUrl,
      cnicBackUrl: cnicBackUrl ?? this.cnicBackUrl,
      workingDays: workingDays ?? this.workingDays,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      isAvailable: isAvailable ?? this.isAvailable,
    );
  }

  bool get isPersonalInfoValid =>
      fullName.trim().isNotEmpty &&
      cnic.trim().isNotEmpty &&
      profilePhotoUrl != null &&
      cnicFrontUrl != null &&
      cnicBackUrl != null;
  bool get isServiceCategoryValid => serviceCategory.isNotEmpty;
  bool get isServiceAreaValid => serviceAreas.isNotEmpty;
  bool get isVisitFeeValid => visitFee > 0;
  bool get isExperienceValid => shortBio.trim().isNotEmpty;
  bool get isWorkingHoursValid => workingDays.isNotEmpty;
}
