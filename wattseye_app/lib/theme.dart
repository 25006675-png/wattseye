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

  // Spacing scale (use instead of ad-hoc magic numbers).
  static const double sp1 = 4;
  static const double sp2 = 8;
  static const double sp3 = 12;
  static const double sp4 = 16;
  static const double sp6 = 24;
  static const double radius = 14;

  // Single corner radius for all pill/tag chips (was a mix of 4/6/20).
  static const double chipRadius = 6;

  // TNB myTNB-inspired palette — scoped to the Bill page so it reads like a
  // real TNB statement without re-skinning the whole app.
  static const tnbTeal = Color(0xFF00A19C);
  static const tnbTealDark = Color(0xFF007E7A);
  static const tnbTealBg = Color(0xFFE6F5F4);
  static const tnbOrange = Color(0xFFF47B20);
  static const tnbOrangeBg = Color(0xFFFDEEE2);

  // TNB printed-statement palette — the paper "Bil Elektrik Anda" look:
  // red logo lockup, ink text on white, and the iconic yellow amount-due box.
  static const tnbRed = Color(0xFFE2231A);
  static const tnbInk = Color(0xFF20262E);
  // TNB corporate blue band (light -> dark) for the statement masthead.
  static const tnbBlueLight = Color(0xFF5E9BEC);
  static const tnbBlueDark = Color(0xFF254A8E);
  static const billYellowBg = Color(0xFFFFF6DA); // pale callout fill
  static const billYellowBar = Color(0xFFF4C430); // callout accent
  static const billYellowBorder = Color(0xFFEAD089);
  static const statementBorder = Color(0xFFE3E6EB);

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
        // Hero metric numbers (today's cost, AC watts, bill total). Semibold
        // with tight tracking + tabular figures — the refined look modern
        // consumer apps use, not chunky extra-bold. Use these instead of
        // hand-rolling copyWith(fontSize: ...) per page.
        displayLarge: TextStyle(
          fontSize: 36,
          fontWeight: FontWeight.w600,
          height: 1.05,
          letterSpacing: -0.8,
          color: text,
          fontFeatures: [FontFeature.tabularFigures()],
        ),
        displayMedium: TextStyle(
          fontSize: 30,
          fontWeight: FontWeight.w600,
          height: 1.05,
          letterSpacing: -0.6,
          color: text,
          fontFeatures: [FontFeature.tabularFigures()],
        ),
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
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
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
