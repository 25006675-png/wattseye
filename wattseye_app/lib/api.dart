import 'dart:convert';

import 'package:http/http.dart' as http;

const defaultApiBaseUrl = String.fromEnvironment(
  'WATTSEYE_API_BASE',
  defaultValue: 'http://localhost:8080',
);

class WattsEyeApi {
  WattsEyeApi({
    String baseUrl = defaultApiBaseUrl,
    http.Client? client,
  }) : baseUrl = baseUrl.replaceFirst(RegExp(r'/$'), ''),
       _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<DashboardSnapshot> getDashboard() async {
    final response = await _get('/api/dashboard');
    return DashboardSnapshot.fromJson(_decodeMap(response.body));
  }

  Future<List<Map<String, dynamic>>> getCoachCards() async {
    final response = await _get('/api/coach/cards');
    final data = jsonDecode(response.body);
    if (data is! List) {
      throw const FormatException('Expected a list of coach cards');
    }
    return data
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<void> markCoachAction(String archetypeKey, String action) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/coach/cards/$archetypeKey/action'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'action': action}),
    );
    _check(response);
  }

  Future<http.Response> _get(String path) async {
    final response = await _client.get(Uri.parse('$baseUrl$path'));
    _check(response);
    return response;
  }

  void _check(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw http.ClientException(
        'Backend returned ${response.statusCode}: ${response.body}',
        response.request?.url,
      );
    }
  }

  Map<String, dynamic> _decodeMap(String body) {
    final data = jsonDecode(body);
    if (data is! Map) {
      throw const FormatException('Expected a JSON object');
    }
    return Map<String, dynamic>.from(data);
  }
}

class DashboardSnapshot {
  const DashboardSnapshot({
    required this.timestamp,
    required this.livePowerW,
    required this.todayCostRm,
    required this.projectedBillRm,
    required this.occupancyState,
    required this.activeAppliances,
  });

  final DateTime? timestamp;
  final double livePowerW;
  final double todayCostRm;
  final double projectedBillRm;
  final String occupancyState;
  final List<ActiveAppliance> activeAppliances;

  factory DashboardSnapshot.fromJson(Map<String, dynamic> json) {
    return DashboardSnapshot(
      timestamp: DateTime.tryParse(json['timestamp']?.toString() ?? ''),
      livePowerW: _number(json['live_power_w']),
      todayCostRm: _number(json['today_cost_rm']),
      projectedBillRm: _number(json['projected_bill_rm']),
      occupancyState: json['occupancy_state']?.toString() ?? 'unknown',
      activeAppliances: [
        for (final item in (json['active_appliances'] as List? ?? const []))
          if (item is Map)
            ActiveAppliance.fromJson(Map<String, dynamic>.from(item)),
      ],
    );
  }
}

class ActiveAppliance {
  const ActiveAppliance({
    required this.name,
    required this.watts,
    required this.todayKwh,
    required this.todayRm,
  });

  final String name;
  final double watts;
  final double todayKwh;
  final double todayRm;

  factory ActiveAppliance.fromJson(Map<String, dynamic> json) {
    return ActiveAppliance(
      name: json['name']?.toString() ?? 'unknown',
      watts: _number(json['watts']),
      todayKwh: _number(json['today_kwh']),
      todayRm: _number(json['today_rm']),
    );
  }
}

double _number(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}
