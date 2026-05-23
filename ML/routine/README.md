# Routine-Aware Insight Prototype

This folder contains the prototype routine-aware layer for WattsEye.

The NILM models answer:

```text
What appliance is probably running?
```

The routine engine answers:

```text
Is this usage normal for this home at this time?
```

For the demo, `demo_history.csv` is seeded household history. In a real deployment, the same columns can come from the Raspberry Pi local database after several days of logging.

Run examples:

```powershell
python .\ML\routine\routine_engine.py --appliance kettle --power-watts 1800 --duration-minutes 4 --occupied true --timestamp "2026-05-20 07:10"
python .\ML\routine\routine_engine.py --appliance kettle --power-watts 1800 --duration-minutes 4 --occupied true --timestamp "2026-05-20 03:10"
python .\ML\routine\routine_engine.py --appliance ac --power-watts 900 --duration-minutes 25 --occupied false --timestamp "2026-05-20 14:20"
```
