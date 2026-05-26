/*
 * WattsEye IR-learn sketch — capture your real AC remote's codes
 * ==============================================================
 * One-time bench tool (HARDWARE_CONNECTION.md §12). Point your AC remote at the
 * VS1838B receiver and press OFF; this prints the protocol + code so you can
 * reproduce it from the ESP32 (set USE_REAL_AC + the matching ir_*.h there).
 *
 * For long inverter-AC frames that don't decode to a simple protocol, the raw
 * timing buffer is printed instead — copy it into an IRsend sendRaw() call.
 *
 * Library: IRremote (z3t0/Armin Joachimsmeyer), v3.x+  — Library Manager.
 * Board:   Arduino Nano / Uno (or ESP32 — change RECV_PIN to a valid GPIO).
 *
 * Wiring (VS1838B, facing the dome: OUT - GND - VCC):
 *   OUT -> D2     GND -> GND     VCC -> 5V (or 3.3V)
 */

#include <IRremote.hpp>

const int RECV_PIN = 2;   // VS1838B OUT

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }
  IrReceiver.begin(RECV_PIN, ENABLE_LED_FEEDBACK);
  Serial.println(F("WattsEye IR learn — point the AC remote and press OFF..."));
}

void loop() {
  if (IrReceiver.decode()) {
    Serial.println(F("---- captured ----"));
    // Human-readable summary: protocol, address, command, raw value.
    IrReceiver.printIRResultShort(&Serial);
    Serial.println();

    // If the protocol is UNKNOWN (common for inverter ACs), dump the raw
    // timing so it can be replayed with IRsend::sendRaw().
    if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
      Serial.println(F("Protocol UNKNOWN — raw timing (microseconds):"));
      IrReceiver.printIRResultRawFormatted(&Serial, true);
      Serial.println();
    }

    IrReceiver.resume();   // ready for the next button press
  }
}
