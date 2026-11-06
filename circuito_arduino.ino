// ============================================================================
// SIFSM - Sistema Integrado de Futuro Sustentável em Marte (Aurora Siger)
// Código Arduino UNO para simulação no Tinkercad Circuits
//
// Implementa em automação embarcada duas regras booleanas do SIFSM:
//   1) Regra Principal de Alerta Energético/Segurança:
//        ALERTA = (A && B) || C          [Álgebra: S = (A · B) + C]
//        A = Consumo acima do limite (potenciômetro A0 > 70% ou chave D2)
//        B = Módulo crítico (chave deslizante no pino D3)
//        C = Falha de segurança / CO2 > 1000 ppm (chave/botão no pino D4)
//        Saída: LED Vermelho (D8) + Buzzer Piezo (D9)
//
//   2) Regra Sustentável de Irrigação da Estufa Ares:
//        IRRIGAR = EstufaAtiva && UmidadeBaixa && (!BateriaCritica)
//        Umidade simulada no potenciômetro A1 (< 55% = baixa)
//        Bateria crítica simulada na chave D5 (HIGH = SoC < 20%)
//        Saída: LED Verde / Válvula de Gotejamento (D10)
// ============================================================================

const int PINO_POT_CONSUMO    = A0;  // Sensor analógico de potência (0..1023 -> 0..20 kW)
const int PINO_POT_UMIDADE    = A1;  // Sensor analógico de umidade da estufa (0..100%)
const int PINO_CHAVE_CRITICO  = 3;   // Entrada B: 1 = módulo crítico, 0 = não crítico
const int PINO_CHAVE_CO2_ALTO = 4;   // Entrada C: 1 = CO2 > 1000 ppm (falha segurança)
const int PINO_CHAVE_BAT_CRIT = 5;   // 1 = Bateria crítica (SoC < 20%)

const int PINO_LED_ALERTA     = 8;   // Atuador: LED vermelho (alerta crítico)
const int PINO_BUZZER         = 9;   // Atuador: Buzzer piezoelétrico
const int PINO_LED_IRRIGACAO  = 10;  // Atuador: LED verde (bomba de gotejamento)
const int PINO_LED_NORMAL     = 11;  // Indicador: operação nominal estável

void setup() {
  pinMode(PINO_CHAVE_CRITICO,  INPUT);
  pinMode(PINO_CHAVE_CO2_ALTO, INPUT);
  pinMode(PINO_CHAVE_BAT_CRIT, INPUT);

  pinMode(PINO_LED_ALERTA,    OUTPUT);
  pinMode(PINO_BUZZER,        OUTPUT);
  pinMode(PINO_LED_IRRIGACAO, OUTPUT);
  pinMode(PINO_LED_NORMAL,    OUTPUT);

  Serial.begin(9600);
  Serial.println("SIFSM Aurora Siger - Controlador Embarcado Iniciado");
}

void loop() {
  // 1. Leitura dos sensores simulados
  float consumoKw  = (analogRead(PINO_POT_CONSUMO) / 1023.0) * 20.0;
  float umidadePct = (analogRead(PINO_POT_UMIDADE) / 1023.0) * 100.0;

  bool entradaA_consumoAlto    = (consumoKw > 14.0);                 // limite de 14 kW
  bool entradaB_moduloCritico  = (digitalRead(PINO_CHAVE_CRITICO) == HIGH);
  bool entradaC_falhaSeguranca = (digitalRead(PINO_CHAVE_CO2_ALTO) == HIGH);
  bool bateriaCritica          = (digitalRead(PINO_CHAVE_BAT_CRIT) == HIGH);

  // 2. Aplicação das expressões booleanas (idênticas ao módulo Python logica.py)
  bool alertaEnergia = (entradaA_consumoAlto && entradaB_moduloCritico) || entradaC_falhaSeguranca;
  bool liberarIrrig  = (umidadePct < 55.0) && (!bateriaCritica);

  // 3. Acionamento dos atuadores
  digitalWrite(PINO_LED_ALERTA,    alertaEnergia ? HIGH : LOW);
  digitalWrite(PINO_LED_NORMAL,    alertaEnergia ? LOW  : HIGH);
  digitalWrite(PINO_LED_IRRIGACAO, liberarIrrig  ? HIGH : LOW);

  if (alertaEnergia) {
    tone(PINO_BUZZER, 1200, 150);
  } else {
    noTone(PINO_BUZZER);
  }

  // 4. Telemetria serial para auditoria
  Serial.print("Consumo(kW)="); Serial.print(consumoKw, 1);
  Serial.print(" [A=");         Serial.print(entradaA_consumoAlto);
  Serial.print(", B=");         Serial.print(entradaB_moduloCritico);
  Serial.print(", C=");         Serial.print(entradaC_falhaSeguranca);
  Serial.print("] -> ALERTA="); Serial.print(alertaEnergia);
  Serial.print(" | Umidade(%)="); Serial.print(umidadePct, 0);
  Serial.print(" BatCrit=");      Serial.print(bateriaCritica);
  Serial.print(" -> IRRIGAR=");   Serial.println(liberarIrrig);

  delay(400);
}
