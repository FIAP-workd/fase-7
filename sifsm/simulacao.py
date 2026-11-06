"""
simulacao.py — Simulação computacional e integração matemática
(Modelagem Matemática e Computacional + Soluções em Energias Renováveis).

Implementado só com a biblioteca padrão (math, random) para rodar em qualquer máquina.
Os gráficos ficam em simulacao_computacional.py (Matplotlib).

Modelos:
 1. Balanço energético da colônia e ESTADO DE CARGA (SoC) da bateria:
        E(t) = E(0) + ∫ [P_ger(t) - P_carga(t)] dt        (integral = energia acumulada)
        SoC(t) = 100 · E(t) / Capacidade
 2. Integração numérica (trapézio e Simpson) comparada com a integral ANALÍTICA
    da geração solar:  ∫ Pmax·sen(π(t-t0)/D) dt  de t0 a t0+D  =  2·Pmax·D/π
 3. MÉDIA DE FUNÇÃO:  P_média = (1/T)·∫ P(t) dt
 4. CONVOLUÇÃO (média móvel) para filtrar o ruído de um sensor de temperatura.
 5. CONTROLE PID (derivada + integral) do aquecimento do habitat.
 6. Busca por BISSECÇÃO do consumo máximo seguro durante uma tempestade de poeira.
"""
import math
import random
from dataclasses import dataclass

from .config import DURACAO_SOL_H

NASCER_SOL_H = 6.2                    # hora do nascer do Sol no sol marciano
DURACAO_DIA_H = DURACAO_SOL_H / 2     # horas com Sol (~12,3 h)


# ===========================================================================
# 1. Balanço energético e estado de carga da bateria
# ===========================================================================
@dataclass
class ParametrosEnergia:
    potencia_pico_kw: float = 220.0        # potência máxima dos painéis ao meio-dia (céu limpo)
    capacidade_bateria_kwh: float = 1200.0
    soc_inicial_pct: float = 60.0
    consumo_base_kw: float = 59.0          # soma do consumo nominal dos módulos (banco)
    eficiencia_carga: float = 0.95
    eficiencia_descarga: float = 0.95


@dataclass
class Cenario:
    nome: str
    fator_poeira: float = 1.0      # 1 = céu limpo; 0.35 = tempestade de poeira (65% menos luz)
    fator_consumo: float = 1.0     # 1 = normal; 0.75 = modo econômico


CENARIOS_PADRAO = [
    Cenario("Normal"),
    Cenario("Tempestade de poeira", fator_poeira=0.35),
    Cenario("Tempestade + modo econômico (50%)", fator_poeira=0.35, fator_consumo=0.50),
]


def geracao_solar(t_h, p, fator_poeira=1.0):
    """Potência solar (kW): meia senoide entre o nascer e o pôr do Sol; zero à noite."""
    t = t_h % DURACAO_SOL_H
    if NASCER_SOL_H <= t <= NASCER_SOL_H + DURACAO_DIA_H:
        return p.potencia_pico_kw * fator_poeira * math.sin(math.pi * (t - NASCER_SOL_H) / DURACAO_DIA_H)
    return 0.0


def carga_colonia(t_h, p, fator_consumo=1.0):
    """Consumo (kW): base + pico de atividade da tripulação no meio da tarde (curva gaussiana)."""
    t = t_h % DURACAO_SOL_H
    atividade = math.exp(-((t - 14.0) / 5.0) ** 2)
    return p.consumo_base_kw * fator_consumo * (0.85 + 0.30 * atividade)


def simular_energia(cenario, p=None, sols=3, passo_h=0.05):
    """
    Integra o balanço de energia pelo método de Euler (passo a passo no tempo).
    Retorna as séries temporais e indicadores do cenário.
    """
    p = p or ParametrosEnergia()
    n_passos = int(round(sols * DURACAO_SOL_H / passo_h))
    energia = p.capacidade_bateria_kwh * p.soc_inicial_pct / 100
    tempos, soc, geracao, carga = [], [], [], []
    deficit_kwh = desperdicio_kwh = 0.0
    horas_criticas = 0.0

    for i in range(n_passos + 1):
        t = i * passo_h
        pg = geracao_solar(t, p, cenario.fator_poeira)
        pc = carga_colonia(t, p, cenario.fator_consumo)
        soc_atual = 100 * energia / p.capacidade_bateria_kwh
        tempos.append(t)
        geracao.append(pg)
        carga.append(pc)
        soc.append(soc_atual)
        if i == n_passos:
            break
        if soc_atual < 20:
            horas_criticas += passo_h
        saldo = pg - pc                                  # kW
        if saldo >= 0:                                   # sobra energia -> carrega a bateria
            energia += saldo * p.eficiencia_carga * passo_h
            if energia > p.capacidade_bateria_kwh:       # bateria cheia -> energia desperdiçada
                desperdicio_kwh += (energia - p.capacidade_bateria_kwh) / p.eficiencia_carga
                energia = p.capacidade_bateria_kwh
        else:                                            # falta energia -> descarrega
            energia += saldo / p.eficiencia_descarga * passo_h
            if energia < 0:                              # bateria vazia -> carga não atendida
                deficit_kwh += -energia * p.eficiencia_descarga
                energia = 0.0

    total_h = tempos[-1]
    energia_gerada = integrar_trapezio(geracao, passo_h)
    energia_consumida = integrar_trapezio(carga, passo_h)
    return {
        "cenario": cenario.nome,
        "tempos": tempos, "soc": soc, "geracao": geracao, "carga": carga,
        "energia_gerada_kwh": energia_gerada,
        "energia_consumida_kwh": energia_consumida,
        "potencia_media_gerada_kw": energia_gerada / total_h,      # média de função
        "potencia_media_carga_kw": energia_consumida / total_h,
        "soc_min_pct": min(soc),
        "soc_final_pct": soc[-1],
        "horas_bateria_critica": horas_criticas,
        "deficit_kwh": deficit_kwh,
        "desperdicio_kwh": desperdicio_kwh,
    }


def fator_consumo_seguro(fator_poeira, p=None, sols=3, soc_minimo=20.0, tolerancia=0.005):
    """
    Método da BISSECÇÃO: maior fator de consumo que mantém o SoC >= soc_minimo
    durante 'sols' dias com o fator de poeira informado.
    """
    p = p or ParametrosEnergia()

    def soc_min(fator):
        return simular_energia(Cenario("busca", fator_poeira, fator), p, sols, passo_h=0.1)["soc_min_pct"]

    baixo, alto = 0.05, 1.5
    if soc_min(baixo) < soc_minimo:
        return None
    if soc_min(alto) >= soc_minimo:
        return alto
    while alto - baixo > tolerancia:
        meio = (baixo + alto) / 2
        if soc_min(meio) >= soc_minimo:
            baixo = meio
        else:
            alto = meio
    return baixo


# ===========================================================================
# 2 e 3. Integração numérica x analítica e média de função
# ===========================================================================
def integrar_trapezio(valores, passo):
    """Regra do trapézio para amostras igualmente espaçadas (erro ~ h²)."""
    if len(valores) < 2:
        return 0.0
    return passo * (sum(valores) - (valores[0] + valores[-1]) / 2)


def integrar_numpy_trapz(valores, passo=1.0):
    """
    Calcula a integral numérica usando numpy.trapz (ou numpy.trapezoid no NumPy 2+),
    com fallback automático para integrar_trapezio caso o NumPy não esteja instalado.
    Retorna (valor_integral, metodo_utilizado).
    """
    try:
        import numpy as np
        fn_trapz = getattr(np, "trapz", None) or getattr(np, "trapezoid")
        nome_fn = "numpy.trapz" if hasattr(np, "trapz") else "numpy.trapezoid (NumPy 2+)"
        return float(fn_trapz(np.asarray(valores, dtype=float), dx=passo)), nome_fn
    except ImportError:
        return integrar_trapezio(valores, passo), "trapézio puro (fallback sem NumPy)"


def simular_bateria_24_ciclos(fator_poeira=1.0, fator_consumo=1.0, p=None):
    """
    Simula a bateria ao longo de 24 ciclos horários discretos (ciclos 0..24, Δt = 1 h)
    calculando geração menos consumo e a energia acumulada via numpy.trapz.
    """
    p = p or ParametrosEnergia()
    ciclos = list(range(25))  # 0 a 24 -> 24 intervalos de 1 hora
    energia_kwh = p.capacidade_bateria_kwh * p.soc_inicial_pct / 100.0
    geracao, consumo, saldo_liquido, soc = [], [], [], []

    for h in ciclos:
        pg = geracao_solar(float(h), p, fator_poeira)
        pc = carga_colonia(float(h), p, fator_consumo)
        saldo = pg - pc
        soc_atual = 100.0 * energia_kwh / p.capacidade_bateria_kwh
        geracao.append(pg)
        consumo.append(pc)
        saldo_liquido.append(saldo)
        soc.append(soc_atual)
        if h == 24:
            break
        if saldo >= 0:
            energia_kwh = min(p.capacidade_bateria_kwh, energia_kwh + saldo * p.eficiencia_carga * 1.0)
        else:
            energia_kwh = max(0.0, energia_kwh + (saldo / p.eficiencia_descarga) * 1.0)

    gerada_kwh, metodo = integrar_numpy_trapz(geracao, passo=1.0)
    consumida_kwh, _ = integrar_numpy_trapz(consumo, passo=1.0)
    saldo_kwh, _ = integrar_numpy_trapz(saldo_liquido, passo=1.0)
    return {
        "ciclos": ciclos,
        "geracao": geracao,
        "consumo": consumo,
        "saldo": saldo_liquido,
        "soc": soc,
        "energia_gerada_kwh": gerada_kwh,
        "energia_consumida_kwh": consumida_kwh,
        "saldo_acumulado_kwh": saldo_kwh,
        "soc_min_pct": min(soc),
        "soc_max_pct": max(soc),
        "soc_final_pct": soc[-1],
        "metodo_integracao": metodo,
    }


def integrar_simpson(valores, passo):
    """Regra 1/3 de Simpson (erro ~ h⁴). Se o nº de intervalos for ímpar, o último usa trapézio."""
    n = len(valores) - 1
    if n < 2:
        return integrar_trapezio(valores, passo)
    extra = 0.0
    if n % 2 == 1:
        extra = passo * (valores[-2] + valores[-1]) / 2
        valores, n = valores[:-1], n - 1
    soma = valores[0] + valores[-1] + 4 * sum(valores[1:n:2]) + 2 * sum(valores[2:n - 1:2])
    return passo / 3 * soma + extra


def energia_solar_analitica(p=None, fator_poeira=1.0):
    """Primitiva da senoide: ∫0^D Pmax·sen(πt/D) dt = 2·Pmax·D/π (kWh por sol)."""
    p = p or ParametrosEnergia()
    return 2 * p.potencia_pico_kw * fator_poeira * DURACAO_DIA_H / math.pi


def comparar_integracao(p=None, divisoes=(4, 8, 16, 64, 256)):
    """Compara trapézio e Simpson com o valor exato para várias quantidades de subintervalos."""
    p = p or ParametrosEnergia()
    exato = energia_solar_analitica(p)
    linhas = []
    for n in divisoes:
        h = DURACAO_DIA_H / n
        amostras = [geracao_solar(NASCER_SOL_H + i * h, p) for i in range(n + 1)]
        trap = integrar_trapezio(amostras, h)
        simp = integrar_simpson(amostras, h)
        linhas.append({"n": n, "trapezio": trap, "simpson": simp,
                       "erro_trap_pct": abs(trap - exato) / exato * 100,
                       "erro_simp_pct": abs(simp - exato) / exato * 100})
    return exato, linhas


# ===========================================================================
# 4. Convolução para filtrar sensores
# ===========================================================================
def temperatura_externa(t_h):
    """Temperatura externa típica de Marte (°C): ~-98 °C de madrugada, ~-28 °C à tarde."""
    return -63.0 + 35.0 * math.sin(2 * math.pi * (t_h - 9.0) / DURACAO_SOL_H)


def convolucao(sinal, kernel):
    """
    Convolução discreta 1D, modo 'same' (mesmo tamanho do sinal):
        y[i] = Σ_j x[i + j - m] · k[K-1-j]
    Nas bordas, onde o kernel "sai" do sinal, normaliza pelos pesos usados.
    """
    k, m = len(kernel), len(kernel) // 2
    saida = []
    for i in range(len(sinal)):
        acumulado = peso = 0.0
        for j in range(k):
            idx = i + j - m
            if 0 <= idx < len(sinal):
                w = kernel[k - 1 - j]
                acumulado += sinal[idx] * w
                peso += w
        saida.append(acumulado / peso if peso else 0.0)
    return saida


def rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def simular_sensor_temperatura(sols=1, passo_h=0.25, ruido=3.0, janela=5, semente=7):
    """Sensor externo com ruído gaussiano e filtro de média móvel (convolução)."""
    gerador = random.Random(semente)
    tempos = [i * passo_h for i in range(int(sols * DURACAO_SOL_H / passo_h) + 1)]
    real = [temperatura_externa(t) for t in tempos]
    medido = [v + gerador.gauss(0, ruido) for v in real]
    filtrado = convolucao(medido, [1 / janela] * janela)
    return {"tempos": tempos, "real": real, "medido": medido, "filtrado": filtrado,
            "rmse_medido": rmse(medido, real), "rmse_filtrado": rmse(filtrado, real),
            "janela": janela}


# ===========================================================================
# 5. Controle PID do aquecimento do habitat
# ===========================================================================
@dataclass
class ParametrosTermicos:
    capacidade_termica: float = 2.0    # kWh/°C — energia para aquecer o habitat em 1 °C
    ua: float = 0.15                   # kW/°C — perda de calor pelas paredes (isolamento)
    potencia_max_kw: float = 20.0      # aquecedor
    setpoint_c: float = 21.0           # temperatura desejada
    temperatura_inicial_c: float = 15.0


def simular_controle(tipo="PID", kp=15.0, ki=4.0, kd=1.0, sols=1, passo_h=0.02, termico=None):
    """
    Modelo térmico (equação diferencial):  C·dT/dt = u(t) - UA·(T - T_ext(t))
    Controladores:
      PID  : u = Kp·e + Ki·∫e dt + Kd·de/dt   (com anti-windup)
      LIGA/DESLIGA : aquecedor 100% abaixo de setpoint-0,5 °C, desligado acima de setpoint+0,5 °C
    """
    th = termico or ParametrosTermicos()
    temp = th.temperatura_inicial_c
    integral = 0.0
    erro_anterior = th.setpoint_c - temp
    ligado = True
    tempos, temps, potencias = [], [], []
    n = int(sols * DURACAO_SOL_H / passo_h)
    for i in range(n + 1):
        t = i * passo_h
        erro = th.setpoint_c - temp
        if tipo == "PID":
            integral += erro * passo_h                      # termo INTEGRAL (acumula o erro)
            derivada = (erro - erro_anterior) / passo_h     # termo DERIVATIVO (tendência do erro)
            u = kp * erro + ki * integral + kd * derivada
            u_sat = min(max(u, 0.0), th.potencia_max_kw)
            if u != u_sat:
                integral -= erro * passo_h                  # anti-windup: não acumula se saturado
            erro_anterior = erro
        else:
            if temp < th.setpoint_c - 0.5:
                ligado = True
            elif temp > th.setpoint_c + 0.5:
                ligado = False
            u_sat = th.potencia_max_kw if ligado else 0.0
        tempos.append(t)
        temps.append(temp)
        potencias.append(u_sat)
        d_temp = (u_sat - th.ua * (temp - temperatura_externa(t))) / th.capacidade_termica
        temp += d_temp * passo_h                            # integração de Euler
    inicio_regime = int(4 / passo_h)                        # avalia após 4 h (regime)
    erros = [abs(th.setpoint_c - x) for x in temps[inicio_regime:]]
    return {"tipo": tipo, "tempos": tempos, "temperaturas": temps, "potencias": potencias,
            "energia_kwh": integrar_trapezio(potencias, passo_h),
            "erro_medio_c": sum(erros) / len(erros),
            "erro_max_c": max(erros),
            "comutacoes": sum(1 for a, b in zip(potencias, potencias[1:]) if (a > 0) != (b > 0)),
            "setpoint": th.setpoint_c}


# ===========================================================================
# Relatório textual
# ===========================================================================
def relatorio_simulacao():
    p = ParametrosEnergia()
    c24 = simular_bateria_24_ciclos(p=p)
    linhas = [f"== 1. Simulação da bateria em 24 ciclos horários ({c24['metodo_integracao']}) =="]
    linhas.append(
        f"   Energia gerada (24 ciclos) = {c24['energia_gerada_kwh']:.1f} kWh | "
        f"Consumida = {c24['energia_consumida_kwh']:.1f} kWh | "
        f"Saldo acumulado = {c24['saldo_acumulado_kwh']:+.1f} kWh"
    )
    linhas.append(
        f"   Estado de Carga (SoC): inicial = {c24['soc'][0]:.1f}% -> mín = {c24['soc_min_pct']:.1f}% "
        f"-> máx = {c24['soc_max_pct']:.1f}% -> final (ciclo 24) = {c24['soc_final_pct']:.1f}%\n"
    )
    linhas.append("== 2. Balanço energético multissol (3 sols, Euler, passo 0,05 h) ==")
    linhas.append(f"{'Cenário':<35}{'Gerado':>9}{'Consumo':>9}{'SoC mín':>9}{'SoC fim':>9}"
                  f"{'Déficit':>9}{'Desperd.':>9}")
    for c in CENARIOS_PADRAO:
        r = simular_energia(c, p)
        linhas.append(f"{c.nome:<35}{r['energia_gerada_kwh']:>8.0f} {r['energia_consumida_kwh']:>8.0f}"
                      f"{r['soc_min_pct']:>8.1f}%{r['soc_final_pct']:>8.1f}%"
                      f"{r['deficit_kwh']:>8.0f} {r['desperdicio_kwh']:>8.0f}")
    linhas.append("   (energias em kWh; déficit = consumo não atendido; desperdício = sobra com bateria cheia)")
    seguro = fator_consumo_seguro(0.35, p)
    if seguro:
        linhas.append(f"   Bissecção: em tempestade, o consumo deve cair para {seguro * 100:.0f}% do normal "
                      f"(~{seguro * p.consumo_base_kw:.1f} kW de base) para manter SoC >= 20% por 3 sols.")

    exato, tabela = comparar_integracao(p)
    linhas.append("\n== 3. Integração da geração solar de um sol (céu limpo) ==")
    linhas.append(f"   Valor analítico 2·Pmax·D/π = {exato:.2f} kWh")
    linhas.append(f"   {'n':>5}{'Trapézio':>12}{'erro %':>9}{'Simpson':>12}{'erro %':>10}")
    for l in tabela:
        linhas.append(f"   {l['n']:>5}{l['trapezio']:>12.2f}{l['erro_trap_pct']:>9.4f}"
                      f"{l['simpson']:>12.2f}{l['erro_simp_pct']:>10.6f}")
    media = exato / DURACAO_SOL_H
    linhas.append(f"   Média de função: potência solar média no sol = {exato:.0f}/{DURACAO_SOL_H} = {media:.1f} kW")

    s = simular_sensor_temperatura()
    linhas.append("\n== 4. Convolução (média móvel) no sensor de temperatura externa ==")
    linhas.append(f"   Janela = {s['janela']} amostras | RMSE bruto = {s['rmse_medido']:.2f} °C | "
                  f"RMSE filtrado = {s['rmse_filtrado']:.2f} °C "
                  f"({(1 - s['rmse_filtrado'] / s['rmse_medido']) * 100:.0f}% menos ruído)")

    pid = simular_controle("PID")
    onoff = simular_controle("LIGA/DESLIGA")
    linhas.append("\n== 5. Controle de temperatura do habitat (1 sol) ==")
    for r in (pid, onoff):
        linhas.append(f"   {r['tipo']:<13} energia = {r['energia_kwh']:6.1f} kWh | erro médio = "
                      f"{r['erro_medio_c']:.2f} °C | erro máx = {r['erro_max_c']:.2f} °C | "
                      f"liga/desliga do aquecedor = {r['comutacoes']}x")
    linhas.append("   O PID ajusta a potência continuamente (sem 'trancos'); o liga/desliga gasta energia "
                  "parecida, mas comuta muitas vezes, desgastando o equipamento.")
    linhas.append("\nLimitações: modelos simplificados (sem sazonalidade, degradação da bateria, "
                  "temperatura afetando painéis ou falhas aleatórias); parâmetros ilustrativos.")
    return "\n".join(linhas)
