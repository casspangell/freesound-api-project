const int numSwitches = 20;

const int switchPins[numSwitches] = {
  0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
  10, 11, 12, 13, A5, A4, A3, A2, A1, A0
};

const char letters[numSwitches] = {
  'a', 'w', 's', 'e', 'd', 'c', 'r', 'f', 't', 'g',
  'b', 'h', 'n', 'm', 'j', 'i', 'k', 'o', 'l', 'p'
};

int prevStates[numSwitches];

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < numSwitches; i++) {
    pinMode(switchPins[i], INPUT_PULLUP);
    prevStates[i] = HIGH;
  }
  Serial.println("Switch detection active.");
}

void loop() { 
  for (int i = 0; i < numSwitches; i++) {
    int state = digitalRead(switchPins[i]);

    if (state == LOW && prevStates[i] == HIGH) {
      Serial.print(letters[i]); // Send letter only (no newline)
      delay(1000); // debounce: adjust as needed
    }

    prevStates[i] = state;
  }
}
