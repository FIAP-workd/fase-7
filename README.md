# SIFSM — Sistema Integrado de Futuro Sustentável em Marte (Aurora Siger)

Protótipo integrador desenvolvido para a **Fase 7 de Ciência da Computação (FIAP)**, conectando banco de dados relacional (CRUD + tratamento de erros), lógica booleana e circuitos embarcados (Arduino/Tinkercad), estruturas de dados clássicas, simulação computacional com cálculo integral e controle PID, modelagem linear para tomada de decisão, sistemas multiagentes de IA com guardrails/RAG, arquitetura computacional heterogênea e cidadania digital/sustentabilidade.

## Integrantes do Grupo

| Nome | RM |
| João Victor Viana Feitosa | 573217 |
| Luis Gustavo Ribeiro Andrade | 569147 |
| Matheus de Carvalho Teodoro | 572855 |
| Pedro César Fernandes de Brito | 573965 |
| Gabriel Coutinho Barcelos | 573211 |

---

## 1. Arquivos Presentes na Entrega (Padrão Seção 6.2)

```
projeto_sifsm/
├── codigo_fonte.py              # Arquivo principal (menu interativo completo + modo --demo)
├── script_banco.sql             # Criação das 5 tabelas SQL, carga inicial e versão Oracle
├── dados_aurora_siger.csv       # Base histórica simulada (120 sols) usada na regressão linear
├── circuito_logico.png          # Esquemático das portas lógicas, pinagem Arduino e tabela-verdade
├── link_tinkercad.txt           # Instruções/link Tinkercad Circuits
├── circuito_arduino.ino         # Código C++ para Arduino UNO no Tinkercad
├── simulacao_computacional.py   # Script standalone de simulação, integrais, regressão e gráficos
├── relatorio_tecnico.md         # Relatório técnico completo conectado ao protótipo
├── README.md                    # Este guia de instalação, arquivos e execução
├── link_video.txt               # Link do vídeo de até 5 min no YouTube ("Não listado")
├── graficos_ou_imagens/         # Gráficos PNG da simulação, regressão e arquitetura IA
│   ├── 01_balanco_energia_soc.png
│   ├── 02_convolucao_sensor_temperatura.png
│   ├── 03_controle_pid_vs_onoff.png
│   ├── 04_regressao_linear_habitat.png
│   ├── 05_bateria_24_ciclos_trapz.png
│   └── 06_diagrama_multiagentes_ia.png
├── sifsm/                       # Módulos internos organizados por disciplina da Fase 7
│   ├── config.py                # Caminhos e constantes físicas de Marte
│   ├── banco.py                 # Conexão SQLite, CRUD parametrizado, try/except/else/finally
│   ├── logica.py                # Regras booleanas, portas AND/OR/NOT e tabelas-verdade
│   ├── estruturas.py            # Fila FIFO, Pilha LIFO, Tabela Hash, Heap Binário e Grafo
│   ├── simulacao.py             # Balanço energético, Trapézio/Simpson, convolução e PID
│   ├── regressao.py             # Análise exploratória, Mínimos Quadrados, MAE/RMSE/R² e VIF
│   ├── agentes.py               # Multiagentes IA, Triador, Handoff, Tools, Guardrails, RAG, Tracing
│   ├── arquitetura.py           # MCU/CPU/GPU/NPU/TPU, modelo Roofline e benchmark de memória
│   └── analise.py               # Fluxo integrado da colônia, pseudonimização e sustentabilidade
└── ferramentas/                 # Utilitários auxiliares de geração de dados, diagrama e testes
    ├── gerar_dados.py
    ├── gerar_diagrama_circuito.py
    └── testar_sistema.py
```

---

## 2. Requisitos e Dependências

- **Python 3.10 ou superior**;
- **Zero dependências obrigatórias para executar o sistema principal (`codigo_fonte.py`)**: todo o núcleo utiliza apenas a biblioteca padrão do Python (`sqlite3`, `csv`, `math`, `collections`, `heapq`, `hashlib`, `re`, `dataclasses`, `pathlib`), garantindo execução imediata na correção!
- **Dependências opcionais (`numpy` e `matplotlib`)**: quando instaladas, a simulação de 24 ciclos usa `numpy.trapz` / `numpy.trapezoid` diretamente e `simulacao_computacional.py` regera os arquivos `.png` da pasta `graficos_ou_imagens/` (todos os gráficos já vão gerados na entrega; caso não estejam instaladas, o sistema faz *fallback* transparente para Python puro):
  ```bash
  pip install numpy matplotlib
  ```

---

## 3. Como Executar o Projeto

Abra o terminal na pasta `projeto_sifsm` e escolha um dos modos abaixo:

### A) Menu Interativo Completo (Recomendado para explorar e demonstrar)
```bash
python codigo_fonte.py
```
> Na primeira execução, o arquivo `aurora_siger.db` é criado e populado automaticamente a partir de `script_banco.sql`. Use as opções `1` a `9` do menu para navegar por todas as funcionalidades!

### B) Demonstração Automatizada de Ponta a Ponta (Sem digitação manual)
```bash
python codigo_fonte.py --demo
```
> Executa automaticamente em banco em memória todas as etapas: CRUD + tratamento de erro de integridade + Pilha Desfazer, circuito lógico e tabela-verdade, simulação e integrais, regressão linear, arquitetura heterogênea, bloqueio de Guardrail de IA e análise integrada de sustentabilidade.

### C) Simulação Computacional e Geração dos Gráficos
```bash
python simulacao_computacional.py
```

### D) Suíte de Testes Automatizados
```bash
python ferramentas/testar_sistema.py
```
