"""
simulacao_computacional.py — Simulação computacional, integração matemática e gráficos
(Arquivo padronizado da entrega - Seção 6.2 do PDF).

Execução:
    python simulacao_computacional.py

Comportamento:
  1. Executa todas as simulações numéricas (balanço energético e SoC de 3 sols,
     integração numérica por Trapézio e Simpson vs integral analítica, média de
     função, filtragem de sensor por convolução e controle térmico PID vs On/Off)
     e o modelo de regressão linear do Habitat Alfa;
  2. Se a biblioteca Matplotlib estiver instalada, gera automaticamente 4 gráficos
     em alta resolução dentro da pasta 'graficos_ou_imagens/'. Caso Matplotlib não
     esteja instalada no ambiente do avaliador, o script continua funcionando
     normalmente no terminal (tratamento com try/except ImportError).
"""
from sifsm.config import PASTA_GRAFICOS
from sifsm.regressao import executar_modelagem, formatar_relatorio
from sifsm.simulacao import (
    CENARIOS_PADRAO,
    ParametrosEnergia,
    relatorio_simulacao,
    simular_bateria_24_ciclos,
    simular_controle,
    simular_energia,
    simular_sensor_temperatura,
)


def gerar_graficos():
    """Gera e salva os gráficos científicos do projeto em graficos_ou_imagens/."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # backend sem janela gráfica (funciona em qualquer terminal)
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[Aviso] Matplotlib não está instalado neste ambiente Python.")
        print("Os resultados numéricos acima estão completos. Para regerar os PNGs:")
        print("    pip install matplotlib && python simulacao_computacional.py")
        return []

    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    arquivos_gerados = []
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})

    # ------------------------------------------------------------------
    # Gráfico 1: Balanço Energético e Estado de Carga (SoC) em 3 Sols
    # ------------------------------------------------------------------
    param = ParametrosEnergia()
    resultados = [simular_energia(c, param) for c in CENARIOS_PADRAO]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    r_norm = resultados[0]
    ax1.plot(r_norm["tempos"], r_norm["geracao"], color="#f59e0b", lw=2, label="Geração Solar - Céu Limpo (kW)")
    ax1.plot(resultados[1]["tempos"], resultados[1]["geracao"], color="#d97706", lw=1.6, ls="--",
             label="Geração Solar - Tempestade de Poeira (kW)")
    ax1.plot(r_norm["tempos"], r_norm["carga"], color="#2563eb", lw=2, label="Demanda Nominal da Colônia (kW)")
    ax1.fill_between(r_norm["tempos"], r_norm["geracao"], alpha=0.15, color="#f59e0b")
    ax1.set_ylabel("Potência (kW)")
    ax1.set_title("Aurora Siger — Balanço Energético (Integral da Potência) e Estado de Carga (3 Sols)")
    ax1.legend(loc="upper right", fontsize=8.5)

    cores = ["#16a34a", "#dc2626", "#2563eb"]
    for r, cor in zip(resultados, cores):
        ax2.plot(r["tempos"], r["soc"], lw=2.2, color=cor,
                 label=f"{r['cenario']} (SoC mín: {r['soc_min_pct']:.1f}%)")
    ax2.axhline(20.0, color="#991b1b", ls=":", lw=1.5, label="Limiar Crítico de Bateria (20%)")
    ax2.set_xlabel("Tempo acumulado (horas — 3 sols marcianos ≈ 74 h)")
    ax2.set_ylabel("Estado de Carga — SoC (%)")
    ax2.set_ylim(-3, 105)
    ax2.legend(loc="lower left", fontsize=8.5)

    fig.tight_layout()
    arq1 = PASTA_GRAFICOS / "01_balanco_energia_soc.png"
    fig.savefig(arq1, dpi=160)
    plt.close(fig)
    arquivos_gerados.append(arq1)

    # ------------------------------------------------------------------
    # Gráfico 2: Convolução Discreta (Filtro de Média Móvel em Sensor)
    # ------------------------------------------------------------------
    s = simular_sensor_temperatura()
    fig, ax = plt.subplots(figsize=(9.5, 4.5))
    ax.plot(s["tempos"], s["medido"], color="#94a3b8", lw=1.0, marker=".", ms=4, alpha=0.8,
            label=f"Leitura Bruta c/ Ruído (RMSE = {s['rmse_medido']:.2f} °C)")
    ax.plot(s["tempos"], s["real"], color="#0f172a", lw=2.0, ls="--", label="Temperatura Real Externa (°C)")
    ax.plot(s["tempos"], s["filtrado"], color="#0284c7", lw=2.3,
            label=f"Sinal Filtrado por Convolução k={s['janela']} (RMSE = {s['rmse_filtrado']:.2f} °C)")
    ax.set_title("Filtragem de Ruído em Sensor Marciano por Convolução Discreta 1D")
    ax.set_xlabel("Tempo em 1 Sol Marciano (horas)")
    ax.set_ylabel("Temperatura Externa (°C)")
    ax.legend()
    fig.tight_layout()
    arq2 = PASTA_GRAFICOS / "02_convolucao_sensor_temperatura.png"
    fig.savefig(arq2, dpi=160)
    plt.close(fig)
    arquivos_gerados.append(arq2)

    # ------------------------------------------------------------------
    # Gráfico 3: Controle Térmico PID (Derivada + Integral) vs Liga/Desliga
    # ------------------------------------------------------------------
    pid = simular_controle("PID")
    onoff = simular_controle("LIGA/DESLIGA")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.5, 6.5), sharex=True)
    ax1.plot(onoff["tempos"], onoff["temperaturas"], color="#f97316", lw=1.4, alpha=0.85,
             label=f"Liga/Desliga (erro médio: {onoff['erro_medio_c']:.2f} °C)")
    ax1.plot(pid["tempos"], pid["temperaturas"], color="#059669", lw=2.2,
             label=f"Controle PID (erro médio: {pid['erro_medio_c']:.2f} °C)")
    ax1.axhline(pid["setpoint"], color="#1e293b", ls="--", lw=1.3, label="Setpoint Habitat (21,0 °C)")
    ax1.set_ylabel("Temperatura Interna (°C)")
    ax1.set_title("Controle Térmico do Habitat Alfa: Malha PID Contínua vs Termostato Liga/Desliga")
    ax1.legend(loc="lower right")

    ax2.plot(onoff["tempos"], onoff["potencias"], color="#fdba74", lw=1.0, alpha=0.8,
             label=f"Potência Liga/Desliga ({onoff['comutacoes']} comutações | {onoff['energia_kwh']:.1f} kWh)")
    ax2.plot(pid["tempos"], pid["potencias"], color="#047857", lw=2.2,
             label=f"Potência PID Contínua ({pid['comutacoes']} comutações | {pid['energia_kwh']:.1f} kWh)")
    ax2.set_xlabel("Tempo em 1 Sol Marciano (horas)")
    ax2.set_ylabel("Aquecedor (kW)")
    ax2.legend(loc="lower right")
    fig.tight_layout()
    arq3 = PASTA_GRAFICOS / "03_controle_pid_vs_onoff.png"
    fig.savefig(arq3, dpi=160)
    plt.close(fig)
    arquivos_gerados.append(arq3)

    # ------------------------------------------------------------------
    # Gráfico 4: Modelagem Linear (Consumo vs Temperatura e Real vs Previsto)
    # ------------------------------------------------------------------
    reg = executar_modelagem()
    dados = reg["dados"]
    teste = reg["teste"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

    temps = [d["temperatura_externa_c"] for d in dados]
    cons = [d["consumo_habitat_kwh"] for d in dados]
    trips = [d["tripulantes_ativos"] for d in dados]
    sc = ax1.scatter(temps, cons, c=trips, cmap="viridis", alpha=0.85, edgecolors="k", linewidths=0.4)
    t_lin = [min(temps), max(temps)]
    ax1.plot(t_lin, reg["simples"].prever([[t] for t in t_lin]), color="#dc2626", lw=2.2,
             label=f"Regressão Simples (R²={reg['aval_simples']['R2']:.3f})")
    ax1.set_title("Consumo do Habitat vs Temperatura Externa")
    ax1.set_xlabel("Temperatura Externa Média (°C)")
    ax1.set_ylabel("Consumo Diário Habitat (kWh/sol)")
    cbar = fig.colorbar(sc, ax=ax1)
    cbar.set_label("Tripulantes Ativos")
    ax1.legend(loc="upper right", fontsize=8.5)

    y_real = [d["consumo_habitat_kwh"] for d in teste]
    x_teste = [[d["temperatura_externa_c"], d["tripulantes_ativos"]] for d in teste]
    y_prev = reg["multipla"].prever(x_teste)
    ax2.scatter(y_real, y_prev, color="#2563eb", alpha=0.85, edgecolors="k", linewidths=0.5)
    lim_min, lim_max = min(y_real + y_prev) - 5, max(y_real + y_prev) + 5
    ax2.plot([lim_min, lim_max], [lim_min, lim_max], "k--", lw=1.4, label="Previsão Perfeita (y = ŷ)")
    ax2.set_xlim(lim_min, lim_max)
    ax2.set_ylim(lim_min, lim_max)
    ax2.set_title(f"Modelo Linear Múltiplo no Conjunto de Teste (R²={reg['aval_multipla']['R2']:.3f})")
    ax2.set_xlabel("Consumo Real Observado (kWh/sol)")
    ax2.set_ylabel("Consumo Previsto pelo Modelo (kWh/sol)")
    ax2.legend()

    fig.tight_layout()
    arq4 = PASTA_GRAFICOS / "04_regressao_linear_habitat.png"
    fig.savefig(arq4, dpi=160)
    plt.close(fig)
    arquivos_gerados.append(arq4)

    # ------------------------------------------------------------------
    # Gráfico 5: Bateria em 24 Ciclos Horários + Integração numpy.trapz
    # ------------------------------------------------------------------
    c24_limpo = simular_bateria_24_ciclos(fator_poeira=1.0, fator_consumo=1.0)
    c24_poeira = simular_bateria_24_ciclos(fator_poeira=0.35, fator_consumo=0.50)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.8), sharex=True)
    ciclos = c24_limpo["ciclos"]
    ax1.step(ciclos, c24_limpo["geracao"], where="mid", color="#f59e0b", lw=2.2,
             label=f"Geração Solar (∫ trapz = {c24_limpo['energia_gerada_kwh']:.0f} kWh)")
    ax1.step(ciclos, c24_limpo["consumo"], where="mid", color="#2563eb", lw=2.2,
             label=f"Consumo Colônia (∫ trapz = {c24_limpo['energia_consumida_kwh']:.0f} kWh)")
    ax1.fill_between(ciclos, c24_limpo["consumo"], c24_limpo["geracao"],
                     where=[g >= c for g, c in zip(c24_limpo["geracao"], c24_limpo["consumo"])],
                     interpolate=True, color="#22c55e", alpha=0.22, label="Saldo Positivo (Carregando)")
    ax1.fill_between(ciclos, c24_limpo["consumo"], c24_limpo["geracao"],
                     where=[g <= c for g, c in zip(c24_limpo["geracao"], c24_limpo["consumo"])],
                     interpolate=True, color="#ef4444", alpha=0.18, label="Saldo Negativo (Descarregando)")
    ax1.set_ylabel("Potência (kW)")
    ax1.set_title(f"Simulação da Bateria em 24 Ciclos Horários — Integração via {c24_limpo['metodo_integracao']}")
    ax1.legend(loc="upper right", fontsize=8.5)

    ax2.plot(ciclos, c24_limpo["soc"], marker="o", ms=4.5, lw=2.2, color="#16a34a",
             label=f"SoC Céu Limpo (final: {c24_limpo['soc_final_pct']:.1f}%)")
    ax2.plot(ciclos, c24_poeira["soc"], marker="s", ms=4.0, lw=2.0, color="#2563eb", ls="--",
             label=f"SoC Tempestade + Modo Econômico 50% (final: {c24_poeira['soc_final_pct']:.1f}%)")
    ax2.axhline(20.0, color="#991b1b", ls=":", lw=1.5, label="Reserva Crítica (20%)")
    ax2.set_xticks(range(0, 25, 2))
    ax2.set_xlabel("Ciclo Horário (0 a 24 horas)")
    ax2.set_ylabel("Estado de Carga — SoC (%)")
    ax2.set_ylim(0, 105)
    ax2.legend(loc="lower right", fontsize=8.5)

    fig.tight_layout()
    arq5 = PASTA_GRAFICOS / "05_bateria_24_ciclos_trapz.png"
    fig.savefig(arq5, dpi=160)
    plt.close(fig)
    arquivos_gerados.append(arq5)

    return arquivos_gerados


def main():
    print("=" * 76)
    print("  SIMULAÇÃO COMPUTACIONAL, INTEGRAÇÃO MATEMÁTICA E MODELAGEM LINEAR")
    print("=" * 76)
    print(relatorio_simulacao())
    print("\n" + "=" * 76)
    print(formatar_relatorio(executar_modelagem()))
    gerados = gerar_graficos()
    if gerados:
        print("\nGráficos gerados com sucesso em 'graficos_ou_imagens/':")
        for caminho in gerados:
            print(f"  * {caminho.name}")


if __name__ == "__main__":
    main()
