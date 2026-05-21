class AuthUser {
  final String id;
  final String phone;
  final String? name;
  final bool isProfileComplete;

  AuthUser({
    required this.id,
    required this.phone,
    this.name,
    this.isProfileComplete = false,
  });

  AuthUser copyWith({
    String? id,
    String? phone,
    String? name,
    bool? isProfileComplete,
  }) {
    return AuthUser(
      id: id ?? this.id,
      phone: phone ?? this.phone,
      name: name ?? this.name,
      isProfileComplete: isProfileComplete ?? this.isProfileComplete,
    );
  }
}
