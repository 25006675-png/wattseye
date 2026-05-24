import 'package:flutter/material.dart';

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
  late List<CoachCardState> _cards;
  DashboardSnapshot? _dashboard;
  IntegrationStatus? _integrations;
  PhoneConnectionStatus? _phones;
  bool _backendOnline = false;
  String _connectionLabel = 'Demo data';

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
        _api.getCoachCards(),
        _api.getIntegrationStatus(),
        _api.getPhones(),
      ]);
      final dashboard = results[0] as DashboardSnapshot;
      final coachCards = results[1] as List<Map<String, dynamic>>;
      final integrations = results[2] as IntegrationStatus;
      final phones = results[3] as PhoneConnectionStatus;
      if (!mounted) return;
      setState(() {
        _dashboard = dashboard;
        _cards = coachCards.map(_coachCardFromApi).toList();
        _integrations = integrations;
        _phones = phones;
        _backendOnline = true;
        _connectionLabel = 'Live Pi';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _backendOnline = false;
        _connectionLabel = 'Demo data';
      });
    }
  }

  Future<void> _pairPhone(String code, String phoneName) async {
    if (!_backendOnline) {
      _snack(context, 'Start the backend before pairing a phone');
      return;
    }
    try {
      final phones = await _api.pairPhone(code: code, phoneName: phoneName);
      if (!mounted) return;
      setState(() => _phones = phones);
      _snack(context, '$phoneName connected');
    } catch (_) {
      if (mounted) _snack(context, 'Pairing failed - check the 6-digit code');
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
          _whatsAppStatusMessage(result.reason),
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
        coachCards: _cards,
        backendOnline: _backendOnline,
        onRefresh: _refreshBackendData,
        onSendWhatsApp: _sendWhatsAppAlert,
        onOpenCoach: _openCoachCard,
      ),
      CoachPage(
        cards: _cards,
        onRefresh: _refreshBackendData,
        onCardTap: _openCoachCard,
        onAction: _markAction,
      ),
      BillPage(
        touPreview: _touPreview,
        onTogglePreview: () => setState(() => _touPreview = !_touPreview),
        onOpenCoach: _openCoachCard,
      ),
      const HistoryPage(),
      ProfilePage(
        integrations: _integrations,
        phones: _phones,
        backendOnline: _backendOnline,
        onPairPhone: _pairPhone,
        onRefresh: _refreshBackendData,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(titles[_selectedIndex]),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: ChipLabel(
                text: _connectionLabel,
                color: _backendOnline ? AppTheme.green : AppTheme.amber,
              ),
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

class DashboardPage extends StatelessWidget {
  const DashboardPage({
    super.key,
    required this.dashboard,
    required this.coachCards,
    required this.backendOnline,
    required this.onRefresh,
    required this.onSendWhatsApp,
    required this.onOpenCoach,
  });

  final DashboardSnapshot? dashboard;
  final List<CoachCardState> coachCards;
  final bool backendOnline;
  final Future<void> Function() onRefresh;
  final Future<void> Function(String keyName) onSendWhatsApp;
  final ValueChanged<String> onOpenCoach;

  @override
  Widget build(BuildContext context) {
    final snapshot = dashboard;
    final topCard = coachCards.isEmpty ? null : coachCards.first.data;
    final appliances = snapshot?.activeAppliances ?? const <ActiveAppliance>[];
    final livePowerW = snapshot?.livePowerW ?? 1420;
    final todayCost = snapshot == null
        ? 'RM4.97'
        : 'RM${snapshot.todayCostRm.toStringAsFixed(2)}';
    final projectedBill = snapshot == null
        ? 'RM149'
        : 'RM${snapshot.projectedBillRm.round()}';
    final occupancy = snapshot == null
        ? 'Away'
        : _titleCase(snapshot.occupancyState);

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          PageHeader(
            subtitle: backendOnline
                ? 'Live from backend - ${_timeLabel(snapshot?.timestamp)}'
                : 'Backend offline - showing demo data',
          ),
          const SizedBox(height: 12),
          LivePowerCard(watts: livePowerW),
          const SizedBox(height: 12),
          MetricGrid(
            metrics: [
              MetricData(
                'Today cost',
                todayCost,
                Icons.payments_outlined,
                AppTheme.green,
              ),
              MetricData(
                'Projected bill',
                projectedBill,
                Icons.trending_up_outlined,
                AppTheme.primary,
              ),
              MetricData(
                'Appliances on',
                appliances.isEmpty ? '4' : appliances.length.toString(),
                Icons.sensors_outlined,
                AppTheme.amber,
              ),
              MetricData(
                'Occupancy',
                occupancy,
                Icons.directions_walk_outlined,
                AppTheme.muted,
              ),
            ],
          ),
          const SizedBox(height: 12),
          InfoCard(
            accentColor: AppTheme.red,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Overline('HIGH PRIORITY'),
                const SizedBox(height: 4),
                Text(
                  topCard?.headline ?? 'AC running in an empty room',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  topCard?.impact ??
                      'Measured AC load is 900W for 25 minutes with no occupancy. Estimated avoidable cost is RM0.12 so far at your current band.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilledButton.icon(
                      onPressed: () =>
                          _snack(context, 'AC turn-off command sent'),
                      icon: const Icon(Icons.power_settings_new, size: 18),
                      label: const Text('Turn off'),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.red,
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () =>
                          onSendWhatsApp(topCard?.keyName ?? 'left_on_empty'),
                      icon: const Icon(Icons.chat_outlined, size: 18),
                      label: const Text('WhatsApp'),
                    ),
                    TextButton(
                      onPressed: () =>
                          onOpenCoach(topCard?.keyName ?? 'left_on_empty'),
                      child: const Text('Coach detail'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Active appliances'),
          const SizedBox(height: 8),
          ..._applianceTiles(appliances),
          const SizedBox(height: 8),
          StatusLine(
            text: backendOnline
                ? 'Backend connected at ${_apiBaseLabel()}. Pull to refresh.'
                : 'Connect the Pi backend at ${_apiBaseLabel()} to replace demo data.',
          ),
        ],
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
                    ).textTheme.titleLarge?.copyWith(fontSize: 36),
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

class CoachPage extends StatelessWidget {
  const CoachPage({
    super.key,
    required this.cards,
    required this.onRefresh,
    required this.onCardTap,
    required this.onAction,
  });

  final List<CoachCardState> cards;
  final Future<void> Function() onRefresh;
  final ValueChanged<String> onCardTap;
  final Future<void> Function(String keyName, InsightAction action) onAction;

  @override
  Widget build(BuildContext context) {
    final surfaced = cards.take(2).toList();
    final rest = cards.skip(2).toList();
    final potential = cards
        .fold<double>(0, (sum, card) => sum + card.data.rmMonthly)
        .round();

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          PageHeader(
            subtitle:
                '${cards.length} active insights - Potential RM $potential/month - Already saved RM 2.72',
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: const [
              FamilyFilterChip(label: 'Waste', color: AppTheme.wasteBorder),
              FamilyFilterChip(label: 'Tariff', color: AppTheme.tariffBorder),
              FamilyFilterChip(
                label: 'Forecast',
                color: AppTheme.forecastBorder,
              ),
              FamilyFilterChip(label: 'Context', color: AppTheme.contextBorder),
              FamilyFilterChip(label: 'Capital', color: AppTheme.capitalBorder),
            ],
          ),
          const SizedBox(height: 16),
          const SectionLabel('Top recommendations now'),
          const SizedBox(height: 8),
          for (final card in surfaced)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: RecommendationCard(
                card: card,
                surfaced: true,
                onTap: () => onCardTap(card.data.keyName),
              ),
            ),
          const SectionLabel('More insights'),
          const SizedBox(height: 8),
          for (final card in rest)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: RecommendationCard(
                card: card,
                onTap: () => onCardTap(card.data.keyName),
              ),
            ),
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
                    ChipLabel(text: data.confidence, color: AppTheme.primary),
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

class BillPage extends StatelessWidget {
  const BillPage({
    super.key,
    required this.touPreview,
    required this.onTogglePreview,
    required this.onOpenCoach,
  });

  final bool touPreview;
  final VoidCallback onTogglePreview;
  final ValueChanged<String> onOpenCoach;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {},
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          const PageHeader(
            subtitle: 'TNB RP4 projection from current household pattern',
          ),
          const SizedBox(height: 12),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ChipLabel(
                  text: touPreview
                      ? 'TNB RP4 - Previewing ToU'
                      : 'TNB RP4 - Standard',
                  color: AppTheme.primary,
                ),
                const SizedBox(height: 8),
                Text(
                  touPreview ? 'RM143.80' : 'RM149.18',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontSize: 36),
                ),
                Text(
                  touPreview
                      ? '460 kWh projected - 31.26 sen/kWh effective'
                      : '460 kWh projected - 32.43 sen/kWh effective',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                const BillLine(
                  'Generation',
                  '460 kWh * 27.03 sen/kWh',
                  'RM124.34',
                ),
                const BillLine('Capacity', '460 kWh * 4.55 sen/kWh', 'RM20.93'),
                const BillLine('Network', '460 kWh * 12.85 sen/kWh', 'RM59.11'),
                const BillLine(
                  'Energy Efficiency Incentive',
                  'Rebate, band 451-500 kWh -12.00 sen/kWh',
                  '- RM55.20',
                  positive: true,
                ),
                const BillLine(
                  'AFA',
                  'Waived under 600 kWh - current rate +0.00 sen/kWh',
                  'waived',
                ),
                const BillLine(
                  'Retail charge',
                  'Waived under 600 kWh - normally RM10.00/month',
                  'waived',
                ),
                const Divider(),
                BillLine(
                  'Projected total',
                  'TNB RP4 standard schedule, your usage pattern',
                  touPreview ? 'RM143.80' : 'RM149.18',
                  strong: true,
                ),
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
                  children: const [
                    Expanded(
                      child: PlanPanel(
                        label: 'Standard',
                        amount: 'RM149.18',
                        detail: '32.43 sen/kWh',
                      ),
                    ),
                    SizedBox(width: 8),
                    Expanded(
                      child: PlanPanel(
                        label: 'Time-of-Use',
                        amount: 'RM143.80',
                        detail: '31.26 sen/kWh',
                        recommended: true,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: const [
                    ChipLabel(
                      text: 'ToU cheaper by RM5.38/month',
                      color: AppTheme.green,
                    ),
                    ChipLabel(
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
          const SectionLabel('Energy Efficiency Incentive band'),
          const SizedBox(height: 8),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'You are at 460 kWh projected this month. The EEI rebate decreases as you cross each band.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                const LinearProgressIndicator(
                  value: 0.46,
                  minHeight: 10,
                  color: AppTheme.green,
                  backgroundColor: AppTheme.divider,
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text(
                      '0 kWh',
                      style: TextStyle(fontSize: 11, color: AppTheme.muted),
                    ),
                    Text(
                      '460 kWh - 12 sen',
                      style: TextStyle(fontSize: 11, color: AppTheme.muted),
                    ),
                    Text(
                      '1000 kWh',
                      style: TextStyle(fontSize: 11, color: AppTheme.muted),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: const [
                    ChipLabel(
                      text: 'Drop to 450 kWh: save RM1.15',
                      color: AppTheme.green,
                    ),
                    ChipLabel(
                      text: 'Cross 500 kWh: rebate drops',
                      color: AppTheme.amber,
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
                SettingsRow(label: 'Source data', value: 'tnb_tariff.py'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class HistoryPage extends StatelessWidget {
  const HistoryPage({super.key});

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {},
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: const [
          PageHeader(subtitle: 'Bill trend, appliance cost, and waste history'),
          SizedBox(height: 12),
          InfoCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MetricGrid(
                  metrics: [
                    MetricData(
                      'Month to date',
                      'RM82.30',
                      Icons.calendar_month_outlined,
                      AppTheme.primary,
                    ),
                    MetricData(
                      'Projected bill',
                      'RM149',
                      Icons.trending_up_outlined,
                      AppTheme.amber,
                    ),
                  ],
                ),
                SizedBox(height: 16),
                StackedBars(),
                SizedBox(height: 8),
                ChartLegend(),
              ],
            ),
          ),
          SizedBox(height: 16),
          SectionLabel('Appliance breakdown'),
          SizedBox(height: 8),
          InfoCard(
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
          SizedBox(height: 16),
          SectionLabel('Waste history'),
          SizedBox(height: 8),
          InfoCard(
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
    required this.phones,
    required this.backendOnline,
    required this.onPairPhone,
    required this.onRefresh,
  });

  final IntegrationStatus? integrations;
  final PhoneConnectionStatus? phones;
  final bool backendOnline;
  final Future<void> Function(String code, String phoneName) onPairPhone;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final status = integrations;
    final phoneStatus = phones;
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
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
                    fontWeight: FontWeight.w800,
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
        ProfileSection(
          title: 'Connected phones',
          rows: [
            SettingsRow(
              label: 'Pairing code',
              value: backendOnline
                  ? (phoneStatus?.pairingCode.isEmpty ?? true
                        ? 'Loading'
                        : phoneStatus!.pairingCode)
                  : 'Backend offline',
            ),
            SettingsRow(
              label: 'API address',
              value: _apiBaseLabel(),
            ),
            SettingsRow(
              label: 'Connected phones',
              value: phoneStatus == null
                  ? 'Unknown'
                  : '${phoneStatus.phones.length}',
            ),
            SettingsRow(
              label: 'Pair this phone',
              actionable: true,
              onTap: () => _showPairPhoneSheet(context, onPairPhone),
            ),
            for (final phone in phoneStatus?.phones ?? const <PairedPhone>[])
              SettingsRow(
                label: phone.phoneName,
                value: 'Last seen ${_dateLabel(phone.lastSeen)}',
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
      ),
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
  });

  final Widget child;
  final Color? accentColor;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: accentColor == null
            ? null
            : Border(left: BorderSide(color: accentColor!, width: 4)),
        boxShadow: [
          BoxShadow(
            blurRadius: 3,
            offset: const Offset(0, 1),
            color: Colors.black.withValues(alpha: 0.04),
          ),
        ],
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
    required this.icon,
    required this.name,
    required this.source,
    required this.watts,
    required this.cost,
    required this.chips,
    required this.chipColor,
  });

  final IconData icon;
  final String name;
  final String source;
  final String watts;
  final String cost;
  final List<String> chips;
  final Color chipColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InfoCard(
        child: Column(
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: chipColor.withValues(alpha: 0.12),
                  child: Icon(icon, color: chipColor),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        source,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(watts, style: Theme.of(context).textTheme.titleMedium),
                    Text(cost, style: Theme.of(context).textTheme.labelSmall),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final chip in chips)
                    ChipLabel(text: chip, color: chipColor),
                ],
              ),
            ),
          ],
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
  });

  final CoachCardState card;
  final VoidCallback onTap;
  final bool surfaced;

  @override
  Widget build(BuildContext context) {
    final data = card.data;
    final acted = card.action == InsightAction.done;
    final dismissed = card.action == InsightAction.dismissed;
    return Opacity(
      opacity: dismissed ? 0.55 : 1,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: InfoCard(
          accentColor: familyBorder(data.family),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      '#${data.id} - ${data.headline}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        decoration: dismissed
                            ? TextDecoration.lineThrough
                            : null,
                      ),
                      maxLines: surfaced ? 2 : 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Wrap(
                    spacing: 4,
                    children: [
                      FamilyTag(family: data.family),
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
                        color: acted ? AppTheme.green : AppTheme.primary,
                        fontWeight: FontWeight.w700,
                        decoration: acted ? TextDecoration.lineThrough : null,
                      ),
                    ),
                  ),
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

class StackedBars extends StatelessWidget {
  const StackedBars({super.key});

  static const bars = [
    [42.0, 52.0, 8.0, 40.0],
    [48.0, 55.0, 10.0, 35.0],
    [58.0, 62.0, 6.0, 32.0],
    [46.0, 48.0, 12.0, 40.0],
    [72.0, 68.0, 9.0, 23.0],
    [64.0, 57.0, 16.0, 27.0],
    [82.0, 61.0, 14.0, 25.0],
  ];

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
                      children: [
                        Expanded(
                          flex: bar[1].round(),
                          child: Container(color: AppTheme.primary),
                        ),
                        Expanded(
                          flex: bar[2].round(),
                          child: Container(color: AppTheme.amber),
                        ),
                        Expanded(
                          flex: bar[3].round(),
                          child: Container(color: AppTheme.muted),
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

class ChartLegend extends StatelessWidget {
  const ChartLegend({super.key});

  @override
  Widget build(BuildContext context) {
    return const Wrap(
      spacing: 12,
      children: [
        LegendItem(label: 'AC', color: AppTheme.primary),
        LegendItem(label: 'Other', color: AppTheme.muted),
        LegendItem(label: 'Unknown', color: AppTheme.amber),
      ],
    );
  }
}

class LegendItem extends StatelessWidget {
  const LegendItem({super.key, required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(label, style: Theme.of(context).textTheme.labelSmall),
      ],
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
        borderRadius: BorderRadius.circular(4),
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

class FamilyFilterChip extends StatelessWidget {
  const FamilyFilterChip({super.key, required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      avatar: Icon(Icons.circle, size: 10, color: color),
      label: Text(label),
      onPressed: () => _snack(context, '$label filter ready for API data'),
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
        borderRadius: BorderRadius.circular(4),
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

String _whatsAppStatusMessage(String reason) {
  if (reason.isEmpty) return 'WhatsApp not sent';
  if (reason.startsWith('already pushed this archetype')) {
    return 'Already sent recently - try again later';
  }
  if (reason.startsWith('global rate-limit')) {
    return 'WhatsApp alert paused to avoid spam';
  }
  if (reason == 'archetype not in PUSH_ARCHETYPES') {
    return 'This coach card is app-only, not a WhatsApp alert';
  }
  if (reason == 'dry_run') return 'WhatsApp preview generated';
  if (reason == 'missing twilio env vars') {
    return 'Add Twilio env vars, then restart backend';
  }
  if (reason.startsWith('twilio error:')) return 'WhatsApp provider error';
  return 'WhatsApp not sent';
}

void _showPairPhoneSheet(
  BuildContext context,
  Future<void> Function(String code, String phoneName) onPairPhone,
) {
  final codeController = TextEditingController();
  final nameController = TextEditingController(text: 'My phone');
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) {
      return Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Pair this phone',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: nameController,
              decoration: const InputDecoration(
                labelText: 'Phone name',
                prefixIcon: Icon(Icons.phone_android_outlined),
              ),
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: codeController,
              decoration: const InputDecoration(
                labelText: '6-digit pairing code',
                prefixIcon: Icon(Icons.password_outlined),
              ),
              keyboardType: TextInputType.number,
              textInputAction: TextInputAction.done,
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () async {
                  await onPairPhone(
                    codeController.text.trim(),
                    nameController.text.trim().isEmpty
                        ? 'My phone'
                        : nameController.text.trim(),
                  );
                  if (context.mounted) Navigator.of(context).pop();
                },
                icon: const Icon(Icons.link_outlined),
                label: const Text('Connect phone'),
              ),
            ),
          ],
        ),
      );
    },
  ).whenComplete(() {
    codeController.dispose();
    nameController.dispose();
  });
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
      saving: json['saving_text']?.toString().replaceFirst(
            RegExp(r'^Expected saving:\s*'),
            '',
          ) ??
          'RM ${monthly.toStringAsFixed(0)}/month',
      effort: json['effort_text']?.toString() ?? 'Low effort',
      confidence: json['confidence_label']?.toString() ?? 'Medium confidence',
      rmMonthly: monthly,
      why: _jsonStringList(json['why_lines']),
      math: _jsonStringList(json['math_lines']),
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

String _titleCase(String value) {
  if (value.isEmpty) return value;
  return value[0].toUpperCase() + value.substring(1).toLowerCase();
}

String _timeLabel(DateTime? timestamp) {
  if (timestamp == null) return 'synced just now';
  final hour = timestamp.hour.toString().padLeft(2, '0');
  final minute = timestamp.minute.toString().padLeft(2, '0');
  return 'synced $hour:$minute';
}

String _dateLabel(DateTime? timestamp) {
  if (timestamp == null) return 'unknown';
  final month = timestamp.month.toString().padLeft(2, '0');
  final day = timestamp.day.toString().padLeft(2, '0');
  final hour = timestamp.hour.toString().padLeft(2, '0');
  final minute = timestamp.minute.toString().padLeft(2, '0');
  return '$day/$month $hour:$minute';
}

String _apiBaseLabel() => defaultApiBaseUrl;

String _readyLabel(bool? ready) {
  return switch (ready) {
    true => 'Ready',
    false => 'Missing',
    null => 'Unknown',
  };
}

IconData _applianceIcon(String name) {
  return switch (name.toLowerCase()) {
    'ac' || 'air_conditioner' => Icons.ac_unit,
    'fridge' || 'refrigerator' => Icons.kitchen_outlined,
    'kettle' => Icons.coffee_maker_outlined,
    'washer' || 'washing_machine' => Icons.local_laundry_service_outlined,
    _ => Icons.sensors_outlined,
  };
}

String _applianceName(String name) {
  return switch (name.toLowerCase()) {
    'ac' => 'Air Conditioner',
    'fridge' => 'Fridge',
    'washing_machine' => 'Washing Machine',
    _ => name
        .split('_')
        .where((part) => part.isNotEmpty)
        .map(_titleCase)
        .join(' '),
  };
}

List<Widget> _applianceTiles(List<ActiveAppliance> appliances) {
  if (appliances.isEmpty) return _demoApplianceTiles();
  return [
    for (final appliance in appliances)
      ApplianceTile(
        icon: _applianceIcon(appliance.name),
        name: _applianceName(appliance.name),
        source: appliance.name == 'ac'
            ? 'Measured - Dedicated CT clamp'
            : 'Estimated - NILM',
        watts: '${appliance.watts.round()}W',
        cost: 'RM${appliance.todayRm.toStringAsFixed(2)} today',
        chips: [
          '${appliance.todayKwh.toStringAsFixed(1)} kWh today',
          appliance.watts > 0 ? 'Active now' : 'Idle',
        ],
        chipColor: appliance.watts > 800 ? AppTheme.red : AppTheme.green,
      ),
  ];
}

List<Widget> _demoApplianceTiles() {
  return const [
    ApplianceTile(
      icon: Icons.ac_unit,
      name: 'Air Conditioner',
      source: 'Measured - Dedicated CT clamp',
      watts: '900W',
      cost: 'RM43.20 this month',
      chips: ['Empty room', 'RM3.50/month if repeated daily'],
      chipColor: AppTheme.red,
    ),
    ApplianceTile(
      icon: Icons.kitchen_outlined,
      name: 'Fridge',
      source: 'Estimated - NILM',
      watts: '118W',
      cost: '~RM18.70 this month',
      chips: ['Health watch', 'UK-DALE baseline'],
      chipColor: AppTheme.amber,
    ),
    ApplianceTile(
      icon: Icons.rice_bowl_outlined,
      name: 'Unknown load',
      source: 'Signature library - 88% match',
      watts: '620W',
      cost: 'RM0.20/h at current band',
      chips: ['Likely rice cooker', 'Tap to confirm'],
      chipColor: AppTheme.amber,
    ),
    ApplianceTile(
      icon: Icons.coffee_maker_outlined,
      name: 'Kettle',
      source: 'Estimated - NILM',
      watts: '0W',
      cost: '~RM4.70 this month',
      chips: ['Normal routine'],
      chipColor: AppTheme.green,
    ),
  ];
}
