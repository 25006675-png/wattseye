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

  Future<IntegrationStatus> getIntegrationStatus() async {
    final response = await _get('/api/integrations/status');
    return IntegrationStatus.fromJson(_decodeMap(response.body));
  }

  Future<PhoneConnectionStatus> getPhones() async {
    final response = await _get('/api/phones');
    return PhoneConnectionStatus.fromJson(_decodeMap(response.body));
  }

  Future<PhoneConnectionStatus> pairPhone({
    required String code,
    required String phoneName,
    String platform = 'mobile',
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/phones/pair'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'code': code,
        'phone_name': phoneName,
        'platform': platform,
      }),
    );
    _check(response);
    return PhoneConnectionStatus.fromJson(_decodeMap(response.body));
  }

  Future<void> markCoachAction(String archetypeKey, String action) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/coach/cards/$archetypeKey/action'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'action': action}),
    );
    _check(response);
  }

  Future<WhatsAppSendResult> sendWhatsAppAlert(String archetypeKey) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/whatsapp/send'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'archetype_key': archetypeKey}),
    );
    _check(response);
    return WhatsAppSendResult.fromJson(_decodeMap(response.body));
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

class WhatsAppSendResult {
  const WhatsAppSendResult({
    required this.sent,
    required this.reason,
    required this.body,
    required this.setupNeeded,
  });

  final bool sent;
  final String reason;
  final String body;
  final List<String> setupNeeded;

  factory WhatsAppSendResult.fromJson(Map<String, dynamic> json) {
    return WhatsAppSendResult(
      sent: json['sent'] == true,
      reason: json['reason']?.toString() ?? '',
      body: json['body']?.toString() ?? '',
      setupNeeded: [
        for (final item in (json['setup_needed'] as List? ?? const []))
          item.toString(),
      ],
    );
  }
}

class IntegrationStatus {
  const IntegrationStatus({
    required this.pdfAvailable,
    required this.weatherAvailable,
    required this.nilmModelCount,
    required this.torchAvailable,
    required this.joblibModelCount,
  });

  final bool pdfAvailable;
  final bool weatherAvailable;
  final int nilmModelCount;
  final bool torchAvailable;
  final int joblibModelCount;

  factory IntegrationStatus.fromJson(Map<String, dynamic> json) {
    final pdf = Map<String, dynamic>.from(json['pdf'] as Map? ?? {});
    final weather = Map<String, dynamic>.from(json['weather'] as Map? ?? {});
    final ml = Map<String, dynamic>.from(json['ml'] as Map? ?? {});
    return IntegrationStatus(
      pdfAvailable: pdf['available'] == true,
      weatherAvailable: weather['available'] == true,
      nilmModelCount: _int(ml['nilm_model_count']),
      torchAvailable: ml['torch_available'] == true,
      joblibModelCount: _int(ml['joblib_model_count']),
    );
  }
}

class PhoneConnectionStatus {
  const PhoneConnectionStatus({
    required this.pairingCode,
    required this.pairingCodeHint,
    required this.phones,
  });

  final String pairingCode;
  final String pairingCodeHint;
  final List<PairedPhone> phones;

  factory PhoneConnectionStatus.fromJson(Map<String, dynamic> json) {
    return PhoneConnectionStatus(
      pairingCode: json['pairing_code']?.toString() ?? '',
      pairingCodeHint: json['pairing_code_hint']?.toString() ?? '',
      phones: [
        for (final item in (json['phones'] as List? ?? const []))
          if (item is Map) PairedPhone.fromJson(Map<String, dynamic>.from(item)),
      ],
    );
  }
}

class PairedPhone {
  const PairedPhone({
    required this.phoneId,
    required this.phoneName,
    required this.platform,
    required this.pairedAt,
    required this.lastSeen,
  });

  final String phoneId;
  final String phoneName;
  final String platform;
  final DateTime? pairedAt;
  final DateTime? lastSeen;

  factory PairedPhone.fromJson(Map<String, dynamic> json) {
    return PairedPhone(
      phoneId: json['phone_id']?.toString() ?? '',
      phoneName: json['phone_name']?.toString() ?? 'Phone',
      platform: json['platform']?.toString() ?? 'mobile',
      pairedAt: DateTime.tryParse(json['paired_at']?.toString() ?? ''),
      lastSeen: DateTime.tryParse(json['last_seen']?.toString() ?? ''),
    );
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

int _int(Object? value) {
  if (value is int) return value;
  if (value is num) return value.round();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}
