# Smart Insight Engines

This folder separates WattsEye's saving-focused logic into small engines.

```text
tnb_tariff.py
  TNB RP4 Domestic tariff model (1 July 2025 - 31 December 2027).
  Implements standard and Time-of-Use schedules, EEI rebate table,
  AFA surcharge, retail-charge waiver, and standard-vs-ToU comparison.

cost_engine.py
  Calculates event cost and monthly repeat cost using tnb_tariff for
  band-aware RM pricing.

occupancy_engine.py
  Detects high-power empty-room waste.

health_engine.py
  Flags appliance behavior changes such as long fridge cycles.

insight_orchestrator.py
  Combines routine, cost, occupancy, and health results into one dashboard object.
```

Quick tariff sanity check:

```powershell
python .\ML\insights\tnb_tariff.py
```

This prints a side-by-side bill breakdown for 180, 350, 650, 1200, and 1800 kWh/month, plus a standard-vs-ToU comparison for a 350 kWh home with 35% peak usage.

## TNB RP4 tariff sources

All constants in `tnb_tariff.py` come from TNB's published Regulatory Period 4 (RP4) Domestic tariff, effective 1 July 2025 – 31 December 2027. Refresh the AFA constant each TNB billing cycle from the official sources below.

Primary (TNB official):
- [myTNB tariff page](https://www.mytnb.com.my/tariff)
- [TNB press release, 30 June 2025 (PDF)](https://www.tnb.com.my/assets/newsclip/30062025a.pdf)
- [New electricity schedule, 23 June 2025 (PDF)](https://www.tnb.com.my/assets/newsclip/23062025a.pdf)
- [SEDA NEM calculator tariff reference (PDF)](https://services.seda.gov.my/nemcalculator/tnb-tariff-rates.pdf)

Secondary (rate breakdowns and EEI table):
- [Soyacincau — TNB Electricity Bill changes starting July 2025](https://soyacincau.com/2025/06/21/tnb-domestic-electricity-tariff-structure-july-2025-impact-changes/)
- [paultan.org — TNB new electricity tariff calculation from July 2025](https://paultan.org/2025/06/21/tnb-new-electricity-tariff-calculation-from-july-2025/)
- [SolarSunYield — Normal vs Time of Use 2026 guide (EEI rebate table)](https://www.solarsunyield.com/latestnews/nid/169869/)
- [Sunview — Homeowner's Guide to the new tariff](https://www.sunview.com.my/r/your-complete-homeowners-guide-to-tnbs-new-electricity-tariff-effective-1-july-2025)
- [Solaroo — TNB's New Electricity Tariff (1 July 2025)](https://solaroo.com/tnbs-new-electricity-tariff-effective-1-july-2025/)

Time-of-Use specifics:
- [Soyacincau — How to apply for TNB ToU (2025-07-05)](https://soyacincau.com/2025/07/05/tnb-time-of-use-off-peak-electricity-tariff-scheme-how-to-apply/)
- [Malay Mail — Is TNB's Time of Use plan right for you?](https://www.malaymail.com/news/malaysia/2025/07/15/is-tnbs-time-of-use-plan-right-for-you-it-depends-on-when-you-use-power/183461)

The routine baseline still lives in `../routine/routine_engine.py`.

Run examples:

```powershell
python .\ML\insights\insight_orchestrator.py --appliance ac --power-watts 900 --duration-minutes 25 --occupied false --timestamp "2026-05-20 14:20" --source direct_ct --confidence 0.99

python .\ML\insights\insight_orchestrator.py --appliance kettle --power-watts 1800 --duration-minutes 4 --occupied true --timestamp "2026-05-20 07:10" --source nilm --confidence 0.96

python .\ML\insights\insight_orchestrator.py --appliance fridge --power-watts 190 --duration-minutes 45 --occupied false --timestamp "2026-05-20 13:00" --source nilm --confidence 0.86
```

The dashboard should consume the orchestrator output, not each engine directly.
