class AuthUser {
  final String id;
  final String phone;
  final String? name;
  final bool isProfileComplete;
  final bool isVerified;

  AuthUser({
    required this.id,
    required this.phone,
    this.name,
    this.isProfileComplete = false,
    this.isVerified = false,
  });

  AuthUser copyWith({
    String? id,
    String? phone,
    String? name,
    bool? isProfileComplete,
    bool? isVerified,
  }) {
    return AuthUser(
      id: id ?? this.id,
      phone: phone ?? this.phone,
      name: name ?? this.name,
      isProfileComplete: isProfileComplete ?? this.isProfileComplete,
      isVerified: isVerified ?? this.isVerified,
    );
  }
}
