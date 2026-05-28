class ProviderProfileModel {
  final String id;
  final String fullName;
  final String phoneNumber;
  final String profilePhotoUrl;
  final String profilePhotoLocalPath; // locally picked image, not yet synced
  final double rating;
  final String bio;
  final int experienceYears;
  final String cnic;
  final bool isVerified;
  final String cnicFrontUrl;
  final String cnicBackUrl;

  // Service Settings
  final String serviceCategory;
  final double visitFee;
  final List<String> serviceAreas;
  
  // Availability
  final bool isAvailable;
  final List<String> workingDays;
  final String startTime;
  final String endTime;

  // Notifications
  final bool notifyNewRequests;
  final bool notifyConfirmations;
  final bool notifyReminders;
  final bool notifyServiceUpdates;

  const ProviderProfileModel({
    required this.id,
    required this.fullName,
    required this.phoneNumber,
    this.profilePhotoUrl = '',
    this.profilePhotoLocalPath = '',
    this.rating = 0.0,
    required this.bio,
    required this.experienceYears,
    this.cnic = '',
    this.isVerified = false,
    this.cnicFrontUrl = '',
    this.cnicBackUrl = '',
    required this.serviceCategory,
    required this.visitFee,
    required this.serviceAreas,
    this.isAvailable = true,
    required this.workingDays,
    required this.startTime,
    required this.endTime,
    this.notifyNewRequests = true,
    this.notifyConfirmations = true,
    this.notifyReminders = true,
    this.notifyServiceUpdates = true,
  });

  ProviderProfileModel copyWith({
    String? fullName,
    String? phoneNumber,
    String? profilePhotoUrl,
    String? profilePhotoLocalPath,
    String? bio,
    int? experienceYears,
    String? cnic,
    bool? isVerified,
    String? cnicFrontUrl,
    String? cnicBackUrl,
    String? serviceCategory,
    double? visitFee,
    List<String>? serviceAreas,
    bool? isAvailable,
    List<String>? workingDays,
    String? startTime,
    String? endTime,
    bool? notifyNewRequests,
    bool? notifyConfirmations,
    bool? notifyReminders,
    bool? notifyServiceUpdates,
  }) {
    return ProviderProfileModel(
      id: id,
      fullName: fullName ?? this.fullName,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      profilePhotoUrl: profilePhotoUrl ?? this.profilePhotoUrl,
      profilePhotoLocalPath: profilePhotoLocalPath ?? this.profilePhotoLocalPath,
      rating: rating,
      bio: bio ?? this.bio,
      experienceYears: experienceYears ?? this.experienceYears,
      cnic: cnic ?? this.cnic,
      isVerified: isVerified ?? this.isVerified,
      cnicFrontUrl: cnicFrontUrl ?? this.cnicFrontUrl,
      cnicBackUrl: cnicBackUrl ?? this.cnicBackUrl,
      serviceCategory: serviceCategory ?? this.serviceCategory,
      visitFee: visitFee ?? this.visitFee,
      serviceAreas: serviceAreas ?? this.serviceAreas,
      isAvailable: isAvailable ?? this.isAvailable,
      workingDays: workingDays ?? this.workingDays,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      notifyNewRequests: notifyNewRequests ?? this.notifyNewRequests,
      notifyConfirmations: notifyConfirmations ?? this.notifyConfirmations,
      notifyReminders: notifyReminders ?? this.notifyReminders,
      notifyServiceUpdates: notifyServiceUpdates ?? this.notifyServiceUpdates,
    );
  }
}
