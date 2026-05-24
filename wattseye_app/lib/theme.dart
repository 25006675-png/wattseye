import 'package:flutter/material.dart';

class AppTheme {
  static const primary = Color(0xFF3F7BE0);
  static const text = Color(0xFF1A2233);
  static const muted = Color(0xFF6B7280);
  static const surface = Color(0xFFFFFFFF);
  static const background = Color(0xFFF5F7FA);
  static const divider = Color(0xFFEEF0F3);
  static const green = Color(0xFF2F9C5B);
  static const amber = Color(0xFFD4A02A);
  static const red = Color(0xFFCC4444);

  static const wasteBorder = Color(0xFFE07B3F);
  static const wasteTagBg = Color(0xFFFCEEE1);
  static const wasteTagText = Color(0xFF8A4515);
  static const tariffBorder = Color(0xFF3F7BE0);
  static const tariffTagBg = Color(0xFFE3EDFB);
  static const tariffTagText = Color(0xFF1D4A99);
  static const forecastBorder = Color(0xFFA23FE0);
  static const forecastTagBg = Color(0xFFEDE1FB);
  static const forecastTagText = Color(0xFF5A1D99);
  static const contextBorder = Color(0xFF3FA6E0);
  static const contextTagBg = Color(0xFFE1F0FB);
  static const contextTagText = Color(0xFF155A8A);
  static const capitalBorder = Color(0xFF2F9C5B);
  static const capitalTagBg = Color(0xFFDFF0E6);
  static const capitalTagText = Color(0xFF195E34);

  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: background,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        surface: surface,
      ),
      fontFamily: 'Inter',
      textTheme: const TextTheme(
        titleLarge: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          height: 1.2,
          color: text,
        ),
        titleMedium: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w700,
          height: 1.2,
          color: text,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          height: 1.45,
          color: text,
        ),
        bodySmall: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          height: 1.4,
          color: muted,
        ),
        labelSmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          height: 1.3,
          color: muted,
        ),
        labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: background,
        foregroundColor: text,
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        indicatorColor: primary.withValues(alpha: 0.12),
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 11,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
            color: states.contains(WidgetState.selected) ? primary : muted,
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: divider,
        thickness: 1,
        space: 1,
      ),
    );
  }
}
