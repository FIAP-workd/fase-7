"""
testar_sistema.py — Suíte automatizada de testes de unidade e integração do SIFSM.
Execução:  python ferramentas/testar_sistema.py
"""
from pathlib import Path
import sys
import unittest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sifsm.agentes import SessaoIA, SistemaMultiagentesAurora, processar_fila_chamados
from sifsm.analise import analisar_sustentabilidade_colonia, pseudonimizar_tripulante
from sifsm.arquitetura import benchmark_localidade_memoria, comparar_arquiteturas
from sifsm.banco import BancoAurora, ErroBanco
from sifsm.estruturas import (
    ORIGEM_ENERGIA,
    FilaAtendimento,
    FilaPrioridadeAlertas,
    PilhaHistorico,
    TabelaHash,
    buscar_sensor,
    criar_indice_sensores,
    criar_rede_padrao,
)
from sifsm.logica import REGRAS, classificar_risco, sensor_valido, tabela_verdade
from sifsm.regressao import executar_modelagem, prever_consumo
from sifsm.simulacao import (
    CENARIOS_PADRAO,
    comparar_integracao,
    fator_consumo_seguro,
    simular_bateria_24_ciclos,
    simular_controle,
    simular_energia,
    simular_sensor_temperatura,
)


class TestesSIFSM(unittest.TestCase):

    def test_01_banco_crud_erros_e_desfazer(self):
        with BancoAurora(":memory:") as db:
            self.assertEqual(len(db.listar("modulos")), 8)
            novo_id = db.inserir("modulos", {
                "nome": "Domo Teste", "tipo": "LABORATORIO",
                "critico": 0, "status": "ATIVO", "consumo_nominal_kw": 2.0,
            })
            self.assertEqual(db.obter("modulos", novo_id)["nome"], "Domo Teste")

            db.atualizar("modulos", novo_id, {"status": "MANUTENCAO"})
            self.assertEqual(db.obter("modulos", novo_id)["status"], "MANUTENCAO")

            # Desfazer UPDATE -> volta para ATIVO
            db.desfazer()
            self.assertEqual(db.obter("modulos", novo_id)["status"], "ATIVO")

            # Excluir módulo que tem sensores deve disparar ErroBanco (ON DELETE RESTRICT)
            with self.assertRaises(ErroBanco):
                db.excluir("modulos", 1)

            # Excluir módulo recém-criado e desfazer DELETE -> restaura registro!
            db.excluir("modulos", novo_id)
            self.assertIsNone(db.obter("modulos", novo_id))
            db.desfazer()
            self.assertIsNotNone(db.obter("modulos", novo_id))

    def test_02_logica_booleana_e_portas(self):
        for nome in REGRAS:
            for _, s_py, s_hw in tabela_verdade(nome):
                self.assertEqual(s_py, s_hw, f"Divergência na regra {nome}")
        self.assertTrue(sensor_valido("TEMPERATURA", -60.0))
        self.assertFalse(sensor_valido("TEMPERATURA", -300.0))
        self.assertFalse(sensor_valido("UMIDADE", "abc"))
        self.assertEqual(classificar_risco(15.2, 14.0, True)["risco"], "ALTO")
        self.assertEqual(classificar_risco(11.0, 10.0, False)["risco"], "MEDIO")
        self.assertEqual(classificar_risco(6.0, 14.0, True)["risco"], "BAIXO")

    def test_03_estruturas_de_dados(self):
        # Fila FIFO
        fila = FilaAtendimento()
        fila.enfileirar("A")
        fila.enfileirar("B")
        self.assertEqual(fila.desenfileirar(), "A")
        self.assertEqual(fila.desenfileirar(), "B")

        # Pilha LIFO
        pilha = PilhaHistorico()
        pilha.empilhar(10)
        pilha.empilhar(20)
        self.assertEqual(pilha.desempilhar(), 20)

        # Dicionário buscar_sensor + Tabela Hash c/ redimensionamento
        idx = criar_indice_sensores([{"codigo": "CNS-HAB-01", "tipo": "CONSUMO"}])
        self.assertEqual(buscar_sensor(idx, "cns-hab-01")["tipo"], "CONSUMO")
        self.assertIsNone(buscar_sensor(idx, "INEXISTENTE"))

        th = TabelaHash(capacidade=4)
        for i in range(20):
            th.inserir(f"CH-{i}", i * 10)
        self.assertEqual(len(th), 20)
        self.assertEqual(th.buscar("CH-15"), 150)
        self.assertIn("CH-0", th)
        self.assertTrue(th.remover("CH-15"))
        self.assertNotIn("CH-15", th)

        # Heap de prioridade
        heap = FilaPrioridadeAlertas()
        heap.inserir(3, "info")
        heap.inserir(1, "critico")
        heap.inserir(2, "atencao")
        self.assertEqual(heap.remover_mais_urgente(), (1, "critico"))

        # Grafo Dijkstra + pontos críticos
        rede = criar_rede_padrao()
        perda, caminho = rede.menor_caminho(ORIGEM_ENERGIA, "Módulo Médico")
        self.assertAlmostEqual(perda, 4.2, places=2)
        self.assertEqual(caminho[0], ORIGEM_ENERGIA)
        self.assertIn("Banco de Baterias", rede.pontos_criticos(ORIGEM_ENERGIA))

    def test_04_simulacao_e_integracao_matematica(self):
        c24 = simular_bateria_24_ciclos()
        self.assertEqual(len(c24["ciclos"]), 25)
        self.assertGreater(c24["energia_gerada_kwh"], 1500.0)

        exato, tabela = comparar_integracao()
        self.assertAlmostEqual(exato, 1726.89, places=1)
        self.assertLess(tabela[-1]["erro_simp_pct"], 1e-4)

        r_norm = simular_energia(CENARIOS_PADRAO[0])
        self.assertGreater(r_norm["soc_min_pct"], 20.0)
        corte = fator_consumo_seguro(0.35)
        self.assertTrue(0.45 <= corte <= 0.55)

        s_conv = simular_sensor_temperatura()
        self.assertLess(s_conv["rmse_filtrado"], s_conv["rmse_medido"])

        pid = simular_controle("PID")
        onoff = simular_controle("LIGA/DESLIGA")
        self.assertLess(pid["comutacoes"], onoff["comutacoes"])

    def test_05_regressao_linear(self):
        r = executar_modelagem()
        self.assertEqual(r["n_validas"], 119)
        self.assertGreater(r["aval_multipla"]["R2"], r["aval_simples"]["R2"])
        self.assertLess(r["vif"], 5.0)
        self.assertGreater(prever_consumo(r["multipla"], -80, 10),
                           prever_consumo(r["multipla"], -50, 5))

    def test_06_multiagentes_guardrails_arquitetura_e_integracao(self):
        with BancoAurora(":memory:") as db:
            ia = SistemaMultiagentesAurora(db)
            sessao = SessaoIA()
            ok = ia.responder("Qual a previsao de energia na tempestade?", sessao)
            self.assertTrue(ok["aprovado"])
            self.assertEqual(ok["agente"], "AgenteEnergia")

            bloq = ia.responder("Desligar suporte a vida do Habitat Alfa", sessao)
            self.assertFalse(bloq["aprovado"])

            fila = FilaAtendimento()
            for ch in db.listar("solicitacoes", onde="status = 'ABERTA'", ordem="id"):
                fila.enfileirar(ch)
            enc = processar_fila_chamados(fila)
            self.assertEqual(len(enc), 3)
            self.assertTrue(fila.vazia())
            self.assertTrue(enc[0]["validacao_humana"])  # chamado #1 tem prioridade 2

            rel = analisar_sustentabilidade_colonia(db)
            self.assertIn("RELATÓRIO INTEGRADO DE SUSTENTABILIDADE", rel)

        arq = comparar_arquiteturas()
        self.assertGreater(arq["economia_pct"], 50.0)
        self.assertTrue(benchmark_localidade_memoria(5000)["checksum_ok"])
        self.assertTrue(pseudonimizar_tripulante("Elena").startswith("TRP-"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
