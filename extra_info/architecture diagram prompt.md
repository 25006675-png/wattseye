Asset type: final cleaned WattsEye expected full-system architecture diagram for project assets, 16:9 landscape,
professional technical infographic
Primary request: Regenerate a clean final version of the WattsEye architecture diagram. Fix the previous ambiguity: Twilio
must connect only to WhatsApp delivery/replies, and ReportLab must connect only to PDF Report generation. The diagram
should represent the expected full system, not only current implementation.
Style/medium: crisp modern vector-like technical architecture infographic rendered as a polished bitmap. Light background,
graphite text, restrained professional colors, subtle borders, clean arrows, high legibility. Stylized non-official tech
icons/badges only, not exact trademark logos.
Composition/framing: Four clear zones. Left = home sensing and optional precision layer. Center = Raspberry Pi edge
backend / coach engine. Right = cloud and external services. Bottom = user outputs. Keep compact and professional, roughly
16-18 grouped visual elements.
ZONE 1, LEFT CLUSTER title: "HOME SENSING RIG"
Inside one bordered hardware group, include mini-icons and exact labels:
"Main CT Clamp"
"AC CT Clamp"
"Voltage Sensor"
"ADS1115"
"ESP32 + mmWave"
"IR Blaster"
Show "MQTT" near the Pi-to-ESP32/IR control link.
Add a small secondary optional badge connected toward the Pi data layer: "Optional Smart Plugs" with sublabel "exact plug-
load validation". It must look optional and secondary, not core.
ZONE 2, CENTER LARGE CLUSTER title: "RASPBERRY PI EDGE / COACH ENGINE"
Inside the Pi cluster, show compact modules in a clean vertical/horizontal flow:
"1 Hz Power Stream"
"Local DB + Offline Queue"
"PyTorch NILM" with small "Py" badge
"ML Stack" with tiny tiles: "ELECTRIcity", "K-Means", "Isolation Forest", "Linear Regression"
"5-Layer Coach Pipeline" with chain: "Correlator -> Quantifier -> Templates -> Ranker -> Cards"
"TNB RP4 Tariff" as amber badge
"FastAPI JSON API" as blue API badge
"ReportLab PDF" as red PDF-generation badge
ZONE 3, RIGHT title: "CLOUD + EXTERNAL SERVICES"
Show a distinct green database/auth node labeled exactly: "Supabase Auth + DB"
Tiny sublabel: "login, device ownership, sync"
Connect it bidirectionally to "Local DB + Offline Queue" with label "offline-first sync".
Connect it to "Flutter App" with label "login + synced history".
Show external APIs as stylized icon labels, not large boxes:
"Gemini" blue-purple star, connected from Coach Pipeline with label "message rephrase only".
"Twilio" red communication icon, connected from Coach Pipeline with label "alert send / reply webhook".
"Open-Meteo" sun/cloud icon, connected to Coach Pipeline with label "weather context".
"ST Registry" shield icon, connected to Coach Pipeline with label "efficiency lookup".
ZONE 4, BOTTOM title: "USER EXPERIENCE"
Show three destination icons:
"Flutter App" with Flutter-style blue badge; sublabels "Dashboard", "Coach", "Bill", "History", "Profile".
"WhatsApp" with green speech bubble.
"PDF Report" with document icon.
CRITICAL ARROW REQUIREMENTS:
Hardware cluster -> Pi cluster arrow labeled "sensor readings / 1 Hz".
Optional Smart Plugs -> Local DB + Offline Queue arrow labeled "MQTT / local API".
Pi -> ESP32 + IR path labeled "MQTT command -> IR off".
Local DB + Offline Queue <-> Supabase Auth + DB labeled "offline-first sync".
FastAPI JSON API -> Flutter App labeled "LAN/cloud JSON".
Supabase Auth + DB -> Flutter App labeled "login + synced history".
Coach Pipeline -> Twilio -> WhatsApp, in a clearly chained path. The arrow from Twilio to WhatsApp must be labeled exactly
No arrow or label should imply PDF replies or Twilio PDF generation.
Visual hierarchy:
Make "Two CT clamps + Pi local brain" the dominant story. Supabase is cloud login/sync, not the live control loop. Optional
smart plugs are secondary. Twilio is only the WhatsApp bridge. ReportLab is only the PDF generation path.
Color palette: light neutral background; teal/green for sensing and Supabase; blue for Pi/API/Flutter; purple for Gemini;
red for Twilio and PDF; amber for tariff/weather; dark graphite text.
Constraints: all labels must be spelled exactly and legibly. Avoid dense tables, paragraphs, tiny unreadable text,
overlapping arrows, dark background, exact official logos, watermark, decorative gradient blobs, 3D perspective.