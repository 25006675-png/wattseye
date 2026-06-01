import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'theme.dart';

void main() {
  runApp(const WattsEyeApp());
}

class WattsEyeApp extends StatelessWidget {
  const WattsEyeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'WattsEye',
      theme: AppTheme.light(),
      home: const HomeShell(),
    );
  }
}

enum InsightAction { none, done, remind, dismissed }

class CoachCardData {
  const CoachCardData({
    required this.id,
    required this.keyName,
    required this.family,
    required this.severity,
    required this.headline,
    required this.impact,
    required this.action,
    required this.saving,
    required this.effort,
    required this.confidence,
    required this.rmMonthly,
    required this.why,
    required this.math,
    this.dataSource = 'showcase',
    this.pushEligible = false,
  });

  final int id;
  final String keyName;
  final String family;
  final String severity;
  final String headline;
  final String impact;
  final String action;
  final String saving;
  final String effort;
  final String confidence;
  final double rmMonthly;
  final List<String> why;
  final List<String> math;
  final String dataSource; // 'live' | 'replay' | 'showcase'
  final bool pushEligible; // earns a WhatsApp push (subset of 4 archetypes)
}

class CoachCardState {
  const CoachCardState(this.data, {this.action = InsightAction.none});

  final CoachCardData data;
  final InsightAction action;

  CoachCardState copyWith({InsightAction? action}) {
    return CoachCardState(data, action: action ?? this.action);
  }
}

const _coachCards = [
  CoachCardData(
    id: 1,
    keyName: 'left_on_empty',
    pushEligible: true,
    family: 'waste',
    severity: 'high',
    headline: 'AC running in empty room',
    impact:
        'AC ran 71 min after the room emptied at 14:19. At your current pattern, this costs about RM 10/month.',
    action: 'Enable auto-off after 20 min empty.',
    saving: 'RM 10/month',
    effort: 'Low effort',
    confidence: 'High confidence',
    rmMonthly: 9.85,
    why: [
      'Occupancy: Room empty since 14:19 (71 min).',
      'NILM: AC drawing 1,200W.',
      'K-Means phase: work (14:00-17:00).',
      'Routine baseline: AC normally OFF during work phase (observed 14/14 weekdays).',
    ],
    math: [
      '1,200W * 71 min / 60 = 1.42 kWh wasted this event',
      'Event cost via TNB RP4 marginal pricing: RM 0.57',
      'Weekly frequency 4 * 4.345 weeks/month = RM 9.85/month',
    ],
  ),
  CoachCardData(
    id: 2,
    keyName: 'phantom_standby',
    family: 'waste',
    severity: 'medium',
    headline: 'Phantom standby load detected',
    impact:
        'Your home draws 48W continuously overnight from devices on standby, about RM 6/month.',
    action:
        'Unplug TV, router, and charger clusters or use a switched power strip overnight.',
    saving: 'RM 6/month',
    effort: 'Low effort',
    confidence: 'High confidence',
    rmMonthly: 6.20,
    why: [
      'NILM minimum-window: Overnight base load: 48W when household asleep.',
      'Routine baseline: Sleep phase identified by K-Means; no high-draw appliances expected.',
    ],
    math: [
      '48W * 24h * 30 days / 1000 = 34.6 kWh/month',
      'At TNB RP4 marginal rate = RM 6.20/month',
    ],
  ),
  CoachCardData(
    id: 5,
    keyName: 'rp4_tier_cliff',
    pushEligible: true,
    family: 'tariff',
    severity: 'medium',
    headline: 'Approaching 1,500 kWh tariff cliff',
    impact:
        'Projected 1,480 kWh, within 20 kWh of the high-band cliff. Crossing raises generation rate from 27.03 to 37.03 sen/kWh on every unit above.',
    action:
        'Trim 25 kWh by month-end, about 1.5 hours less AC/day, to stay in the lower tier.',
    saving: 'RM 3/month',
    effort: 'Low effort',
    confidence: 'High confidence',
    rmMonthly: 3.00,
    why: [
      'Cost engine: Projected month-end: 1,480 kWh.',
      'TNB RP4 schedule: Crossing 1,500 kWh raises generation rate from 27.03 to 37.03 sen/kWh on every unit.',
    ],
    math: [
      'Generation rate jumps from 27.03 sen/kWh to 37.03 sen/kWh at 1,500 kWh',
      'Estimated savings if you stay below: RM 3.00',
    ],
  ),
  CoachCardData(
    id: 4,
    keyName: 'tou_switch',
    family: 'tariff',
    severity: 'medium',
    headline: 'You may save by switching to TNB ToU tariff',
    impact:
        '68% of your last 30 days fell in off-peak hours. Switching to ToU could save about RM 12/month.',
    action: 'Apply for ToU tariff via myTNB app as a one-time opt-in.',
    saving: 'RM 12/month',
    effort: 'Low effort',
    confidence: 'High confidence',
    rmMonthly: 12.40,
    why: [
      'Routine engine: 68% of your last 30 days of usage fell in off-peak hours.',
      'TNB tariff calc: ToU off-peak rate is 17.55 sen/kWh lower than peak.',
    ],
    math: [
      'Standard tariff projected bill: RM 612/month',
      'ToU tariff projected bill:      RM 600/month',
      'Difference:                     RM 12/month',
    ],
  ),
  CoachCardData(
    id: 7,
    keyName: 'bill_trending_high',
    pushEligible: true,
    family: 'forecast',
    severity: 'high',
    headline: 'Bill trending high this month',
    impact:
        'On track for RM 612 this month, +25% vs your usual RM 489. Main driver: AC usage.',
    action:
        'Raise AC setpoint by 1-2 C and reduce kettle pre-heating to save about RM 19 this month.',
    saving: 'RM 19/month',
    effort: 'Medium effort',
    confidence: 'High confidence',
    rmMonthly: 18.80,
    why: [
      'Cost engine: Projection 1,480 kWh (+25% vs 3-month average of 1,180 kWh).',
      'NILM attribution: Main driver: AC usage.',
    ],
    math: [
      'Projected: 1,480 kWh = RM 612 (TNB RP4)',
      'Baseline 3-mo avg: 1,180 kWh = RM 489',
      'Overage: RM 19',
    ],
  ),
  CoachCardData(
    id: 12,
    keyName: 'inefficient_upgrade',
    family: 'capital',
    severity: 'low',
    headline: 'Fridge runs inefficiently, upgrade pays back',
    impact:
        'Your fridge draws 180W continuous. 5-star class average is 90W. A more efficient model saves about RM 230/year.',
    action:
        'Compare 5-star models on the ST efficiency registry; estimated payback is 7.8 years on a RM 1,800 replacement.',
    saving: 'RM 19/month',
    effort: 'High effort',
    confidence: 'High confidence',
    rmMonthly: 19.00,
    why: [
      'NILM steady-state: Fridge draws 180W continuous at idle.',
      'ST efficiency registry: 5-star class average for same size: 90W.',
    ],
    math: [
      'Delta 90W * 24h * 30 days = 64.8 kWh/month extra',
      '* TNB RP4 marginal rate = RM 19/month',
      '* 12 months = RM 230/year',
      'Payback: RM 1,800 / RM 230/year = 7.8 years',
    ],
  ),
  CoachCardData(
    id: 3,
    keyName: 'simultaneous_peak_load',
    family: 'waste',
    severity: 'medium',
    headline: 'Heavy simultaneous use in peak window',
    impact:
        'Kettle, microwave, and AC ran together yesterday at 19:34 with 3,200W combined. Staggering could save about RM 4/month.',
    action:
        'Delay non-urgent loads like kettle and microwave to off-peak after 22:00 weekdays.',
    saving: 'RM 4/month',
    effort: 'Low effort',
    confidence: 'Medium confidence',
    rmMonthly: 4.20,
    why: [
      'NILM: 3 appliances active simultaneously: kettle, microwave, AC (3,200W total).',
      'ToU schedule: Current event is in TNB peak window (14:00-22:00 weekdays).',
    ],
    math: [
      'Estimated 30% of combined load shifted off-peak',
      'Saving = shifted kWh * (peak rate - off-peak rate) = RM 4.20/month',
    ],
  ),
  CoachCardData(
    id: 6,
    keyName: 'peak_window_shift',
    family: 'tariff',
    severity: 'medium',
    headline: 'Shift schedulable loads to off-peak',
    impact:
        'Dishwasher and washer ran 4 times in TNB peak window over the last 14 days. Shifting to after 22:00 saves about RM 5/month.',
    action: 'Set a delay-start timer on dishwasher for after 22:00 weekdays.',
    saving: 'RM 5/month',
    effort: 'Low effort',
    confidence: 'High confidence',
    rmMonthly: 5.30,
    why: [
      'NILM: 4 schedulable runs in peak window over last 14 days.',
      'ToU schedule: Shifting these to after 22:00 would charge at off-peak rate.',
    ],
    math: [
      'Peak kWh over 14 days * 4.345 / 2 = monthly shiftable kWh',
      '* (peak rate - off-peak rate) = RM 5.30/month',
    ],
  ),
  CoachCardData(
    id: 8,
    keyName: 'comparative_regression',
    family: 'forecast',
    severity: 'medium',
    headline: 'AC using more energy this week',
    impact:
        'AC used 38% more this week vs the same week last month. At this rate, monthly cost is up about RM 11.',
    action:
        'Check AC settings, try +1 C setpoint, and look for a window or door left open.',
    saving: 'RM 11/month',
    effort: 'Medium effort',
    confidence: 'High confidence',
    rmMonthly: 11.00,
    why: [
      'NILM: AC used 28.4 kWh this week vs 20.5 kWh same week last month.',
      'Routine engine: External conditions appear similar; likely usage pattern change.',
    ],
    math: [
      'This week: 28.4 kWh',
      'Same week last month: 20.5 kWh',
      'Delta * 4.345 weeks = RM 11/month at TNB RP4 marginal rate',
    ],
  ),
  CoachCardData(
    id: 9,
    keyName: 'routine_shift',
    family: 'forecast',
    severity: 'low',
    headline: 'Your daily routine has shifted',
    impact:
        'K-Means detects your evening phase has moved 75 min later over the past 3 weeks. Old AC schedule may waste about RM 5/month.',
    action: 'Adjust AC scheduler by about 75 min later.',
    saving: 'RM 5/month',
    effort: 'Low effort',
    confidence: 'Medium confidence',
    rmMonthly: 4.80,
    why: [
      'K-Means clustering: evening phase boundary has drifted 75 min later over the past 3 weeks.',
      'Routine engine: Scheduled appliances may still follow old timing.',
    ],
    math: [
      'Estimated 30 min of misaligned AC * 30 days = about 0.9 kWh/day * 30',
      'At TNB RP4 marginal rate = RM 4.80/month',
    ],
  ),
  CoachCardData(
    id: 10,
    keyName: 'weather_correlated_ac',
    family: 'context',
    severity: 'low',
    headline: 'Hot week ahead, pre-cool to save',
    impact:
        '3 hot days above 33 C are forecast in the next 7 days from Open-Meteo. Your AC usage rises about 45% on hot days.',
    action: 'Pre-cool 30 min before peak window on forecast hot days.',
    saving: 'RM 2/week',
    effort: 'Low effort',
    confidence: 'Medium confidence',
    rmMonthly: 2.10,
    why: [
      'Open-Meteo forecast: 3 days above 33 C in next 7 days for Kuala Lumpur.',
      'Routine engine: Your AC usage rises about 45% on hot days.',
    ],
    math: [
      'Estimated 1 kWh/hot-day shifted from peak to off-peak',
      '* 3 hot days * (peak - off-peak rate) = RM 2.10',
    ],
  ),
  CoachCardData(
    id: 11,
    keyName: 'anomaly_with_action',
    pushEligible: true,
    family: 'context',
    severity: 'medium',
    headline: 'Unusual water heater activity at 02:14',
    impact:
        'Water heater ran at 02:14, outside your normal pattern. If this is unintended and continues, about RM 23/month is wasted.',
    action: 'Check water heater timer settings. Confirm or dismiss this card.',
    saving: 'RM 23/month',
    effort: 'Low effort',
    confidence: 'Medium confidence',
    rmMonthly: 23.00,
    why: [
      'Isolation Forest: Event scored -0.42, outside learned baseline for this appliance.',
      'Routine engine: Water heater normally inactive at 02:00.',
    ],
    math: ['Event: 2,400W * 35 min', 'If repeats 4 times/month = RM 23/month'],
  ),
];

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _api = WattsEyeApi();
  int _selectedIndex = 0;
  bool _touPreview = false;
  // Global mode: Demo = showcase coach catalog + synthetic dashboard; Live =
  // real coach cards + real sensor. One toggle in the AppBar drives both.
  bool _demoMode = true;
  late List<CoachCardState> _cards;
  DashboardSnapshot? _dashboard;
  IntegrationStatus? _integrations;
  BillInfo? _bill;
  List<HistoryDay> _history = const [];
  bool _backendOnline = false;

  String get _coachMode => _demoMode ? 'showcase' : 'live';

  @override
  void initState() {
    super.initState();
    _cards = _coachCards.map((card) => CoachCardState(card)).toList();
    _refreshBackendData();
  }

  Future<void> _refreshBackendData() async {
    try {
      final results = await Future.wait<Object>([
        _api.getDashboard(),
        _api.getCoachCards(mode: _coachMode),
        _api.getIntegrationStatus(),
        _api.getBill(),
        _api.getHistory(),
      ]);
      final dashboard = results[0] as DashboardSnapshot;
      final coachCards = results[1] as List<Map<String, dynamic>>;
      final integrations = results[2] as IntegrationStatus;
      final bill = results[3] as BillInfo;
      final history = results[4] as List<HistoryDay>;
      if (!mounted) return;
      setState(() {
        _dashboard = dashboard;
        _cards = coachCards.map(_coachCardFromApi).toList();
        _integrations = integrations;
        _bill = bill;
        _history = history;
        _backendOnline = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _backendOnline = false);
    }
  }

  Future<void> _setDemoMode(bool demo) async {
    if (demo == _demoMode) return;
    setState(() => _demoMode = demo);
    try {
      final cards = await _api.getCoachCards(mode: _coachMode);
      if (!mounted) return;
      setState(() => _cards = cards.map(_coachCardFromApi).toList());
    } catch (_) {
      // Offline: keep showing the current card set (showcase fallback).
    }
  }

  Future<void> _turnOffAc() async {
    if (!_backendOnline) {
      _snack(context, 'Start the backend to send the AC cutoff');
      return;
    }
    try {
      final result = await _api.triggerAcCutoff();
      if (!mounted) return;
      _snack(
        context,
        result.sent
            ? 'AC off command published to the Pi'
            : 'Cutoff not sent: ${result.reason}',
      );
    } catch (_) {
      if (mounted) _snack(context, 'Cutoff request failed');
    }
  }

  Future<void> _markAction(String keyName, InsightAction action) async {
    setState(() {
      _cards = [
        for (final card in _cards)
          if (card.data.keyName == keyName)
            card.copyWith(action: action)
          else
            card,
      ];
    });
    if (_backendOnline) {
      try {
        await _api.markCoachAction(keyName, action.apiValue);
      } catch (_) {
        if (mounted) _snack(context, 'Saved locally - backend did not confirm');
      }
    }
  }

  Future<void> _sendWhatsAppAlert(String keyName) async {
    if (!_backendOnline) {
      _snack(context, 'Start the backend before sending WhatsApp alerts');
      return;
    }
    try {
      final result = await _api.sendWhatsAppAlert(keyName);
      if (!mounted) return;
      if (result.sent) {
        _snack(context, 'WhatsApp alert sent');
      } else if (result.setupNeeded.isNotEmpty) {
        _snack(context, 'Add Twilio env vars, then restart backend');
      } else {
        _snack(
          context,
          result.reason.isEmpty ? 'WhatsApp not sent' : result.reason,
        );
      }
    } catch (_) {
      if (mounted) _snack(context, 'WhatsApp send failed');
    }
  }

  void _openCoachCard(String keyName) {
    final card = _cards.firstWhere((item) => item.data.keyName == keyName);
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CardDetailScreen(
          card: card,
          onAction: (action) async {
            await _markAction(keyName, action);
            if (!mounted) return;
            Navigator.of(context).pop();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    const titles = ['Dashboard', 'Coach', 'Bill', 'History', 'Profile'];
    final pages = [
      DashboardPage(
        dashboard: _dashboard,
        backendOnline: _backendOnline,
        demoMode: _demoMode,
        onRefresh: _refreshBackendData,
        onTurnOff: _turnOffAc,
        onOpenCoach: _openCoachCard,
      ),
      CoachPage(
        cards: _cards,
        demoMode: _demoMode,
        onRefresh: _refreshBackendData,
        onCardTap: _openCoachCard,
        onAction: _markAction,
        onSendWhatsApp: _sendWhatsAppAlert,
      ),
      BillPage(
        touPreview: _touPreview,
        bill: _bill,
        onTogglePreview: () => setState(() => _touPreview = !_touPreview),
        onOpenCoach: _openCoachCard,
      ),
      HistoryPage(history: _history),
      ProfilePage(integrations: _integrations, backendOnline: _backendOnline),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(titles[_selectedIndex]),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: ModeToggle(demo: _demoMode, onChanged: _setDemoMode),
            ),
          ),
        ],
      ),
      body: SafeArea(top: false, child: pages[_selectedIndex]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        onDestinationSelected: (index) =>
            setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.psychology_alt_outlined),
            selectedIcon: Icon(Icons.psychology_alt),
            label: 'Coach',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long),
            label: 'Bill',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart_outlined),
            selectedIcon: Icon(Icons.bar_chart),
            label: 'History',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}

class _DashAppliance {
  _DashAppliance({
    required this.name,
    required this.svg,
    required this.source,
    required this.accent,
    required this.baseWatts,
    required this.costMonth,
    required this.kind,
    this.apiName,
    this.coachKey,
    this.coachHint,
    this.detectedMinsAgo,
    this.drawShape,
    this.recurrence,
  }) : watts = baseWatts;

  final String name;
  final String svg;
  final String source;
  final Color accent;
  final double baseWatts;
  final ApplianceKind kind;
  final String? apiName;
  // Coach deep-link (only set when a real card is about this appliance).
  final String? coachKey;
  final String? coachHint;
  // Unknown-load detection hints.
  final int? detectedMinsAgo;
  final String? drawShape;
  final String? recurrence;
  double watts;
  double costMonth;
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({
    super.key,
    required this.dashboard,
    required this.backendOnline,
    required this.demoMode,
    required this.onRefresh,
    required this.onTurnOff,
    required this.onOpenCoach,
  });

  final DashboardSnapshot? dashboard;
  final bool backendOnline;
  final bool demoMode;
  final Future<void> Function() onRefresh;
  final Future<void> Function() onTurnOff;
  final ValueChanged<String> onOpenCoach;

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  static const _rate = 0.40;
  static const _tick = Duration(milliseconds: 250);
  static const _dtH = 250 / 3600000;
  final _rng = Random();
  late List<_DashAppliance> _appliances;
  double _todayCost = 21.50;
  bool _bannerDismissed = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _appliances = _seed();
    _timer = Timer.periodic(_tick, (_) => _onTick());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  List<_DashAppliance> _seed() => [
    _DashAppliance(
      name: 'Air Conditioner',
      svg: 'assets/appliances/air-conditioning.svg',
      source: 'Measured - Dedicated CT clamp',
      accent: AppTheme.red,
      baseWatts: 900,
      costMonth: 281.40,
      kind: ApplianceKind.measured,
      apiName: 'ac',
      coachKey: 'left_on_empty',
      coachHint: 'Running in an empty room - wasting energy now.',
    ),
    _DashAppliance(
      name: 'Fridge',
      svg: 'assets/appliances/fridge.svg',
      source: 'Estimated - NILM',
      accent: AppTheme.amber,
      baseWatts: 118,
      costMonth: 92.10,
      kind: ApplianceKind.estimated,
      apiName: 'fridge',
      coachKey: 'inefficient_upgrade',
      coachHint: 'Drawing more than a 5-star model - a swap pays back.',
    ),
    _DashAppliance(
      name: 'Unknown load 1',
      svg: 'assets/appliances/unknown.svg',
      source: 'Signature library',
      accent: AppTheme.amber,
      baseWatts: 300,
      costMonth: 98.30,
      kind: ApplianceKind.unknown,
      detectedMinsAgo: 8,
      drawShape: 'steady draw',
      recurrence: 'Seen 4 evenings this week, around 7pm',
    ),
    _DashAppliance(
      name: 'Washing Machine',
      svg: 'assets/appliances/wash-machine.svg',
      source: 'Estimated - NILM',
      accent: AppTheme.green,
      baseWatts: 0,
      costMonth: 38.00,
      kind: ApplianceKind.estimated,
      apiName: 'washing_machine',
    ),
    _DashAppliance(
      name: 'Kettle',
      svg: 'assets/appliances/kettle.svg',
      source: 'Estimated - NILM',
      accent: AppTheme.green,
      baseWatts: 0,
      costMonth: 21.20,
      kind: ApplianceKind.estimated,
      apiName: 'kettle',
    ),
    _DashAppliance(
      name: 'Iron',
      svg: 'assets/appliances/iron.svg',
      source: 'Estimated - NILM',
      accent: AppTheme.green,
      baseWatts: 0,
      costMonth: 12.40,
      kind: ApplianceKind.estimated,
      apiName: 'iron',
    ),
    _DashAppliance(
      name: 'Hair Dryer',
      svg: 'assets/appliances/hair-dryer.svg',
      source: 'Estimated - NILM',
      accent: AppTheme.green,
      baseWatts: 0,
      costMonth: 8.10,
      kind: ApplianceKind.estimated,
      apiName: 'hair_dryer',
    ),
    _DashAppliance(
      name: 'Unknown load 2',
      svg: 'assets/appliances/unknown.svg',
      source: 'Signature library',
      accent: AppTheme.muted,
      baseWatts: 0,
      costMonth: 71.20,
      kind: ApplianceKind.unknown,
      detectedMinsAgo: 35,
      drawShape: 'cyclic draw',
      recurrence: 'First time seen',
    ),
  ];

  double _realWatts(String? apiName) {
    if (apiName == null) return 0;
    for (final a
        in (widget.dashboard?.activeAppliances ?? const <ActiveAppliance>[])) {
      if (a.name == apiName) return a.watts;
    }
    return 0;
  }

  void _onTick() {
    if (!mounted) return;
    // Only the synthetic demo animates; Live shows the real (static) snapshot.
    if (!widget.demoMode) return;
    setState(() {
      var totalW = 0.0;
      for (final a in _appliances) {
        final double w;
        if (widget.demoMode) {
          w = a.baseWatts > 5
              ? a.baseWatts * (0.92 + _rng.nextDouble() * 0.16)
              : 0;
        } else {
          w = _realWatts(a.apiName);
        }
        a.watts = w;
        a.costMonth += (w / 1000) * _dtH * _rate;
        totalW += w;
      }
      _todayCost += (totalW / 1000) * _dtH * _rate;
    });
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = widget.dashboard;
    // Demo = synthetic showcase (animated). Live = the real appliances the
    // backend reports (AC + fridge today), with real watts and month cost.
    final list = widget.demoMode ? _appliances : _liveAppliances();
    final totalMonth = list.fold<double>(0, (s, a) => s + a.costMonth);
    final powerW = widget.demoMode
        ? list.fold<double>(0, (s, a) => s + a.watts)
        : (snapshot?.livePowerW ?? 0);
    final todayShown = widget.demoMode
        ? _todayCost
        : (snapshot?.todayCostRm ?? 0);
    final wholeHomeKw = (powerW / 1000).toStringAsFixed(2);
    final acList = list.where((a) => a.apiName == 'ac').toList();
    final acWatts = acList.isNotEmpty ? acList.first.watts : 0.0;
    final acOn = acWatts > 5;
    final away = (snapshot?.occupancyState ?? 'away').toLowerCase() == 'away';
    final acAlert = acOn && away;

    return RefreshIndicator(
      onRefresh: widget.onRefresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          PageHeader(
            subtitle: widget.demoMode
                ? 'Demo - simulated live readings'
                : (widget.backendOnline
                      ? 'Live from sensor - ${_timeLabel(snapshot?.timestamp)}'
                      : 'Live - no sensor connected'),
          ),
          const SizedBox(height: 12),
          if (_askable.isNotEmpty && !_bannerDismissed) ...[
            _identifyBanner(),
            const SizedBox(height: 12),
          ],
          // Cost hero - blue gradient (echoes the Bill masthead) with white
          // live flip-numbers. The AC card below stays white so it can pop red.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.tnbBlueLight, AppTheme.tnbBlueDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(AppTheme.radius),
              boxShadow: [
                BoxShadow(
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                  color: AppTheme.tnbBlueDark.withValues(alpha: 0.25),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.payments_outlined,
                      color: Colors.white.withValues(alpha: 0.9),
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'COST THIS MONTH',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.9),
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                FlipNumber(
                  formatRm(totalMonth),
                  style: Theme.of(
                    context,
                  ).textTheme.displayLarge!.copyWith(color: Colors.white),
                ),
                const SizedBox(height: 6),
                FlipNumber(
                  '${formatRm(todayShown)} today',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w600,
                    color: Colors.white.withValues(alpha: 0.92),
                  ),
                ),
                const SizedBox(height: 2),
                FlipNumber(
                  '${powerW.round()} W now',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white.withValues(alpha: 0.75),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'On track for ${formatRm(snapshot?.projectedBillRm ?? 667, decimals: 0)} this month on TNB RP4',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.8),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          InfoCard(
            accentColor: acAlert ? AppTheme.red : AppTheme.primary,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                        color: (acAlert ? AppTheme.red : AppTheme.primary)
                            .withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: Icon(
                        Icons.ac_unit,
                        color: acAlert ? AppTheme.red : AppTheme.primary,
                        size: 19,
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Expanded(child: Overline('AIR CONDITIONER')),
                    ChipLabel(
                      text: away ? 'Room empty' : 'Occupied',
                      color: away ? AppTheme.amber : AppTheme.green,
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                IntrinsicHeight(
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${acWatts.round()} W',
                              style: Theme.of(context).textTheme.displayMedium
                                  ?.copyWith(
                                    color: acAlert
                                        ? AppTheme.red
                                        : AppTheme.text,
                                  ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'AC branch - dedicated CT clamp',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      const VerticalDivider(width: 24, thickness: 1),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            '$wholeHomeKw kW',
                            style: Theme.of(context).textTheme.titleMedium
                                ?.copyWith(color: AppTheme.muted),
                          ),
                          Text(
                            'Whole-home',
                            style: Theme.of(context).textTheme.labelSmall,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (acAlert) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.red.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.warning_amber_rounded,
                          color: AppTheme.red,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Running in an empty room - cost adds up while nobody benefits.',
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: AppTheme.red),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                if (acOn) ...[
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: widget.onTurnOff,
                      icon: const Icon(Icons.power_settings_new, size: 18),
                      label: const Text('Turn off AC'),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.red,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Active appliances'),
          const SizedBox(height: 8),
          if (list.isEmpty)
            StatusLine(
              text:
                  'No live appliances reported. Start the Pi feed or switch to Demo.',
            )
          else
            for (final a in list) _tile(a),
          const SizedBox(height: 8),
          StatusLine(
            text: widget.demoMode
                ? 'Demo mode - readings are simulated. Switch to Live (top right) for real sensor data.'
                : 'Live mode - reading the ${_apiBaseLabel()} sensor feed.',
          ),
        ],
      ),
    );
  }

  Widget _tile(_DashAppliance a) {
    return ApplianceTile(
      svgAsset: a.svg,
      name: a.name,
      source: a.source,
      monthCost: formatRm(a.costMonth),
      power: '${a.watts.round()} W',
      accent: a.accent,
      onTap: () => _openZoom(a),
    );
  }

  void _openZoom(_DashAppliance a) {
    _openApplianceZoom(
      context,
      ApplianceZoomArgs(
        name: a.name,
        svgAsset: a.svg,
        watts: a.watts,
        startCostRm: a.costMonth,
        startTodayRm: a.costMonth / 30,
        accent: a.accent,
        kind: a.kind,
        coachKey: a.coachKey,
        coachHint: a.coachHint,
        detectedMinsAgo: a.detectedMinsAgo,
        drawShape: a.drawShape,
        recurrence: a.recurrence,
      ),
      widget.demoMode,
      widget.onOpenCoach,
    );
  }

  // Unknown loads worth proactively asking about: a RECURRING signature (seen
  // before), not a first sighting. We can cluster a repeat mystery load without
  // naming it - that recurrence (not a fake %) is the honest basis for asking.
  // Only in Demo: the live backend reports no unidentified loads yet.
  List<_DashAppliance> get _askable {
    if (!widget.demoMode) return const [];
    return _appliances
        .where(
          (a) =>
              a.kind == ApplianceKind.unknown &&
              (a.recurrence?.startsWith('Seen') ?? false),
        )
        .toList();
  }

  // Build the dashboard appliance list from real backend data (Live mode).
  List<_DashAppliance> _liveAppliances() {
    return [
      for (final a
          in (widget.dashboard?.activeAppliances ?? const <ActiveAppliance>[]))
        _DashAppliance(
          name: _prettyApi(a.name),
          svg: _svgForApi(a.name),
          source: a.kind == 'measured'
              ? 'Measured - Dedicated CT clamp'
              : 'Estimated - NILM',
          accent: a.kind == 'measured' ? AppTheme.red : AppTheme.amber,
          baseWatts: a.watts,
          costMonth: a.monthCostRm,
          kind: switch (a.kind) {
            'measured' => ApplianceKind.measured,
            'unknown' => ApplianceKind.unknown,
            _ => ApplianceKind.estimated,
          },
          apiName: a.name,
        ),
    ];
  }

  Widget _identifyBanner() {
    final loads = _askable;
    final first = loads.first;
    final n = loads.length;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openZoom(first),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
          decoration: BoxDecoration(
            color: AppTheme.amber.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.amber.withValues(alpha: 0.4)),
          ),
          child: Row(
            children: [
              const Icon(Icons.help_outline, color: AppTheme.amber, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  n == 1
                      ? '1 new load to identify - tap to help WattsEye learn it'
                      : '$n new loads to identify - tap to help WattsEye learn them',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.text,
                  ),
                ),
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.close, size: 18, color: AppTheme.muted),
                onPressed: () => setState(() => _bannerDismissed = true),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LivePowerCard extends StatelessWidget {
  const LivePowerCard({super.key, required this.watts});

  final double watts;

  @override
  Widget build(BuildContext context) {
    final kw = (watts / 1000).toStringAsFixed(2);
    return InfoCard(
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Current power',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 4),
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 350),
                  child: Text(
                    '$kw kW',
                    key: ValueKey(kw),
                    style: Theme.of(
                      context,
                    ).textTheme.titleLarge?.copyWith(fontSize: 24),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Whole-home main clamp plus exact AC branch reading.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Container(
            width: 68,
            height: 68,
            decoration: BoxDecoration(
              color: AppTheme.primary.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.bolt, color: AppTheme.primary, size: 34),
          ),
        ],
      ),
    );
  }
}

class _CoachFamilyFilter {
  const _CoachFamilyFilter(this.keyName, this.label, this.color);

  final String keyName;
  final String label;
  final Color color;
}

const _coachFamilyFilters = [
  _CoachFamilyFilter('waste', 'Waste', AppTheme.wasteBorder),
  _CoachFamilyFilter('tariff', 'Tariff', AppTheme.tariffBorder),
  _CoachFamilyFilter('forecast', 'Forecast', AppTheme.forecastBorder),
  _CoachFamilyFilter('context', 'Context', AppTheme.contextBorder),
  _CoachFamilyFilter('capital', 'Capital', AppTheme.capitalBorder),
];

class CoachPage extends StatefulWidget {
  const CoachPage({
    super.key,
    required this.cards,
    required this.demoMode,
    required this.onRefresh,
    required this.onCardTap,
    required this.onAction,
    required this.onSendWhatsApp,
  });

  final List<CoachCardState> cards;
  final bool demoMode;
  final Future<void> Function() onRefresh;
  final ValueChanged<String> onCardTap;
  final Future<void> Function(String keyName, InsightAction action) onAction;
  final Future<void> Function(String keyName) onSendWhatsApp;

  @override
  State<CoachPage> createState() => _CoachPageState();
}

class _CoachPageState extends State<CoachPage> {
  final Set<String> _selectedFamilies = <String>{};

  void _toggleFamily(String family) {
    setState(() {
      if (!_selectedFamilies.add(family)) {
        _selectedFamilies.remove(family);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final visibleCards = _selectedFamilies.isEmpty
        ? widget.cards
        : widget.cards
              .where((card) => _selectedFamilies.contains(card.data.family))
              .toList();
    final surfaced = visibleCards.take(2).toList();
    final rest = visibleCards.skip(2).toList();
    final potential = visibleCards
        .fold<double>(0, (sum, card) => sum + card.data.rmMonthly)
        .round();
    final countLabel = _selectedFamilies.isEmpty
        ? '${widget.cards.length} active insights'
        : '${visibleCards.length} of ${widget.cards.length} insights shown';

    return RefreshIndicator(
      onRefresh: widget.onRefresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          PageHeader(
            subtitle:
                '$countLabel - Potential RM $potential/month - Already saved RM 2.72',
          ),
          const SizedBox(height: 6),
          Text(
            widget.demoMode
                ? 'Demo: all 12 recommendation types (catalog) - not one real home.'
                : 'Live: cards from the Pi feed (or the bench log) - the real, sparser set.',
            style: Theme.of(context).textTheme.labelSmall,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final family in _coachFamilyFilters)
                FamilyFilterChip(
                  label: family.label,
                  color: family.color,
                  selected: _selectedFamilies.contains(family.keyName),
                  onSelected: () => _toggleFamily(family.keyName),
                ),
              if (_selectedFamilies.isNotEmpty)
                ActionChip(
                  avatar: const Icon(Icons.clear_all, size: 16),
                  label: const Text('Show all'),
                  onPressed: () => setState(_selectedFamilies.clear),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (visibleCards.isEmpty)
            const InfoCard(
              child: Text(
                'No insights match the selected filters.',
                style: TextStyle(color: AppTheme.muted),
              ),
            )
          else ...[
            const SectionLabel('Top recommendations now'),
            const SizedBox(height: 8),
            for (final card in surfaced)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: RecommendationCard(
                  card: card,
                  surfaced: true,
                  onTap: () => widget.onCardTap(card.data.keyName),
                  onSendWhatsApp: widget.onSendWhatsApp,
                ),
              ),
            if (rest.isNotEmpty) ...[
              const SectionLabel('More insights'),
              const SizedBox(height: 8),
              for (final card in rest)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: RecommendationCard(
                    card: card,
                    onTap: () => widget.onCardTap(card.data.keyName),
                    onSendWhatsApp: widget.onSendWhatsApp,
                  ),
                ),
            ],
          ],
          Text(
            'Generated by ML/insights/coach: correlator -> quantifier (TNB RP4) -> templates -> ranker.',
            style: Theme.of(context).textTheme.labelSmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class CardDetailScreen extends StatelessWidget {
  const CardDetailScreen({
    super.key,
    required this.card,
    required this.onAction,
  });

  final CoachCardState card;
  final Future<void> Function(InsightAction action) onAction;

  @override
  Widget build(BuildContext context) {
    final data = card.data;
    return Scaffold(
      appBar: AppBar(title: const Text('Recommendation')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FamilyTag(family: data.family),
              SeverityTag(severity: data.severity),
            ],
          ),
          const SizedBox(height: 12),
          Text(data.headline, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(data.impact, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 16),
          InfoCard(
            color: AppTheme.background,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Overline('TRY THIS'),
                const SizedBox(height: 6),
                Text(
                  data.action,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ChipLabel(text: data.saving, color: AppTheme.green),
                    ChipLabel(text: data.effort, color: AppTheme.muted),
                    // Only surface confidence when it's NOT high — a constant
                    // "High confidence" badge is noise; uncertainty is the
                    // signal worth showing.
                    if (!data.confidence.toLowerCase().startsWith('high'))
                      ChipLabel(text: data.confidence, color: AppTheme.amber),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () => onAction(InsightAction.done),
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Do this'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => onAction(InsightAction.remind),
            icon: const Icon(Icons.notifications_active_outlined),
            label: const Text('Remind me'),
          ),
          const SizedBox(height: 4),
          TextButton(
            onPressed: () => onAction(InsightAction.dismissed),
            child: const Text('Not useful'),
          ),
          const SizedBox(height: 8),
          InfoCard(
            child: Column(
              children: [
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: const EdgeInsets.only(bottom: 8),
                  title: Text(
                    'Why this appeared',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  children: [BulletList(lines: data.why)],
                ),
                const Divider(),
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: const EdgeInsets.only(bottom: 8),
                  title: Text(
                    'How we calculated this',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  children: [
                    for (final line in data.math)
                      Container(
                        width: double.infinity,
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.background,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          line,
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 12,
                            color: AppTheme.text,
                          ),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// Offline fallback for the bill breakdown — mirrors the tnb_tariff engine at
// the near-cliff 1,480 kWh projection so the demo reads the same with no backend.
const _fallbackBillLines = [
  BillLineItem(
    label: 'Generation',
    amountRm: 400.04,
    unitDetail: '27.03 sen/kWh',
  ),
  BillLineItem(label: 'Capacity', amountRm: 67.34, unitDetail: '4.55 sen/kWh'),
  BillLineItem(label: 'Network', amountRm: 190.18, unitDetail: '12.85 sen/kWh'),
  BillLineItem(
    label: 'Energy Efficiency Incentive (rebate)',
    amountRm: 0.0,
    unitDetail: '-0.00 sen/kWh (band >1000 kWh)',
  ),
  BillLineItem(
    label: 'AFA (Automatic Fuel Adjustment)',
    amountRm: 0.0,
    unitDetail: '+0.00 sen/kWh',
  ),
  BillLineItem(
    label: 'Retail charge',
    amountRm: 10.0,
    unitDetail: 'RM10.00/month',
  ),
];

/// Horizontal gauge that places the projected monthly kWh against the TNB RP4
/// 1,500 kWh high-band cliff, with the high-band zone tinted after the line.
class CliffGauge extends StatelessWidget {
  const CliffGauge({
    super.key,
    required this.projectedKwh,
    required this.thresholdKwh,
  });

  final double projectedKwh;
  final double thresholdKwh;

  @override
  Widget build(BuildContext context) {
    final maxScale = thresholdKwh * 1.12;
    final fillFrac = (projectedKwh / maxScale).clamp(0.0, 1.0);
    final cliffFrac = (thresholdKwh / maxScale).clamp(0.0, 1.0);
    final near =
        (thresholdKwh - projectedKwh) <= 50 && projectedKwh <= thresholdKwh;
    final over = projectedKwh > thresholdKwh;
    final fillColor = over || near ? AppTheme.tnbOrange : AppTheme.tnbTeal;
    return LayoutBuilder(
      builder: (context, c) {
        final w = c.maxWidth;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 46,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Positioned(
                    top: 18,
                    left: 0,
                    right: 0,
                    child: Container(
                      height: 12,
                      decoration: BoxDecoration(
                        color: AppTheme.divider,
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                  ),
                  Positioned(
                    top: 18,
                    left: w * cliffFrac,
                    right: 0,
                    child: Container(
                      height: 12,
                      decoration: const BoxDecoration(
                        color: AppTheme.tnbOrangeBg,
                        borderRadius: BorderRadius.horizontal(
                          right: Radius.circular(6),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: 18,
                    left: 0,
                    child: Container(
                      width: w * fillFrac,
                      height: 12,
                      decoration: BoxDecoration(
                        color: fillColor,
                        borderRadius: BorderRadius.circular(6),
                      ),
                    ),
                  ),
                  Positioned(
                    top: 10,
                    left: (w * cliffFrac) - 1,
                    child: Container(width: 2, height: 28, color: AppTheme.red),
                  ),
                  Positioned(
                    top: 0,
                    left: (w * cliffFrac - 16).clamp(0.0, w - 32),
                    child: const Text(
                      '1,500',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.red,
                      ),
                    ),
                  ),
                  Positioned(
                    top: 33,
                    left: (w * fillFrac - 12).clamp(0.0, w - 28),
                    child: Text(
                      'you',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: fillColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 2),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: const [
                Text(
                  '0 kWh',
                  style: TextStyle(fontSize: 11, color: AppTheme.muted),
                ),
                Text(
                  'high-band rate',
                  style: TextStyle(fontSize: 11, color: AppTheme.tnbOrange),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

/// Printed-statement header that mimics a real TNB "Bil Elektrik Anda":
/// red logo lockup, account meta, and the iconic yellow amount-due callout —
/// rendered as a clean mobile card rather than a literal paper photocopy.
class TnbStatementHeader extends StatelessWidget {
  const TnbStatementHeader({
    super.key,
    required this.modeLabel,
    required this.amount,
    required this.kwh,
    required this.effSen,
    required this.accountNo,
    required this.billDate,
    required this.dueDate,
  });

  final String modeLabel;
  final double amount;
  final int kwh;
  final double effSen;
  final String accountNo;
  final String billDate;
  final String dueDate;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(AppTheme.radius),
        border: Border.all(color: AppTheme.statementBorder),
        boxShadow: [
          BoxShadow(
            blurRadius: 16,
            offset: const Offset(0, 6),
            color: Colors.black.withValues(alpha: 0.06),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Masthead: TNB blue band with logo lockup, title + tariff tag.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(
              AppTheme.sp4,
              AppTheme.sp4,
              AppTheme.sp4,
              AppTheme.sp4,
            ),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [AppTheme.tnbBlueLight, AppTheme.tnbBlueDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.bolt,
                    color: AppTheme.tnbRed,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'TNB',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Tenaga Nasional',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.85),
                              fontWeight: FontWeight.w600,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 1),
                      const Text(
                        'Electricity Bill',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.20),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    modeLabel,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Account meta strip.
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppTheme.sp4,
              vertical: AppTheme.sp3,
            ),
            child: Row(
              children: [
                Expanded(
                  child: _MetaCell(label: 'Account No.', value: accountNo),
                ),
                Expanded(
                  child: _MetaCell(label: 'Bill Date', value: billDate),
                ),
              ],
            ),
          ),
          // Amount-due callout — the iconic yellow TNB box.
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppTheme.sp4,
              0,
              AppTheme.sp4,
              AppTheme.sp4,
            ),
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppTheme.billYellowBg,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.billYellowBorder),
              ),
              child: IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      width: 5,
                      decoration: const BoxDecoration(
                        color: AppTheme.billYellowBar,
                        borderRadius: BorderRadius.horizontal(
                          left: Radius.circular(10),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.all(AppTheme.sp3),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'TOTAL AMOUNT DUE',
                              style: TextStyle(
                                color: AppTheme.tnbInk,
                                fontWeight: FontWeight.w700,
                                fontSize: 11,
                                letterSpacing: 0.6,
                              ),
                            ),
                            Text(
                              'Jumlah Perlu Dibayar',
                              style: TextStyle(
                                color: AppTheme.tnbInk.withValues(alpha: 0.55),
                                fontWeight: FontWeight.w600,
                                fontSize: 10.5,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'RM ${amount.toStringAsFixed(2)}',
                              style: const TextStyle(
                                color: AppTheme.tnbInk,
                                fontSize: 32,
                                fontWeight: FontWeight.w700,
                                height: 1.0,
                                letterSpacing: -0.8,
                                fontFeatures: [FontFeature.tabularFigures()],
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                const Icon(
                                  Icons.event_outlined,
                                  size: 14,
                                  color: AppTheme.tnbInk,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  'Pay before $dueDate',
                                  style: const TextStyle(
                                    color: AppTheme.tnbInk,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 12.5,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Projected $kwh kWh - ${effSen.toStringAsFixed(2)} sen/kWh effective',
                              style: TextStyle(
                                color: AppTheme.tnbInk.withValues(alpha: 0.7),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MetaCell extends StatelessWidget {
  const _MetaCell({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            color: AppTheme.muted,
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            color: AppTheme.tnbInk,
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

/// Statement reference footer with a faux barcode — the bill-stub strip that
/// makes the page read as an authentic TNB document.
class BillReferenceFooter extends StatelessWidget {
  const BillReferenceFooter({super.key, required this.accountNo});

  final String accountNo;

  @override
  Widget build(BuildContext context) {
    // Deterministic bar widths so the "barcode" looks like a real one.
    const widths = [
      2.0,
      1.0,
      3.0,
      1.0,
      2.0,
      1.0,
      1.0,
      3.0,
      2.0,
      1.0,
      2.0,
      1.0,
      3.0,
      1.0,
      1.0,
      2.0,
      2.0,
      1.0,
      3.0,
      2.0,
      1.0,
      1.0,
      2.0,
      3.0,
      1.0,
      2.0,
      1.0,
      1.0,
      3.0,
      2.0,
      1.0,
      2.0,
      1.0,
      3.0,
      1.0,
      2.0,
    ];
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppTheme.sp4),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(AppTheme.radius),
        border: Border.all(color: AppTheme.statementBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Account No. $accountNo',
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: AppTheme.tnbInk,
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 38,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < widths.length; i++) ...[
                  Container(
                    width: widths[i],
                    color: i.isEven ? AppTheme.tnbInk : Colors.transparent,
                  ),
                  const SizedBox(width: 1),
                ],
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Scan to pay via myTNB / JomPAY - bill generated by WattsEye',
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ],
      ),
    );
  }
}

class BillPage extends StatelessWidget {
  const BillPage({
    super.key,
    required this.touPreview,
    required this.onTogglePreview,
    required this.onOpenCoach,
    this.bill,
  });

  final bool touPreview;
  final VoidCallback onTogglePreview;
  final ValueChanged<String> onOpenCoach;
  final BillInfo? bill;

  @override
  Widget build(BuildContext context) {
    final standardTotal = bill?.projectedTotalRm ?? 667.56;
    final touTotal = bill?.touProjectedTotalRm ?? 650.27;
    final kwh = (bill?.projectedKwh ?? 1480).round();
    final eff = bill?.effectiveSenPerKwh ?? 45.11;
    final saving = standardTotal - touTotal;
    final headlineTotal = touPreview ? touTotal : standardTotal;
    final lines = (bill?.lines.isNotEmpty ?? false)
        ? bill!.lines
        : _fallbackBillLines;
    final threshold = bill?.highBandThresholdKwh ?? 1500;
    final headroom = bill?.headroomKwh ?? (threshold - kwh);
    final lowGen = bill?.lowBandGenSen ?? 27.03;
    final highGen = bill?.highBandGenSen ?? 37.03;
    final inHighBand = bill?.inHighBand ?? false;
    return RefreshIndicator(
      onRefresh: () async {},
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          const PageHeader(
            subtitle: "Your TNB RP4 bill, projected from this month's usage",
          ),
          const SizedBox(height: AppTheme.sp3),
          // --- TNB printed-statement header (Bil Elektrik Anda) ---
          TnbStatementHeader(
            modeLabel: touPreview ? 'Time-of-Use (preview)' : 'RP4 - Standard',
            amount: headlineTotal,
            kwh: kwh,
            effSen: eff,
            accountNo: '0123 4567 4291',
            billDate: '31 May 2026',
            dueDate: '14 Jun 2026',
          ),
          const SizedBox(height: AppTheme.sp4),
          const SectionLabel('Bill breakdown'),
          const SizedBox(height: AppTheme.sp2),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final line in lines)
                  BillLine(
                    line.label,
                    line.unitDetail,
                    line.amountRm < 0
                        ? '- ${formatRm(-line.amountRm)}'
                        : formatRm(line.amountRm),
                    positive: line.amountRm < 0,
                  ),
                const Divider(),
                BillLine(
                  'Projected total',
                  'TNB RP4 standard schedule - your usage pattern',
                  formatRm(standardTotal),
                  strong: true,
                ),
                if (touPreview) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Breakdown shown for the Standard tariff. Time-of-Use total compared below.',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Standard vs Time-of-Use'),
          const SizedBox(height: 8),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Based on your last 30 days. ToU peak hours are weekdays 2-10 PM; off-peak all other hours.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: PlanPanel(
                        label: 'Standard',
                        amount: formatRm(standardTotal),
                        detail: '${eff.toStringAsFixed(2)} sen/kWh',
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: PlanPanel(
                        label: 'Time-of-Use',
                        amount: formatRm(touTotal),
                        detail: 'est. ToU plan',
                        recommended: true,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    ChipLabel(
                      text: saving >= 0
                          ? 'ToU cheaper by ${formatRm(saving)}/month'
                          : 'ToU costs ${formatRm(-saving)} more/month',
                      color: saving >= 0 ? AppTheme.green : AppTheme.amber,
                    ),
                    const ChipLabel(
                      text: '35% peak / 65% off-peak',
                      color: AppTheme.muted,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'Shifting half your AC runtime to before 2 PM or after 10 PM could increase the saving to about RM12/month.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: onTogglePreview,
                      icon: Icon(
                        touPreview
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                      ),
                      label: Text(
                        touPreview ? 'Show standard' : 'Preview as ToU',
                      ),
                    ),
                    FilledButton(
                      onPressed: () => onOpenCoach('tou_switch'),
                      child: const Text('See Coach to apply'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('1,500 kWh high-band cliff'),
          const SizedBox(height: 8),
          InfoCard(
            accentColor: AppTheme.tnbOrange,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  inHighBand
                      ? 'You are over the 1,500 kWh cliff - every unit this month is billed at the ${highGen.toStringAsFixed(2)} sen/kWh high-band generation rate.'
                      : 'Projected $kwh kWh - ${headroom.toStringAsFixed(0)} kWh under the 1,500 kWh cliff. Cross it and the generation rate jumps from ${lowGen.toStringAsFixed(2)} to ${highGen.toStringAsFixed(2)} sen/kWh on every unit.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: AppTheme.sp3),
                CliffGauge(
                  projectedKwh: kwh.toDouble(),
                  thresholdKwh: threshold,
                ),
                const SizedBox(height: AppTheme.sp3),
                Wrap(
                  spacing: AppTheme.sp2,
                  runSpacing: AppTheme.sp2,
                  children: [
                    ChipLabel(
                      text: '${headroom.toStringAsFixed(0)} kWh headroom',
                      color: (!inHighBand && headroom <= 50)
                          ? AppTheme.tnbOrange
                          : (inHighBand ? AppTheme.red : AppTheme.green),
                    ),
                    ChipLabel(
                      text:
                          'Cliff: +${(highGen - lowGen).toStringAsFixed(2)} sen/kWh',
                      color: AppTheme.muted,
                    ),
                  ],
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: () => onOpenCoach('rp4_tier_cliff'),
                    child: const Text('See Coach for action'),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Tariff schedule'),
          const SizedBox(height: 8),
          const InfoCard(
            child: Column(
              children: [
                SettingsRow(
                  label: 'Regulatory Period 4 (RP4)',
                  value: 'Active',
                ),
                SettingsRow(
                  label: 'Effective dates',
                  value: '1 Jul 2025 - 31 Dec 2027',
                ),
                SettingsRow(
                  label: 'AFA value this month',
                  value: '+0.00 sen/kWh',
                ),
                SettingsRow(label: 'Source data', value: 'TNB RP4 schedule'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => launchUrl(
              Uri.parse('$defaultApiBaseUrl/api/report/monthly?mode=summary'),
              mode: LaunchMode.externalApplication,
            ),
            icon: const Icon(Icons.picture_as_pdf_outlined),
            label: const Text('Download monthly report (PDF)'),
          ),
          const SizedBox(height: 16),
          const BillReferenceFooter(accountNo: '0123 4567 4291'),
        ],
      ),
    );
  }
}

enum _UsageSeries { ac, other, unknown }

const _allUsageSeries = [
  _UsageSeries.ac,
  _UsageSeries.other,
  _UsageSeries.unknown,
];

String _usageSeriesLabel(_UsageSeries series) {
  return switch (series) {
    _UsageSeries.ac => 'AC',
    _UsageSeries.other => 'Other',
    _UsageSeries.unknown => 'Unknown',
  };
}

Color _usageSeriesColor(_UsageSeries series) {
  return switch (series) {
    _UsageSeries.ac => AppTheme.primary,
    _UsageSeries.other => AppTheme.muted,
    _UsageSeries.unknown => AppTheme.amber,
  };
}

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key, this.history = const []});

  final List<HistoryDay> history;

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  final Set<_UsageSeries> _visibleSeries = {..._allUsageSeries};

  void _toggleSeries(_UsageSeries series) {
    setState(() {
      if (!_visibleSeries.add(series)) {
        _visibleSeries.remove(series);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {},
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          const PageHeader(
            subtitle: 'Bill trend, appliance cost, and waste history',
          ),
          const SizedBox(height: 12),
          if (widget.history.isNotEmpty) ...[
            InfoCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Overline('RECENT DAYS (LIVE)'),
                  const SizedBox(height: 8),
                  for (final day in widget.history)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            day.date,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          Text(
                            'RM${day.costRm.toStringAsFixed(2)}',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const MetricGrid(
                  metrics: [
                    MetricData(
                      'Month to date',
                      'RM 631.40',
                      Icons.calendar_month_outlined,
                      AppTheme.primary,
                    ),
                    MetricData(
                      'Projected bill',
                      'RM 667',
                      Icons.trending_up_outlined,
                      AppTheme.amber,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _StackedBars(visibleSeries: _visibleSeries),
                const SizedBox(height: 8),
                _ChartLegend(
                  visibleSeries: _visibleSeries,
                  onToggle: _toggleSeries,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Appliance breakdown'),
          const SizedBox(height: 8),
          const InfoCard(
            child: Column(
              children: [
                BillLine(
                  'Air Conditioner',
                  'Measured directly - 29% of projected bill',
                  'RM43.20',
                ),
                BillLine(
                  'Fridge',
                  'Estimated - health watch active',
                  '~RM18.70',
                ),
                BillLine('Kettle', 'Estimated - normal routine', '~RM4.70'),
                BillLine(
                  'Unknown / Other',
                  'Needs user labels to improve future breakdown',
                  'RM15.40',
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Waste history'),
          const SizedBox(height: 8),
          const InfoCard(
            child: Column(
              children: [
                BillLine(
                  'Empty-room AC',
                  '3 events this week - 71 minutes total',
                  'RM0.64',
                ),
                BillLine(
                  'High standby nights',
                  '1 night above normal baseline',
                  'RM0.28',
                ),
                BillLine(
                  'User corrections',
                  '2 labels improved household profiles',
                  'Saved',
                  positive: true,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class ProfilePage extends StatelessWidget {
  const ProfilePage({
    super.key,
    required this.integrations,
    required this.backendOnline,
  });

  final IntegrationStatus? integrations;
  final bool backendOnline;

  @override
  Widget build(BuildContext context) {
    final status = integrations;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        const PageHeader(
          subtitle: 'Account, household, hardware, and data settings',
        ),
        const SizedBox(height: 12),
        const InfoCard(
          child: Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: AppTheme.primary,
                child: Text(
                  'CL',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Choong Zhuo Lin',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.text,
                      ),
                    ),
                    Text(
                      'choongzhuolin@gmail.com',
                      style: TextStyle(fontSize: 13, color: AppTheme.muted),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const ProfileSection(
          title: 'Household',
          rows: [
            SettingsRow(label: 'Address', value: 'Petaling Jaya, Selangor'),
            SettingsRow(label: 'Weather location', value: 'Kuala Lumpur'),
            SettingsRow(label: 'Household size', value: '4 people'),
            SettingsRow(label: 'Home type', value: 'Double-storey terrace'),
          ],
        ),
        ProfileSection(
          title: 'Backend integrations',
          rows: [
            SettingsRow(
              label: 'API bridge',
              value: backendOnline ? 'Connected' : 'Offline',
            ),
            SettingsRow(
              label: 'Monthly PDF report',
              value: _readyLabel(status?.pdfAvailable),
            ),
            SettingsRow(
              label: 'Open-Meteo weather',
              value: _readyLabel(status?.weatherAvailable),
            ),
            SettingsRow(
              label: 'NILM .pth models',
              value: status == null
                  ? 'Unknown'
                  : '${status.nilmModelCount} found',
            ),
            SettingsRow(
              label: 'PyTorch runtime',
              value: _readyLabel(status?.torchAvailable),
            ),
            SettingsRow(
              label: 'Joblib ML models',
              value: status == null
                  ? 'Unknown'
                  : '${status.joblibModelCount} found',
            ),
          ],
        ),
        const ProfileSection(
          title: 'TNB Account',
          rows: [
            SettingsRow(label: 'Account number', value: '**** 4291'),
            SettingsRow(label: 'Tariff plan', value: 'RP4 - Standard'),
            SettingsRow(label: 'Smart meter', value: 'Linked'),
            SettingsRow(label: 'myTNB integration', value: 'Linked'),
          ],
        ),
        const ProfileSection(
          title: 'Coach & Notifications',
          rows: [
            SettingsRow(label: 'WhatsApp number', value: '**** 8472'),
            SettingsRow(
              label: 'Push frequency',
              value: 'Real-time + weekly digest',
            ),
            SettingsRow(label: 'Language', value: 'English - Manglish tone'),
            SettingsRow(label: 'Quiet hours', value: '23:00 - 07:00'),
          ],
        ),
        const ProfileSection(
          title: 'Hardware',
          rows: [
            SettingsRow(label: 'WattsEye Pi', value: 'Online - 14d uptime'),
            SettingsRow(label: 'Main feeder clamp', value: 'OK'),
            SettingsRow(label: 'Dedicated AC clamp', value: 'OK'),
            SettingsRow(label: 'mmWave occupancy', value: 'OK'),
            SettingsRow(label: 'Firmware', value: 'v0.4.2'),
          ],
        ),
        ProfileSection(
          title: 'Data',
          rows: [
            const SettingsRow(
              label: 'Local storage',
              value: '47 days - 312 MB',
            ),
            const SettingsRow(label: 'Cloud sync', value: 'Last: 2 min ago'),
            SettingsRow(
              label: 'Export my data',
              actionable: true,
              onTap: () => _snack(context, 'Data export queued'),
            ),
            SettingsRow(
              label: 'Clear local data',
              actionable: true,
              danger: true,
              onTap: () =>
                  _snack(context, 'Clear local data not available in demo'),
            ),
          ],
        ),
        ProfileSection(
          title: 'Account',
          rows: [
            SettingsRow(
              label: 'Help & support',
              actionable: true,
              onTap: () => _snack(context, 'Help centre opens in browser'),
            ),
            SettingsRow(
              label: 'Privacy policy',
              actionable: true,
              onTap: () => _snack(context, 'Privacy policy opens in browser'),
            ),
            SettingsRow(
              label: 'Sign out',
              actionable: true,
              danger: true,
              onTap: () => _snack(context, 'Sign out not available in demo'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          'WattsEye v0.4.2 - Made in Malaysia',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.labelSmall,
        ),
      ],
    );
  }
}

class PageHeader extends StatelessWidget {
  const PageHeader({super.key, required this.subtitle});

  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.primary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.10)),
      ),
      child: Row(
        children: [
          const Icon(Icons.sensors_outlined, size: 18, color: AppTheme.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
          ),
        ],
      ),
    );
  }
}

class SheetSection extends StatelessWidget {
  const SheetSection({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surface,
      borderRadius: BorderRadius.circular(8),
      child: Column(
        children: [
          for (var i = 0; i < children.length; i++) ...[
            children[i],
            if (i != children.length - 1)
              const Divider(indent: 16, endIndent: 16),
          ],
        ],
      ),
    );
  }
}

class NativeListTile extends StatelessWidget {
  const NativeListTile({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.trailing,
    this.color = AppTheme.primary,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String trailing;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        radius: 19,
        backgroundColor: color.withValues(alpha: 0.12),
        child: Icon(icon, color: color, size: 20),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(subtitle),
      trailing: Text(
        trailing,
        textAlign: TextAlign.right,
        style: const TextStyle(
          fontWeight: FontWeight.w700,
          color: AppTheme.text,
        ),
      ),
    );
  }
}

class InfoCard extends StatelessWidget {
  const InfoCard({
    super.key,
    required this.child,
    this.accentColor,
    this.color,
    this.elevated = true,
  });

  final Widget child;
  final Color? accentColor;
  final Color? color;

  /// Top-level cards float with a shadow. Cards nested inside another card
  /// (e.g. metric tiles) set this false to avoid muddy stacked shadows and
  /// use a hairline border instead.
  final bool elevated;

  @override
  Widget build(BuildContext context) {
    final border = accentColor != null
        ? Border(left: BorderSide(color: accentColor!, width: 4))
        : (elevated ? null : Border.all(color: AppTheme.divider));
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? AppTheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: border,
        boxShadow: elevated
            ? [
                BoxShadow(
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                  color: Colors.black.withValues(alpha: 0.07),
                ),
                BoxShadow(
                  blurRadius: 2,
                  offset: const Offset(0, 1),
                  color: Colors.black.withValues(alpha: 0.04),
                ),
              ]
            : null,
      ),
      child: child,
    );
  }
}

class MetricData {
  const MetricData(this.label, this.value, this.icon, this.color);

  final String label;
  final String value;
  final IconData icon;
  final Color color;
}

class MetricGrid extends StatelessWidget {
  const MetricGrid({super.key, required this.metrics});

  final List<MetricData> metrics;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      physics: const NeverScrollableScrollPhysics(),
      shrinkWrap: true,
      crossAxisCount: 2,
      crossAxisSpacing: 8,
      mainAxisSpacing: 8,
      childAspectRatio: 2.15,
      children: [
        for (final metric in metrics)
          InfoCard(
            elevated: false,
            child: Row(
              children: [
                Icon(metric.icon, color: metric.color),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        metric.label,
                        style: Theme.of(context).textTheme.labelSmall,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        metric.value,
                        style: Theme.of(context).textTheme.titleMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class ApplianceTile extends StatelessWidget {
  const ApplianceTile({
    super.key,
    required this.svgAsset,
    required this.name,
    required this.source,
    required this.monthCost,
    required this.power,
    required this.accent,
    this.onTap,
  });

  final String svgAsset;
  final String name;
  final String source;
  final String monthCost;
  final String power;
  final Color accent;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: InfoCard(
          child: Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: accent.withValues(alpha: 0.12),
                child: SvgPicture.asset(
                  svgAsset,
                  width: 24,
                  colorFilter: ColorFilter.mode(accent, BlendMode.srcIn),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: Theme.of(context).textTheme.titleMedium),
                    Text(
                      source,
                      style: Theme.of(context).textTheme.bodySmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    monthCost,
                    textAlign: TextAlign.end,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppTheme.text,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '$power now',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class RecommendationCard extends StatelessWidget {
  const RecommendationCard({
    super.key,
    required this.card,
    required this.onTap,
    this.surfaced = false,
    this.onSendWhatsApp,
  });

  final CoachCardState card;
  final VoidCallback onTap;
  final bool surfaced;
  final Future<void> Function(String keyName)? onSendWhatsApp;

  @override
  Widget build(BuildContext context) {
    final data = card.data;
    final acted = card.action == InsightAction.done;
    final dismissed = card.action == InsightAction.dismissed;
    return Opacity(
      opacity: dismissed ? 0.55 : 1,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: InfoCard(
          accentColor: familyBorder(data.family),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    data.headline,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      decoration: dismissed ? TextDecoration.lineThrough : null,
                    ),
                    maxLines: surfaced ? 2 : 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [
                      // Family is already encoded by the coloured left accent
                      // bar, so no FamilyTag pill here — keep the data-source
                      // (LIVE/REPLAY) signal and priority only.
                      if (data.dataSource == 'live')
                        ChipLabel(text: 'LIVE', color: AppTheme.green),
                      if (data.dataSource == 'replay')
                        ChipLabel(text: 'REPLAY', color: AppTheme.amber),
                      SeverityTag(severity: data.severity),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                data.impact,
                style: Theme.of(context).textTheme.bodySmall,
                maxLines: surfaced ? 3 : 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Icon(
                    acted ? Icons.check_circle : Icons.savings_outlined,
                    color: acted ? AppTheme.green : AppTheme.primary,
                    size: 18,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      data.saving,
                      style: TextStyle(
                        fontSize: 19,
                        color: acted ? AppTheme.green : AppTheme.text,
                        fontWeight: FontWeight.w700,
                        height: 1.1,
                        letterSpacing: -0.3,
                        decoration: acted ? TextDecoration.lineThrough : null,
                      ),
                    ),
                  ),
                  if (data.pushEligible && onSendWhatsApp != null) ...[
                    GestureDetector(
                      onTap: () => onSendWhatsApp!(data.keyName),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: AppTheme.green.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.chat_outlined,
                              size: 15,
                              color: AppTheme.green,
                            ),
                            SizedBox(width: 4),
                            Text(
                              'WhatsApp',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.green,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                  ],
                  const Icon(Icons.chevron_right, color: AppTheme.muted),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class BillLine extends StatelessWidget {
  const BillLine(
    this.title,
    this.subtitle,
    this.amount, {
    super.key,
    this.positive = false,
    this.strong = false,
  });

  final String title;
  final String subtitle;
  final String amount;
  final bool positive;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: strong ? 16 : 14,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.text,
                  ),
                ),
                const SizedBox(height: 2),
                Text(subtitle, style: Theme.of(context).textTheme.labelSmall),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            amount,
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: positive ? AppTheme.green : AppTheme.text,
            ),
          ),
        ],
      ),
    );
  }
}

class PlanPanel extends StatelessWidget {
  const PlanPanel({
    super.key,
    required this.label,
    required this.amount,
    required this.detail,
    this.recommended = false,
  });

  final String label;
  final String amount;
  final String detail;
  final bool recommended;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: recommended
            ? AppTheme.green.withValues(alpha: 0.08)
            : AppTheme.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: recommended ? AppTheme.green : AppTheme.divider,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall,
          ),
          const SizedBox(height: 4),
          Text(amount, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 2),
          Text(detail, style: Theme.of(context).textTheme.labelSmall),
        ],
      ),
    );
  }
}

class ProfileSection extends StatelessWidget {
  const ProfileSection({super.key, required this.title, required this.rows});

  final String title;
  final List<Widget> rows;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionLabel(title),
          const SizedBox(height: 8),
          InfoCard(child: Column(children: rows)),
        ],
      ),
    );
  }
}

class SettingsRow extends StatelessWidget {
  const SettingsRow({
    super.key,
    required this.label,
    this.value,
    this.actionable = false,
    this.danger = false,
    this.onTap,
  });

  final String label;
  final String? value;
  final bool actionable;
  final bool danger;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final child = Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: danger ? AppTheme.red : AppTheme.text,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (value != null)
            Flexible(
              child: Text(
                value!,
                textAlign: TextAlign.right,
                style: const TextStyle(color: AppTheme.muted),
              ),
            ),
          if (actionable)
            const Icon(Icons.chevron_right, color: AppTheme.muted),
        ],
      ),
    );
    if (!actionable) return child;
    return InkWell(onTap: onTap, child: child);
  }
}

class _StackedBars extends StatelessWidget {
  const _StackedBars({required this.visibleSeries});

  final Set<_UsageSeries> visibleSeries;

  static const bars = [
    [42.0, 52.0, 8.0, 40.0],
    [48.0, 55.0, 10.0, 35.0],
    [58.0, 62.0, 6.0, 32.0],
    [46.0, 48.0, 12.0, 40.0],
    [72.0, 68.0, 9.0, 23.0],
    [64.0, 57.0, 16.0, 27.0],
    [82.0, 61.0, 14.0, 25.0],
  ];

  int _barFlex(List<double> bar, _UsageSeries series) {
    return switch (series) {
      _UsageSeries.ac => bar[1].round(),
      _UsageSeries.other => bar[3].round(),
      _UsageSeries.unknown => bar[2].round(),
    };
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 150,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final bar in bars)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: SizedBox(
                  height: 140 * bar[0] / 100,
                  child: ClipRRect(
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(4),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      verticalDirection: VerticalDirection.up,
                      children: [
                        for (final series in _allUsageSeries)
                          if (visibleSeries.contains(series))
                            Expanded(
                              flex: _barFlex(bar, series),
                              child: Container(
                                color: _usageSeriesColor(series),
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

class _ChartLegend extends StatelessWidget {
  const _ChartLegend({required this.visibleSeries, required this.onToggle});

  final Set<_UsageSeries> visibleSeries;
  final ValueChanged<_UsageSeries> onToggle;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      children: [
        for (final series in _allUsageSeries)
          LegendItem(
            label: _usageSeriesLabel(series),
            color: _usageSeriesColor(series),
            selected: visibleSeries.contains(series),
            onTap: () => onToggle(series),
          ),
      ],
    );
  }
}

class LegendItem extends StatelessWidget {
  const LegendItem({
    super.key,
    required this.label,
    required this.color,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Opacity(
        opacity: selected ? 1 : 0.38,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                selected ? Icons.check_circle : Icons.circle_outlined,
                size: selected ? 14 : 12,
                color: color,
              ),
              const SizedBox(width: 4),
              Text(
                label,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: selected ? AppTheme.text : AppTheme.muted,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class BulletList extends StatelessWidget {
  const BulletList({super.key, required this.lines});

  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final line in lines)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('- ', style: TextStyle(color: AppTheme.muted)),
                Expanded(
                  child: Text(
                    line,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class StatusLine extends StatelessWidget {
  const StatusLine({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return InfoCard(
      color: AppTheme.primary.withValues(alpha: 0.06),
      child: Row(
        children: [
          const Icon(Icons.visibility_outlined, color: AppTheme.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text, style: Theme.of(context).textTheme.titleMedium);
  }
}

class Overline extends StatelessWidget {
  const Overline(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.8,
        color: AppTheme.muted,
      ),
    );
  }
}

class ChipLabel extends StatelessWidget {
  const ChipLabel({super.key, required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppTheme.chipRadius),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }
}

/// Compact global Demo/Live pill toggle for the AppBar.
class ModeToggle extends StatelessWidget {
  const ModeToggle({super.key, required this.demo, required this.onChanged});

  final bool demo;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.divider),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _seg('Demo', demo, AppTheme.amber, () => onChanged(true)),
          _seg('Live', !demo, AppTheme.green, () => onChanged(false)),
        ],
      ),
    );
  }

  Widget _seg(String label, bool selected, Color color, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? color.withValues(alpha: 0.16) : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: selected ? color : AppTheme.muted,
          ),
        ),
      ),
    );
  }
}

class FamilyFilterChip extends StatelessWidget {
  const FamilyFilterChip({
    super.key,
    required this.label,
    required this.color,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final Color color;
  final bool selected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: Icon(
        selected ? Icons.check_circle : Icons.circle,
        size: selected ? 16 : 10,
        color: selected ? color : color.withValues(alpha: 0.8),
      ),
      label: Text(label),
      labelStyle: TextStyle(
        color: selected ? AppTheme.text : AppTheme.muted,
        fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
      ),
      backgroundColor: selected ? color.withValues(alpha: 0.12) : null,
      side: BorderSide(color: selected ? color : AppTheme.divider),
      onPressed: onSelected,
    );
  }
}

class FamilyTag extends StatelessWidget {
  const FamilyTag({super.key, required this.family});

  final String family;

  @override
  Widget build(BuildContext context) {
    final colors = familyTagColors(family);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: colors.$1,
        borderRadius: BorderRadius.circular(AppTheme.chipRadius),
      ),
      child: Text(
        family.toUpperCase(),
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: colors.$2,
        ),
      ),
    );
  }
}

class SeverityTag extends StatelessWidget {
  const SeverityTag({super.key, required this.severity});

  final String severity;

  @override
  Widget build(BuildContext context) {
    final color = switch (severity) {
      'high' => AppTheme.red,
      'medium' => AppTheme.amber,
      _ => AppTheme.muted,
    };
    return ChipLabel(text: severity.toUpperCase(), color: color);
  }
}

Color familyBorder(String family) {
  return switch (family) {
    'waste' => AppTheme.wasteBorder,
    'tariff' => AppTheme.tariffBorder,
    'forecast' => AppTheme.forecastBorder,
    'context' => AppTheme.contextBorder,
    'capital' => AppTheme.capitalBorder,
    _ => AppTheme.muted,
  };
}

(Color, Color) familyTagColors(String family) {
  return switch (family) {
    'waste' => (AppTheme.wasteTagBg, AppTheme.wasteTagText),
    'tariff' => (AppTheme.tariffTagBg, AppTheme.tariffTagText),
    'forecast' => (AppTheme.forecastTagBg, AppTheme.forecastTagText),
    'context' => (AppTheme.contextTagBg, AppTheme.contextTagText),
    'capital' => (AppTheme.capitalTagBg, AppTheme.capitalTagText),
    _ => (AppTheme.divider, AppTheme.muted),
  };
}

void _snack(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}

extension InsightActionApi on InsightAction {
  String get apiValue {
    return switch (this) {
      InsightAction.done => 'do',
      InsightAction.remind => 'remind',
      InsightAction.dismissed => 'dismiss',
      InsightAction.none => 'none',
    };
  }
}

CoachCardState _coachCardFromApi(Map<String, dynamic> json) {
  final monthly = _jsonDouble(json['impact_rm_monthly']);
  return CoachCardState(
    CoachCardData(
      id: _jsonInt(json['archetype_id']),
      keyName: json['archetype_key']?.toString() ?? 'unknown',
      family: json['family']?.toString() ?? 'context',
      severity: json['severity']?.toString() ?? 'low',
      headline: json['headline']?.toString() ?? 'Untitled insight',
      impact: json['impact_text']?.toString() ?? '',
      action: json['action_text']?.toString() ?? '',
      saving:
          json['saving_text']?.toString().replaceFirst(
            RegExp(r'^Expected saving:\s*'),
            '',
          ) ??
          'RM ${monthly.toStringAsFixed(0)}/month',
      effort: json['effort_text']?.toString() ?? 'Low effort',
      confidence: json['confidence_label']?.toString() ?? 'Medium confidence',
      rmMonthly: monthly,
      why: _jsonStringList(json['why_lines']),
      math: _jsonStringList(json['math_lines']),
      dataSource: json['data_source']?.toString() ?? 'showcase',
      pushEligible: json['push_eligible'] == true,
    ),
  );
}

int _jsonInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.round();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _jsonDouble(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

List<String> _jsonStringList(Object? value) {
  if (value is! List) return const [];
  return [for (final item in value) item.toString()];
}

String _timeLabel(DateTime? timestamp) {
  if (timestamp == null) return 'synced just now';
  final hour = timestamp.hour.toString().padLeft(2, '0');
  final minute = timestamp.minute.toString().padLeft(2, '0');
  return 'synced $hour:$minute';
}

String _apiBaseLabel() => defaultApiBaseUrl;

String _prettyApi(String name) => switch (name.toLowerCase()) {
  'ac' || 'air_conditioner' => 'Air Conditioner',
  'fridge' || 'refrigerator' => 'Fridge',
  'kettle' => 'Kettle',
  'washing_machine' || 'washer' => 'Washing Machine',
  'hair_dryer' => 'Hair Dryer',
  'iron' => 'Iron',
  _ =>
    name.isEmpty
        ? 'Unknown'
        : name[0].toUpperCase() + name.substring(1).replaceAll('_', ' '),
};

String _svgForApi(String name) => switch (name.toLowerCase()) {
  'ac' || 'air_conditioner' => 'assets/appliances/air-conditioning.svg',
  'fridge' || 'refrigerator' => 'assets/appliances/fridge.svg',
  'kettle' => 'assets/appliances/kettle.svg',
  'washing_machine' || 'washer' => 'assets/appliances/wash-machine.svg',
  'hair_dryer' => 'assets/appliances/hair-dryer.svg',
  'iron' => 'assets/appliances/iron.svg',
  _ => 'assets/appliances/unknown.svg',
};

/// Single currency format for the whole app: always "RM " + amount, so figures
/// read the same on every page. Pass decimals: 0 for rounded headline numbers.
String formatRm(num amount, {int decimals = 2}) {
  return 'RM ${amount.toStringAsFixed(decimals)}';
}

String _readyLabel(bool? ready) {
  return switch (ready) {
    true => 'Ready',
    false => 'Missing',
    null => 'Unknown',
  };
}

enum ApplianceKind { measured, estimated, unknown }

class ApplianceZoomArgs {
  const ApplianceZoomArgs({
    required this.name,
    required this.svgAsset,
    required this.watts,
    required this.startCostRm,
    required this.startTodayRm,
    required this.accent,
    required this.kind,
    this.coachKey,
    this.coachHint,
    this.detectedMinsAgo,
    this.drawShape,
    this.recurrence,
    this.guessName,
    this.guessConfidence,
  });

  final String name;
  final String svgAsset;
  final double watts;
  final double startCostRm;
  final double startTodayRm;
  final Color accent;
  final ApplianceKind kind;
  final String? coachKey;
  final String? coachHint;
  final int? detectedMinsAgo;
  final String? drawShape;
  final String? recurrence;
  final String? guessName;
  final double? guessConfidence;
}

void _openApplianceZoom(
  BuildContext context,
  ApplianceZoomArgs args,
  bool demoMode,
  ValueChanged<String> onOpenCoach,
) {
  Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => ApplianceZoomScreen(
        args: args,
        demoMode: demoMode,
        onOpenCoach: onOpenCoach,
      ),
    ),
  );
}

/// A number whose digits flip individually when they change (like a live
/// counter) — quiet between updates, no continuous ticking.
class FlipNumber extends StatelessWidget {
  const FlipNumber(this.value, {super.key, required this.style});

  final String value;
  final TextStyle style;

  @override
  Widget build(BuildContext context) {
    final s = style.copyWith(
      fontFeatures: const [FontFeature.tabularFigures()],
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < value.length; i++)
          _FlipChar(slot: i, char: value[i], style: s),
      ],
    );
  }
}

class _FlipChar extends StatelessWidget {
  const _FlipChar({
    required this.slot,
    required this.char,
    required this.style,
  });

  final int slot;
  final String char;
  final TextStyle style;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 160),
      transitionBuilder: (child, anim) => ClipRect(
        child: SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, -0.7),
            end: Offset.zero,
          ).animate(anim),
          child: FadeTransition(opacity: anim, child: child),
        ),
      ),
      child: Text(char, key: ValueKey('$slot-$char'), style: style),
    );
  }
}

/// Tap-to-zoom appliance view: illustration on the left, a live accumulated-cost
/// meter on the right whose trailing decimals flip as cost integrates from the
/// (real or simulated) power reading.
class ApplianceZoomScreen extends StatefulWidget {
  const ApplianceZoomScreen({
    super.key,
    required this.args,
    required this.demoMode,
    required this.onOpenCoach,
  });

  final ApplianceZoomArgs args;
  final bool demoMode;
  final ValueChanged<String> onOpenCoach;

  @override
  State<ApplianceZoomScreen> createState() => _ApplianceZoomScreenState();
}

class _ApplianceZoomScreenState extends State<ApplianceZoomScreen> {
  static const _rateRmPerKwh = 0.40;
  static const _tick = Duration(milliseconds: 250);
  final _rng = Random();
  final _api = WattsEyeApi();
  late double _cost;
  late double _today;
  late double _watts;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _cost = widget.args.startCostRm;
    _today = widget.args.startTodayRm;
    _watts = widget.args.watts;
    _timer = Timer.periodic(_tick, (_) => _onTick());
  }

  void _onTick() {
    if (!mounted) return;
    setState(() {
      final base = widget.args.watts;
      if (base > 5 && widget.demoMode) {
        _watts = (base * (0.95 + _rng.nextDouble() * 0.1)).clamp(0, base * 1.3);
      } else {
        _watts = base;
      }
      final delta =
          (_watts / 1000) * (_tick.inMilliseconds / 3600000) * _rateRmPerKwh;
      _cost += delta;
      _today += delta;
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _submitLabel(String kind, {String? device}) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await _api.labelAppliance(
        appliance: widget.args.name,
        kind: kind,
        device: device,
      );
    } catch (_) {
      // Best-effort: offline keeps the confirmation (session-local).
    }
    if (!mounted) return;
    final what = switch (kind) {
      'device' => 'Saved as "${device ?? ''}"',
      'multiple' => 'Marked as multiple devices',
      'unsure' => 'Marked as not sure',
      _ => 'Saved',
    };
    messenger.showSnackBar(
      SnackBar(content: Text('$what - WattsEye will remember this.')),
    );
  }

  void _showLabelSheet({required bool unknown}) {
    final controller = TextEditingController();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            8,
            20,
            20 + MediaQuery.of(sheetContext).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                unknown
                    ? 'Identify this load'
                    : 'Correct "${widget.args.name}"',
                style: Theme.of(sheetContext).textTheme.titleMedium,
              ),
              const SizedBox(height: 4),
              Text(
                'Your answer trains the signature library so WattsEye recognises it next time.',
                style: Theme.of(sheetContext).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: controller,
                autofocus: true,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  labelText: 'What is it?',
                  hintText: 'e.g. Rice cooker',
                  border: OutlineInputBorder(),
                ),
                onSubmitted: (v) {
                  if (v.trim().isEmpty) return;
                  Navigator.pop(sheetContext);
                  _submitLabel('device', device: v.trim());
                },
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () {
                    final v = controller.text.trim();
                    if (v.isEmpty) return;
                    Navigator.pop(sheetContext);
                    _submitLabel('device', device: v);
                  },
                  child: const Text('Save this device'),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () {
                        Navigator.pop(sheetContext);
                        _submitLabel('multiple');
                      },
                      child: const Text('Multiple devices'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () {
                        Navigator.pop(sheetContext);
                        _submitLabel('unsure');
                      },
                      child: const Text('Not sure'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final accent = widget.args.accent;
    final kwh = _cost / _rateRmPerKwh;
    return Scaffold(
      appBar: AppBar(title: Text(widget.args.name)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  flex: 4,
                  child: Container(
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    padding: const EdgeInsets.all(18),
                    child: Center(
                      child: SvgPicture.asset(
                        widget.args.svgAsset,
                        width: 104,
                        colorFilter: ColorFilter.mode(accent, BlendMode.srcIn),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 20),
                Expanded(
                  flex: 6,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Overline('COST THIS MONTH'),
                      const SizedBox(height: 8),
                      FlipNumber(
                        'RM ${_cost.toStringAsFixed(6)}',
                        style: Theme.of(
                          context,
                        ).textTheme.displayMedium!.copyWith(color: accent),
                      ),
                      const SizedBox(height: 6),
                      FlipNumber(
                        'RM ${_today.toStringAsFixed(2)} today',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.text,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Icon(Icons.bolt, size: 18, color: accent),
                          const SizedBox(width: 6),
                          Text(
                            '${_watts.round()} W now',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          InfoCard(
            color: AppTheme.background,
            child: Column(
              children: [
                _statRow('Source', switch (widget.args.kind) {
                  ApplianceKind.measured => 'Measured - dedicated CT clamp',
                  ApplianceKind.estimated => 'Estimated - NILM model',
                  ApplianceKind.unknown => 'Signature library - unmatched',
                }),
                _statRow('Energy this month', '${kwh.toStringAsFixed(1)} kWh'),
                _statRow(
                  'Reading',
                  widget.demoMode ? 'Simulated (Demo)' : 'Live sensor',
                ),
              ],
            ),
          ),
          _coachLink(),
          const SizedBox(height: 16),
          _actionArea(),
        ],
      ),
    );
  }

  Widget _coachLink() {
    final key = widget.args.coachKey;
    final hint = widget.args.coachHint;
    if (key == null || hint == null) return const SizedBox.shrink();
    final color = widget.args.kind == ApplianceKind.measured
        ? AppTheme.red
        : AppTheme.amber;
    return Column(
      children: [
        const SizedBox(height: 16),
        InfoCard(
          accentColor: color,
          child: Row(
            children: [
              Icon(Icons.lightbulb_outline, color: color, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      hint,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        color: AppTheme.text,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'See the fix in Coach',
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                  ],
                ),
              ),
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  widget.onOpenCoach(key);
                },
                child: const Text('See Coach'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _statRow(String k, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(k, style: Theme.of(context).textTheme.bodySmall),
          Flexible(
            child: Text(
              v,
              textAlign: TextAlign.right,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                color: AppTheme.text,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionArea() {
    switch (widget.args.kind) {
      case ApplianceKind.measured:
        return const InfoCard(
          child: Row(
            children: [
              Icon(Icons.verified_outlined, color: AppTheme.green),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Measured directly on its own clamp - nothing to label or correct.',
                ),
              ),
            ],
          ),
        );
      case ApplianceKind.estimated:
        return InfoCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Estimated by the NILM model. If this looks wrong, correct it and WattsEye will learn.',
                style: TextStyle(color: AppTheme.text),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => _showLabelSheet(unknown: false),
                  icon: const Icon(Icons.flag_outlined),
                  label: const Text('Flag as wrong'),
                ),
              ),
            ],
          ),
        );
      case ApplianceKind.unknown:
        final conf = widget.args.guessConfidence;
        final guess = widget.args.guessName;
        final pct = conf == null ? null : (conf * 100).round();
        return InfoCard(
          accentColor: AppTheme.amber,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Overline('UNIDENTIFIED LOAD'),
              const SizedBox(height: 10),
              ..._hintRows(),
              const SizedBox(height: 6),
              if (conf != null && conf >= 0.9 && guess != null) ...[
                // High confidence: auto-identified, but keep it correctable.
                Text(
                  'Auto-identified as $guess ($pct%)',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: AppTheme.text,
                  ),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: () => _showLabelSheet(unknown: true),
                    child: Text('Not a $guess? Fix it'),
                  ),
                ),
              ] else if (conf != null && conf >= 0.5 && guess != null) ...[
                // Ask band: surface the guess for one-tap confirm.
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.amber.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.auto_awesome,
                        size: 18,
                        color: AppTheme.amber,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Looks like a $guess ($pct% match)',
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: AppTheme.text,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton(
                        onPressed: () => _submitLabel('device', device: guess),
                        child: Text('Yes, $guess'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => _showLabelSheet(unknown: true),
                        child: const Text("No, it's..."),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                _multipleUnsureRow(),
              ] else ...[
                // No prior match: we can't honestly name a never-seen load, so
                // we don't guess - we ask, and learn it for next time.
                const Text(
                  "Not matched to anything WattsEye knows yet. Tell us what it is and it'll recognise this next time.",
                  style: TextStyle(color: AppTheme.text),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => _showLabelSheet(unknown: true),
                    icon: const Icon(Icons.edit_outlined),
                    label: const Text('Identify device'),
                  ),
                ),
                const SizedBox(height: 8),
                _multipleUnsureRow(),
              ],
            ],
          ),
        );
    }
  }

  Widget _multipleUnsureRow() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: () => _submitLabel('multiple'),
            child: const Text('Multiple devices'),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: OutlinedButton(
            onPressed: () => _submitLabel('unsure'),
            child: const Text('Not sure'),
          ),
        ),
      ],
    );
  }

  List<Widget> _hintRows() {
    final a = widget.args;
    return [
      if (a.detectedMinsAgo != null)
        _hint(Icons.schedule, 'Detected ${a.detectedMinsAgo} min ago'),
      _hint(
        Icons.bolt,
        '~${_watts.round()} W${a.drawShape != null ? ' - ${a.drawShape}' : ''}',
      ),
      if (a.recurrence != null) _hint(Icons.event_repeat, a.recurrence!),
    ];
  }

  Widget _hint(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 15, color: AppTheme.muted),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text, style: Theme.of(context).textTheme.bodySmall),
          ),
        ],
      ),
    );
  }
}
