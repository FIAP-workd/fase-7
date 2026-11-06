"""
config.py — Constantes e caminhos globais do SIFSM.

Centralizar configurações evita "números mágicos" espalhados pelo código.
"""
from pathlib import Path

# Pasta raiz do projeto (um nível acima deste pacote)
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

CAMINHO_BANCO = RAIZ_PROJETO / "aurora_siger.db"        # arquivo SQLite gerado na 1ª execução
CAMINHO_SCRIPT_SQL = RAIZ_PROJETO / "script_banco.sql"  # DDL + carga inicial
CAMINHO_CSV = RAIZ_PROJETO / "dados_aurora_siger.csv"   # base histórica simulada (regressão)
PASTA_GRAFICOS = RAIZ_PROJETO / "graficos_ou_imagens"

# Um dia marciano (sol) dura ~24 h 39 min 35 s
DURACAO_SOL_H = 24.66

# Número de tripulantes ativos usado nas previsões
TRIPULANTES_ATIVOS = 8

# "Sal" usado na pseudonimização da tripulação (privacidade).
# Em um sistema real ficaria fora do código (variável de ambiente / cofre de segredos).
SAL_PSEUDONIMO = "aurora-siger-fase7"
