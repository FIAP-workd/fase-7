"""
gerar_diagrama_circuito.py — Gera os diagramas visuais do circuito lógico (circuito_logico.png)
e da arquitetura multiagentes de IA (graficos_ou_imagens/06_diagrama_multiagentes_ia.png).
"""
from pathlib import Path


def _caixa(ax, x, y, w, h, texto, cor="#e0f2fe", borda="#0284c7", fontsize=9.2):
    from matplotlib.patches import FancyBboxPatch
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12", facecolor=cor, edgecolor=borda, lw=1.8)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color="#0f172a")


def desenhar_circuito():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    raiz = Path(__file__).resolve().parent.parent
    destino = raiz / "circuito_logico.png"

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(12.2, 8.6), gridspec_kw={"height_ratios": [1.45, 1.0]})
    fig.patch.set_facecolor("#f8fafc")

    ax = ax_top
    ax.set_facecolor("#ffffff")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    ax.set_title(
        "SIFSM (Aurora Siger) — Circuito Lógico Tinkercad (2 Entradas + AND + LED) e Expansão Embarcada",
        fontsize=12.0, fontweight="bold", pad=10, color="#0f172a",
    )

    # Moldura destacando o núcleo de 2 entradas + AND + LED (Parte 2)
    destaque = FancyBboxPatch((0.15, 3.35), 8.65, 2.85, boxstyle="round,pad=0.12",
                              facecolor="#f0f9ff", edgecolor="#0284c7", lw=1.4, ls="--")
    ax.add_patch(destaque)
    ax.text(4.45, 6.03, "Núcleo Tinkercad (2 Entradas + Porta AND 74HC08 + LED):  ALERTA = A AND B",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color="#0369a1")

    # Entradas A e B + Porta AND + LED direto (2 entradas)
    _caixa(ax, 0.35, 4.85, 2.45, 0.85, "Chave / Sensor A\nConsumo > Limite", "#fef3c7", "#d97706")
    _caixa(ax, 0.35, 3.60, 2.45, 0.85, "Chave B\nMódulo Crítico = 1", "#fef3c7", "#d97706")
    _caixa(ax, 3.65, 4.15, 1.85, 1.15, "Porta AND\n(CI 74HC08)\nS₁ = A · B", "#dbeafe", "#1d4ed8")
    _caixa(ax, 6.30, 4.85, 2.30, 0.90, "Saída Tinkercad Base\nResistor 220 Ω + LED\n(Acende se A=1 e B=1)", "#fee2e2", "#b91c1c", 8.6)

    # Expansão opcional C (CO2 > 1000 ppm) + Porta OR
    _caixa(ax, 0.35, 1.95, 2.45, 0.85, "Sensor C (Expansão)\nCO2 > 1000 ppm", "#fee2e2", "#dc2626")
    _caixa(ax, 6.30, 2.35, 2.30, 1.10, "Porta OR (74HC32)\nExpansão Segurança\nS₂ = (A · B) + C", "#ede9fe", "#6d28d9", 8.8)
    _caixa(ax, 9.35, 2.35, 2.35, 1.10, "Atuadores Arduino\nLED Vermelho (D8)\n+ Buzzer (D9)", "#fee2e2", "#b91c1c", 8.8)

    fios = [
        ([2.92, 3.65], [5.28, 4.95]),
        ([2.92, 3.65], [4.02, 4.50]),
        ([5.62, 6.30], [4.90, 5.30]),
        ([5.62, 6.30], [4.50, 3.10]),
        ([2.92, 6.30], [2.38, 2.70]),
        ([8.72, 9.35], [2.90, 2.90]),
    ]
    for xs, ys in fios:
        ax.plot(xs, ys, color="#1e293b", lw=2.1)

    # Circuito secundário de irrigação
    _caixa(ax, 0.35, 0.35, 2.45, 0.95, "Estufa Ares (A1 / D5)\nA=Ativa, B=Umid<55%\nC=Bateria<20%", "#dcfce7", "#15803d", 8.5)
    _caixa(ax, 3.65, 0.35, 1.85, 0.95, "Porta NOT (74HC04)\nC' (Bat. OK)", "#f1f5f9", "#475569", 8.8)
    _caixa(ax, 6.30, 0.35, 2.30, 0.95, "Porta AND\nIRRIGAR = A · B · C'", "#dbeafe", "#1d4ed8", 8.8)
    _caixa(ax, 9.35, 0.35, 2.35, 0.95, "Válvula / LED Verde\n(Pino D10)", "#dcfce7", "#15803d", 8.8)
    for xs, ys in [([2.92, 3.65], [0.82, 0.82]), ([5.62, 6.30], [0.82, 0.82]), ([8.72, 9.35], [0.82, 0.82])]:
        ax.plot(xs, ys, color="#15803d", lw=2.0, ls="--")

    # Painel inferior: duas tabelas-verdade lado a lado (2 entradas e 3 entradas)
    ax_bot.axis("off")
    tv2 = [["0", "0", "0 (Apagado)"], ["0", "1", "0 (Apagado)"], ["1", "0", "0 (Apagado)"], ["1", "1", "1 (ALERTA LED)"]]
    t_esq = ax_bot.table(
        cellText=tv2,
        colLabels=["A (Consumo Alto)", "B (Mód. Crítico)", "S₁ = A AND B"],
        bbox=[0.02, 0.12, 0.38, 0.74], cellLoc="center",
    )
    t_esq.auto_set_font_size(False)
    t_esq.set_fontsize(9)
    for (r, c), cel in t_esq.get_celld().items():
        if r == 0:
            cel.set_facecolor("#0369a1")
            cel.set_text_props(color="white", fontweight="bold")
        else:
            cel.set_facecolor("#fef2f2" if r == 4 else "#f0fdf4")

    tv3 = []
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                s = (a & b) | c
                tv3.append([str(a), str(b), str(c), str(a & b), str(s)])
    t_dir = ax_bot.table(
        cellText=tv3,
        colLabels=["A", "B", "C (CO2)", "A · B", "S₂ = (A·B)+C"],
        bbox=[0.44, 0.05, 0.54, 0.85], cellLoc="center",
    )
    t_dir.auto_set_font_size(False)
    t_dir.set_fontsize(8.6)
    for (r, c), cel in t_dir.get_celld().items():
        if r == 0:
            cel.set_facecolor("#1e293b")
            cel.set_text_props(color="white", fontweight="bold")
        else:
            cel.set_facecolor("#fef2f2" if tv3[r - 1][4] == "1" else "#f0fdf4")

    ax_bot.set_title("Tabelas-Verdade: Circuito Base 2 Entradas (Esquerda) e Circuito Integrado 3 Entradas (Direita)",
                     fontsize=10.8, fontweight="bold", color="#0f172a")

    fig.tight_layout()
    fig.savefig(destino, dpi=160)
    plt.close(fig)
    return destino


def desenhar_diagrama_ia():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raiz = Path(__file__).resolve().parent.parent
    pasta = raiz / "graficos_ou_imagens"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "06_diagrama_multiagentes_ia.png"

    fig, ax = plt.subplots(figsize=(12, 6.6))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#ffffff")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.0)
    ax.axis("off")
    ax.set_title(
        "SIFSM — Arquitetura Conceitual e Simulada do Sistema Multiagentes de IA",
        fontsize=12.5, fontweight="bold", pad=10, color="#0f172a",
    )

    _caixa(ax, 0.3, 4.9, 2.3, 1.2, "Solicitação / Fila FIFO\nde Chamados\n(Pseudônimo TRP-XXXX)", "#fef3c7", "#d97706", 8.8)
    _caixa(ax, 3.1, 4.9, 2.3, 1.2, "Guardrail de Entrada\nBloqueia ações letais,\ninjection e vazamentos", "#fee2e2", "#dc2626", 8.8)
    _caixa(ax, 5.9, 4.9, 2.4, 1.2, "Agente Triador\nClassifica intenção e\nfaz Handoff (Sessão)", "#dbeafe", "#1d4ed8", 9.0)

    # Especialistas
    _caixa(ax, 0.6, 2.55, 2.4, 1.25, "Agente de Energia\nSimulação SoC, Bissecção\ne Regressão Linear", "#dcfce7", "#15803d", 8.6)
    _caixa(ax, 3.5, 2.55, 2.4, 1.25, "Agente Ambiental\nSensores CO2/Umidade\ne Regras Booleanas", "#dcfce7", "#15803d", 8.6)
    _caixa(ax, 6.4, 2.55, 2.4, 1.25, "Agente de Manutenção\nFila FIFO, Módulos e\nGrafo Smart Grid", "#dcfce7", "#15803d", 8.6)
    _caixa(ax, 9.2, 2.55, 2.4, 1.25, "Agente de Dados\nInventário SQLite e\nGovernança", "#dcfce7", "#15803d", 8.6)

    # RAG + Banco + Guardrail de saída
    _caixa(ax, 1.4, 0.45, 4.2, 1.15, "Tools Determinísticas + RAG Simulado\nConsulta SQLite (modulos/leituras) +\nNormas Oficiais [DOC-01..04] (TF-IDF)", "#ede9fe", "#6d28d9", 8.7)
    _caixa(ax, 6.5, 0.45, 4.7, 1.15, "Guardrail de Saída + Human-in-the-Loop\nTracing auditável (ms) + Oficial de Controle\nHUMANO valida toda decisão crítica!", "#fee2e2", "#b91c1c", 8.7)

    setas = [
        (2.72, 5.5, 3.08, 5.5),
        (5.52, 5.5, 5.88, 5.5),
        (6.5, 4.85, 1.8, 3.92),
        (6.9, 4.85, 4.7, 3.92),
        (7.3, 4.85, 7.6, 3.92),
        (7.7, 4.85, 10.4, 3.92),
        (3.5, 2.5, 3.5, 1.72),
        (7.6, 2.5, 8.5, 1.72),
        (5.72, 1.02, 6.45, 1.02),
    ]
    for x1, y1, x2, y2 in setas:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.9, color="#1e293b"))

    # Handoff entre especialistas
    ax.annotate("", xy=(3.05, 3.18), xytext=(3.48, 3.18),
                arrowprops=dict(arrowstyle="<->", lw=1.8, ls="--", color="#0284c7"))
    ax.text(3.26, 3.98, "Handoff", ha="center", fontsize=8.2, color="#0369a1", fontweight="bold")

    fig.tight_layout()
    fig.savefig(destino, dpi=160)
    plt.close(fig)
    return destino


if __name__ == "__main__":
    c1 = desenhar_circuito()
    c2 = desenhar_diagrama_ia()
    print(f"Diagramas salvos em:\n  * {c1}\n  * {c2}")
