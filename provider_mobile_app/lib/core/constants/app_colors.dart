import 'package:flutter/material.dart';

class AppColors {
  // Primary Lime Green (accent / CTA)
  static const Color primary = Color(0xFF8BC34A);          // Lime green
  static const Color primaryBright = Color(0xFFB5E551);    // Neon lime highlight
  static const Color primaryLight = Color(0xFFCBED8B);     // Soft lime tint

  // Dark Teal (backgrounds / surfaces)
  static const Color darkTeal = Color(0xFF14342B);         // Deep forest teal
  static const Color darkTealMid = Color(0xFF1E4D3A);      // Mid-dark teal
  static const Color darkTealSurface = Color(0xFF25573F);  // Card/container dark

  // Backgrounds
  static const Color background = Color(0xFFF7FAF8);       // Light off-white
  static const Color surface = Color(0xFFFFFFFF);          // Pure white cards
  static const Color surfaceDark = Color(0xFF1A3D2B);      // Dark card surface

  // Text
  static const Color textPrimary = Color(0xFF111D13);      // Almost black
  static const Color textSecondary = Color(0xFF637066);    // Medium grey-green
  static const Color textOnDark = Color(0xFFFFFFFF);       // White on dark bg
  static const Color textOnDarkMuted = Color(0xFFB0C4B8);  // Muted on dark

  // Status
  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFF9800);
  static const Color error = Color(0xFFE53935);
  static const Color info = Color(0xFF1976D2);

  // Gradient stops
  static const List<Color> primaryGradient = [
    Color(0xFF14342B),
    Color(0xFF1E4D3A),
  ];

  static const List<Color> accentGradient = [
    Color(0xFF8BC34A),
    Color(0xFFB5E551),
  ];
}
