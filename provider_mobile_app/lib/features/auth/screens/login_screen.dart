import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import '../../../core/constants/dummy_data.dart';
import '../providers/auth_provider.dart';
import '../widgets/phone_input.dart';
import '../../../shared/widgets/app_primary_button.dart';
import '../../../shared/widgets/app_card.dart';
import '../../../shared/widgets/app_location_map.dart';
import '../../../core/constants/app_colors.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _cityController =
      TextEditingController(text: 'peshawar');
  final TextEditingController _feeController =
      TextEditingController(text: '500');
  final TextEditingController _latController =
      TextEditingController(text: '34.00');
  final TextEditingController _lngController =
      TextEditingController(text: '71.50');
  final TextEditingController _cnicController = TextEditingController();
  late AnimationController _animController;
  late Animation<Offset> _slideAnim;
  late Animation<double> _fadeAnim;
  bool _showRegister = false;
  String _selectedService = 'AC Repair';
  bool _isFetchingLocation = false;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.12),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _animController, curve: Curves.easeOut));
    _fadeAnim =
        CurvedAnimation(parent: _animController, curve: Curves.easeOut);
    _animController.forward();
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _nameController.dispose();
    _cityController.dispose();
    _feeController.dispose();
    _latController.dispose();
    _lngController.dispose();
    _cnicController.dispose();
    _animController.dispose();
    super.dispose();
  }

  void _handleLogin() {
    final phone = _phoneController.text.trim();
    if (phone.isNotEmpty) {
      ref.read(authProvider.notifier).login(phone);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid phone number')),
      );
    }
  }

  void _handleRegister() {
    final name = _nameController.text.trim();
    final phone = _phoneController.text.trim();
    final city = _cityController.text.trim();
    final visitFee = double.tryParse(_feeController.text.trim()) ?? 0;
    final lat = double.tryParse(_latController.text.trim()) ?? 0;
    final lng = double.tryParse(_lngController.text.trim()) ?? 0;
    final cnic = _cnicController.text.trim();

    if (name.isEmpty || phone.isEmpty || city.isEmpty || cnic.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all required fields')),
      );
      return;
    }
    if (visitFee <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid visit fee')),
      );
      return;
    }

    ref.read(authProvider.notifier).register(
          name: name,
          phone: phone,
          serviceType: _selectedService,
          city: city,
          visitFee: visitFee,
          lat: lat,
          lng: lng,
          cnic: cnic,
        );
  }

  Future<void> _useCurrentLocation() async {
    setState(() {
      _isFetchingLocation = true;
    });
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw Exception('Location services are disabled.');
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        throw Exception('Location permission was not granted.');
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.best,
        ),
      );
      _updateCoordinates(position.latitude, position.longitude);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isFetchingLocation = false;
        });
      }
    }
  }

  void _updateCoordinates(double lat, double lng) {
    setState(() {
      _latController.text = lat.toStringAsFixed(6);
      _lngController.text = lng.toStringAsFixed(6);
    });
  }

  LatLng get _selectedLatLng {
    final lat = double.tryParse(_latController.text.trim()) ?? 34.0;
    final lng = double.tryParse(_lngController.text.trim()) ?? 71.5;
    return LatLng(lat, lng);
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next is AuthAuthenticated) {
        if (next.user.isVerified) {
          context.go('/dashboard');
        } else {
          context.go('/verification');
        }
      } else if (next is AuthCodeSent) {
        context.push('/verify-otp', extra: next.phone);
      } else if (next is AuthError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(next.message)),
        );
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          // ── Dark header banner ──────────────────────────────────────────
          Container(
            width: double.infinity,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: AppColors.primaryGradient,
              ),
              borderRadius: BorderRadius.only(
                bottomLeft: Radius.circular(36),
                bottomRight: Radius.circular(36),
              ),
            ),
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(28, 32, 28, 44),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Logo pill
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.25),
                        borderRadius: BorderRadius.circular(50),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.handyman_rounded,
                              color: AppColors.primaryLight, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            'Ustaad Connect',
                            style: GoogleFonts.poppins(
                              color: AppColors.primaryLight,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      _showRegister ? 'Create Provider\nAccount' : 'Provider Login',
                      style: GoogleFonts.poppins(
                        color: Colors.white,
                        fontSize: 30,
                        fontWeight: FontWeight.w800,
                        height: 1.15,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      _showRegister
                          ? 'Set up your provider account and start accepting jobs right away.'
                          : 'Sign in directly to your single-provider job console.',
                      style: GoogleFonts.inter(
                        color: AppColors.textOnDarkMuted,
                        fontSize: 14,
                        height: 1.6,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // ── Form area ───────────────────────────────────────────────────
          Expanded(
            child: FadeTransition(
              opacity: _fadeAnim,
              child: SlideTransition(
                position: _slideAnim,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(24, 36, 24, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: _ModeChip(
                              label: 'Login',
                              isSelected: !_showRegister,
                              onTap: () {
                                setState(() {
                                  _showRegister = false;
                                });
                              },
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _ModeChip(
                              label: 'Register',
                              isSelected: _showRegister,
                              onTap: () {
                                setState(() {
                                  _showRegister = true;
                                });
                              },
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      AppCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (_showRegister) ...[
                              _FieldLabel('Full Name'),
                              const SizedBox(height: 8),
                              _AppTextField(
                                controller: _nameController,
                                hintText: 'John Doe',
                              ),
                              const SizedBox(height: 16),
                            ],
                            _FieldLabel('Phone Number'),
                            const SizedBox(height: 8),
                            PhoneInput(
                              controller: _phoneController,
                              hintText: '3001234567',
                            ),
                            if (_showRegister) ...[
                              const SizedBox(height: 16),
                              _FieldLabel('CNIC Number'),
                              const SizedBox(height: 8),
                              _AppTextField(
                                controller: _cnicController,
                                hintText: 'e.g. 35202-1234567-1',
                                keyboardType: TextInputType.phone,
                              ),
                              const SizedBox(height: 16),
                              _FieldLabel('Service Type'),
                              const SizedBox(height: 8),
                              DropdownButtonFormField<String>(
                                initialValue: _selectedService,
                                decoration: _inputDecoration(),
                                items: DummyData.serviceCategories
                                    .map(
                                      (service) => DropdownMenuItem<String>(
                                        value: service,
                                        child: Text(service),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (value) {
                                  if (value != null) {
                                    setState(() {
                                      _selectedService = value;
                                    });
                                  }
                                },
                              ),
                              const SizedBox(height: 16),
                              _FieldLabel('City'),
                              const SizedBox(height: 8),
                              _AppTextField(
                                controller: _cityController,
                                hintText: 'peshawar',
                              ),
                              const SizedBox(height: 16),
                              _FieldLabel('Visit Fee (PKR)'),
                              const SizedBox(height: 8),
                              _AppTextField(
                                controller: _feeController,
                                hintText: '500',
                                keyboardType: TextInputType.number,
                              ),
                              const SizedBox(height: 16),
                              SizedBox(
                                width: double.infinity,
                                child: OutlinedButton.icon(
                                  onPressed:
                                      _isFetchingLocation ? null : _useCurrentLocation,
                                  icon: _isFetchingLocation
                                      ? const SizedBox(
                                          width: 16,
                                          height: 16,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Icon(Icons.my_location_rounded),
                                  label: Text(
                                    _isFetchingLocation
                                        ? 'Fetching location...'
                                        : 'Use Current Location',
                                    style: GoogleFonts.poppins(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: AppColors.darkTeal,
                                    minimumSize: const Size.fromHeight(48),
                                    side: BorderSide(
                                      color: AppColors.darkTeal.withValues(
                                        alpha: 0.16,
                                      ),
                                    ),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(16),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 16),
                              AppLocationMap(
                                center: _selectedLatLng,
                                marker: _selectedLatLng,
                                height: 220,
                                zoom: 14,
                                label: 'Tap map to adjust provider pin',
                                onTap: (point) {
                                  _updateCoordinates(
                                    point.latitude,
                                    point.longitude,
                                  );
                                },
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 36),
                      AppPrimaryButton(
                        text: _showRegister ? 'Create Account' : 'Login',
                        isLoading: authState is AuthLoading,
                        onPressed:
                            _showRegister ? _handleRegister : _handleLogin,
                      ),
                      const SizedBox(height: 20),
                      Center(
                        child: Text(
                          _showRegister
                              ? 'Simple single-provider setup, based on the current live workflow.'
                              : 'Use your provider phone number to enter the job console.',
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(
                            color: AppColors.textSecondary,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

InputDecoration _inputDecoration() {
  return InputDecoration(
    hintStyle: GoogleFonts.inter(color: AppColors.textSecondary),
    filled: true,
    fillColor: Colors.white,
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: BorderSide(color: Colors.black.withValues(alpha: 0.08)),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: BorderSide(color: Colors.black.withValues(alpha: 0.08)),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: const BorderSide(color: AppColors.primary, width: 1.4),
    ),
  );
}

class _FieldLabel extends StatelessWidget {
  final String text;

  const _FieldLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: GoogleFonts.poppins(
        color: AppColors.textPrimary,
        fontSize: 14,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

class _AppTextField extends StatelessWidget {
  final TextEditingController controller;
  final String hintText;
  final TextInputType? keyboardType;

  const _AppTextField({
    required this.controller,
    required this.hintText,
    this.keyboardType,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: _inputDecoration().copyWith(hintText: hintText),
    );
  }
}

class _ModeChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _ModeChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withValues(alpha: 0.12)
              : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected
                ? AppColors.primary.withValues(alpha: 0.4)
                : Colors.black.withValues(alpha: 0.08),
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: GoogleFonts.poppins(
              color: isSelected ? AppColors.primary : AppColors.textSecondary,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}
