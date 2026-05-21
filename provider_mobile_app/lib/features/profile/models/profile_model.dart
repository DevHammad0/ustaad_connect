class ProviderProfileModel {
  final String id;
  final String fullName;
  final String phoneNumber;
  final String profilePhotoUrl;
  final double rating;
  final String bio;
  final int experienceYears;
  final String cnic;

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
    this.rating = 0.0,
    required this.bio,
    required this.experienceYears,
    this.cnic = '',
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
    String? bio,
    int? experienceYears,
    String? cnic,
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
      profilePhotoUrl: profilePhotoUrl,
      rating: rating,
      bio: bio ?? this.bio,
      experienceYears: experienceYears ?? this.experienceYears,
      cnic: cnic ?? this.cnic,
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
