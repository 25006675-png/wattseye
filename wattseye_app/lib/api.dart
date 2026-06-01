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

  Future<List<Map<String, dynamic>>> getCoachCards({String mode = 'showcase'}) async {
    final response = await _get('/api/coach/cards?mode=$mode');
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

  Future<void> markCoachAction(String archetypeKey, String action) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/coach/cards/$archetypeKey/action'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'action': action}),
    );
    _check(response);
  }

  /// Schedule a WhatsApp reminder for a coach card, [fireInSeconds] from now.
  Future<void> createReminder(
    String archetypeKey,
    int fireInSeconds, {
    String headline = '',
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/reminders'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'archetype_key': archetypeKey,
        'fire_in_seconds': fireInSeconds,
        'headline': headline,
      }),
    );
    _check(response);
  }

  Future<BillInfo> getBill() async {
    final response = await _get('/api/bill');
    return BillInfo.fromJson(_decodeMap(response.body));
  }

  /// Recompute the forecast for a chosen set of lever keys. The server composes
  /// through the tariff engine (handles cliff/EEI band crossings), so the total
  /// is correct for combinations, not a flat per-card sum.
  Future<ForecastSim> simulateForecast(
    List<String> selected, {
    String mode = 'showcase',
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/forecast/simulate'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'mode': mode, 'selected': selected}),
    );
    _check(response);
    return ForecastSim.fromJson(_decodeMap(response.body));
  }

  /// Persist a user label/correction for an appliance signature so future
  /// detections can match it. [kind] is 'device' | 'multiple' | 'unsure'.
  Future<void> labelAppliance({
    required String appliance,
    required String kind,
    String? device,
  }) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/appliance/label'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'appliance': appliance,
        'kind': kind,
        'device': ?device,
      }),
    );
    _check(response);
  }

  Future<List<HistoryDay>> getHistory() async {
    final response = await _get('/api/history');
    final map = _decodeMap(response.body);
    final days = map['days'];
    if (days is! List) return const [];
    return [
      for (final d in days)
        if (d is Map) HistoryDay.fromJson(Map<String, dynamic>.from(d)),
    ];
  }

  Future<AcCutoffResult> triggerAcCutoff() async {
    final response = await _client.post(
      Uri.parse('$baseUrl/api/ac/cutoff'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'reason': 'app_manual'}),
    );
    _check(response);
    return AcCutoffResult.fromJson(_decodeMap(response.body));
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

class BillLineItem {
  const BillLineItem({
    required this.label,
    required this.amountRm,
    required this.unitDetail,
  });

  final String label;
  final double amountRm;
  final String unitDetail;

  factory BillLineItem.fromJson(Map<String, dynamic> json) {
    return BillLineItem(
      label: json['label']?.toString() ?? '',
      amountRm: _number(json['amount_rm']),
      unitDetail: json['unit_detail']?.toString() ?? '',
    );
  }
}

/// One slice of the forecast cost attribution. `kind` is 'measured' (AC clamp,
/// exact), 'estimated' (NILM-disaggregated), or 'unknown' (unattributed residual).
class ApplianceCost {
  const ApplianceCost({
    required this.appliance,
    required this.amountRm,
    required this.kind,
  });

  final String appliance;
  final double amountRm;
  final String kind;

  factory ApplianceCost.fromJson(Map<String, dynamic> json) {
    return ApplianceCost(
      appliance: json['appliance']?.toString() ?? '',
      amountRm: _number(json['amount_rm']),
      kind: json['kind']?.toString() ?? 'estimated',
    );
  }
}

/// Result of a backend forecast composition for a chosen lever set.
class ForecastSim {
  const ForecastSim({
    required this.composedTotalRm,
    required this.savingRm,
    required this.newKwh,
  });

  final double composedTotalRm;
  final double savingRm;
  final double newKwh;

  factory ForecastSim.fromJson(Map<String, dynamic> json) {
    return ForecastSim(
      composedTotalRm: _number(json['composed_total_rm']),
      savingRm: _number(json['saving_rm']),
      newKwh: _number(json['new_kwh']),
    );
  }
}

class BillInfo {
  const BillInfo({
    required this.projectedTotalRm,
    required this.projectedKwh,
    required this.effectiveSenPerKwh,
    required this.touProjectedTotalRm,
    this.baselineTotalRm = 0,
    this.attribution = const [],
    this.highBandThresholdKwh = 1500,
    this.headroomKwh = 0,
    this.inHighBand = false,
    this.lowBandGenSen = 27.03,
    this.highBandGenSen = 37.03,
    this.lines = const [],
  });

  final double projectedTotalRm;
  final double projectedKwh;
  final double effectiveSenPerKwh;
  final double touProjectedTotalRm;
  final double baselineTotalRm;
  final List<ApplianceCost> attribution;
  final double highBandThresholdKwh;
  final double headroomKwh;
  final bool inHighBand;
  final double lowBandGenSen;
  final double highBandGenSen;
  final List<BillLineItem> lines;

  factory BillInfo.fromJson(Map<String, dynamic> json) {
    final rawLines = json['lines'];
    final rawAttribution = json['attribution'];
    return BillInfo(
      projectedTotalRm: _number(json['projected_total_rm']),
      projectedKwh: _number(json['projected_kwh']),
      effectiveSenPerKwh: _number(json['effective_sen_per_kwh']),
      touProjectedTotalRm: _number(json['tou_projected_total_rm']),
      baselineTotalRm: _number(json['baseline_total_rm']),
      attribution: rawAttribution is List
          ? rawAttribution
                .whereType<Map>()
                .map((m) => ApplianceCost.fromJson(Map<String, dynamic>.from(m)))
                .toList()
          : const [],
      highBandThresholdKwh: json['high_band_threshold_kwh'] == null
          ? 1500
          : _number(json['high_band_threshold_kwh']),
      headroomKwh: _number(json['headroom_kwh']),
      inHighBand: json['in_high_band'] == true,
      lowBandGenSen: json['low_band_gen_sen'] == null
          ? 27.03
          : _number(json['low_band_gen_sen']),
      highBandGenSen: json['high_band_gen_sen'] == null
          ? 37.03
          : _number(json['high_band_gen_sen']),
      lines: rawLines is List
          ? rawLines
                .whereType<Map>()
                .map((m) => BillLineItem.fromJson(Map<String, dynamic>.from(m)))
                .toList()
          : const [],
    );
  }
}

class HistoryDay {
  const HistoryDay({required this.date, required this.costRm});

  final String date;
  final double costRm;

  factory HistoryDay.fromJson(Map<String, dynamic> json) {
    return HistoryDay(
      date: json['date']?.toString() ?? '',
      costRm: _number(json['cost_rm']),
    );
  }
}

class AcCutoffResult {
  const AcCutoffResult({required this.sent, required this.reason});

  final bool sent;
  final String reason;

  factory AcCutoffResult.fromJson(Map<String, dynamic> json) {
    return AcCutoffResult(
      sent: json['sent'] == true,
      reason: json['reason']?.toString() ?? '',
    );
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
    this.kind = 'estimated',
    this.monthCostRm = 0,
  });

  final String name;
  final double watts;
  final double todayKwh;
  final double todayRm;
  final String kind; // 'measured' | 'estimated' | 'unknown'
  final double monthCostRm;

  factory ActiveAppliance.fromJson(Map<String, dynamic> json) {
    return ActiveAppliance(
      name: json['name']?.toString() ?? 'unknown',
      watts: _number(json['watts']),
      todayKwh: _number(json['today_kwh']),
      todayRm: _number(json['today_rm']),
      kind: json['kind']?.toString() ?? 'estimated',
      monthCostRm: _number(json['month_cost_rm']),
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
