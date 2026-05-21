import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../../../core/constants/app_colors.dart';

class RadarScanner extends StatefulWidget {
  const RadarScanner({super.key});

  @override
  State<RadarScanner> createState() => _RadarScannerState();
}

class _RadarScannerState extends State<RadarScanner>
    with TickerProviderStateMixin {
  late AnimationController _sweepController;
  late AnimationController _rippleController;
  late AnimationController _pinController;

  @override
  void initState() {
    super.initState();

    _sweepController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    _rippleController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    _pinController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _sweepController.dispose();
    _rippleController.dispose();
    _pinController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 320,
      height: 320,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background grid/circles
          Container(
            width: 256,
            height: 256,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withValues(alpha: 0.05),
              border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.1), width: 1),
            ),
          ),
          Container(
            width: 128,
            height: 128,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.05), width: 1),
            ),
          ),

          // Ripples
          ...List.generate(4, (index) {
            return AnimatedBuilder(
              animation: _rippleController,
              builder: (context, child) {
                // Offset each ripple by 1/4th of the animation
                double progress = (_rippleController.value + (index * 0.25)) % 1.0;
                // Ease out cubic
                double scale = 0.5 + (2.0 * (1 - math.pow(1 - progress, 3)));
                double opacity = 1.0 - progress;

                return Transform.scale(
                  scale: scale,
                  child: Opacity(
                    opacity: opacity,
                    child: Container(
                      width: 192,
                      height: 192,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: AppColors.primary.withValues(alpha: 0.4),
                          width: 1,
                        ),
                      ),
                    ),
                  ),
                );
              },
            );
          }),

          // Scanner Sweep
          AnimatedBuilder(
            animation: _sweepController,
            builder: (context, child) {
              return Transform.rotate(
                angle: _sweepController.value * 2 * math.pi,
                child: Container(
                  width: 256,
                  height: 256,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: SweepGradient(
                      colors: [
                        Colors.transparent,
                        AppColors.primaryLight,
                      ],
                      stops: [0.75, 1.0],
                    ),
                  ),
                ),
              );
            },
          ),

          // Floating Pin
          AnimatedBuilder(
            animation: _pinController,
            builder: (context, child) {
              // Smooth float up and down (-8px to 0)
              final offsetY = -8.0 * _pinController.value;
              return Transform.translate(
                offset: Offset(0, offsetY),
                child: Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withValues(alpha: 0.3),
                        blurRadius: 16,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.location_on_rounded,
                    color: Colors.white,
                    size: 32,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
