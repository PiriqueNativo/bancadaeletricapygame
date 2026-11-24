"""Testes de unidade da bancada elétrica.  Execute com:  python -m unittest -v"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # Pygame sem janela (testes de integração)
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import logica_bancada as lb
from logica_bancada import BorneInvalidoError, TensaoInvalidaError

FASE1 = [("L", "F5_1"), ("F5_2", "S12_13"), ("S12_14", "H1_X1"), ("H1_X2", "N")]
FASE2 = [("L", "F5_1"), ("F5_2", "S10_11"), ("S10_12", "S12_13"), ("S12_14", "H2_X1"),
         ("H2_X2", "N"), ("V_POS", "H2_X1"), ("V_NEG", "H2_X2")]
FASE3 = [("L", "F5_1"), ("F5_2", "R1_1"), ("R1_2", "A_POS"), ("A_NEG", "N")]


class TestCircuito(unittest.TestCase):
    def test_sem_cabos_nada_energizado(self):
        r = lb.avaliar_circuito([], False, False, 127)
        self.assertFalse(r.curto)
        self.assertFalse(r.h1_acesa or r.h2_acesa or r.r1_energizado)
        self.assertEqual((r.leitura_volt, r.leitura_amp), (0.0, 0.0))

    def test_fase1_lampada_so_acende_com_s12_pressionado(self):
        self.assertFalse(lb.avaliar_circuito(FASE1, False, False, 127).h1_acesa)
        self.assertTrue(lb.avaliar_circuito(FASE1, False, True, 127).h1_acesa)

    def test_fase2_s10_pressionado_abre_o_comando(self):
        self.assertTrue(lb.avaliar_circuito(FASE2, False, True, 127).h2_acesa)
        self.assertFalse(lb.avaliar_circuito(FASE2, True, True, 127).h2_acesa)

    def test_fase2_voltimetro_em_paralelo_le_a_tensao_da_fonte(self):
        r = lb.avaliar_circuito(FASE2, False, True, 127)
        self.assertEqual(r.leitura_volt, 127)
        self.assertEqual(lb.avaliar_circuito(FASE2, False, False, 127).leitura_volt, 0.0)

    def test_fase3_corrente_do_resistor_lei_de_ohm(self):
        r = lb.avaliar_circuito(FASE3, False, False, 127)
        self.assertTrue(r.r1_energizado)
        self.assertAlmostEqual(r.leitura_amp, 127 / lb.RESISTENCIA_R1, places=2)

    def test_amperimetro_sem_carga_le_zero(self):
        # Amperímetro ligado só do lado de L: não há caminho até N, logo corrente zero.
        r = lb.avaliar_circuito([("L", "F5_1"), ("F5_2", "A_POS")], False, False, 127)
        self.assertFalse(r.curto)
        self.assertEqual(r.leitura_amp, 0.0)

    def test_amperimetro_direto_entre_l_e_n_e_curto(self):
        r = lb.avaliar_circuito([("L", "F5_1"), ("F5_2", "A_POS"), ("A_NEG", "N")], False, False, 127)
        self.assertTrue(r.curto)

    def test_curto_direto_entre_l_e_n(self):
        r = lb.avaliar_circuito([("L", "N")], False, False, 127)
        self.assertTrue(r.curto)
        self.assertEqual(r.leitura_amp, lb.CORRENTE_CURTO)
        self.assertEqual(r.potenciais["L"], "CURTO")

    def test_curto_atraves_de_contato_nf_some_ao_pressionar(self):
        cabos = [("L", "S10_11"), ("S10_12", "N")]
        self.assertTrue(lb.avaliar_circuito(cabos, False, False, 127).curto)
        self.assertFalse(lb.avaliar_circuito(cabos, True, False, 127).curto)

    def test_potenciais_propagados(self):
        r = lb.avaliar_circuito([("L", "F5_1")], False, False, 127)
        self.assertEqual(r.potenciais["F5_2"], "L")  # fusível conduz
        self.assertEqual(r.potenciais["N"], "N")


class TestExcecoes(unittest.TestCase):
    def test_tensao_invalida(self):
        for ruim in (0, -127, "abc", None):
            with self.subTest(tensao=ruim):
                with self.assertRaises(TensaoInvalidaError):
                    lb.avaliar_circuito([], False, False, ruim)

    def test_borne_desconhecido(self):
        with self.assertRaises(BorneInvalidoError):
            lb.avaliar_circuito([("L", "XYZ")], False, False, 127)

    def test_cabo_no_mesmo_borne(self):
        with self.assertRaises(BorneInvalidoError):
            lb.avaliar_circuito([("L", "L")], False, False, 127)

    def test_erros_herdam_de_bancada_error(self):
        self.assertTrue(issubclass(BorneInvalidoError, lb.BancadaError))
        self.assertTrue(issubclass(TensaoInvalidaError, lb.BancadaError))


class TestSimulador(unittest.TestCase):
    """Integração com a interface (Pygame em modo headless)."""

    def setUp(self):
        import bancada_eletrica as be
        self.be = be
        self.sim = be.SimuladorBancada()

    def _cabos(self, pares):
        for a, b in pares:
            self.sim.cabos.append(self.be.Cabo(self.sim.bornes[a], self.sim.bornes[b], self.be.COR_VERMELHO))

    def test_simulador_reflete_a_logica(self):
        self._cabos(FASE3)
        self.sim.avaliar_circuito()
        self.assertTrue(self.sim.r1_energizado)
        self.assertAlmostEqual(self.sim.leitura_amp, 1.27, places=2)

    def test_curto_atualiza_mensagem_de_status(self):
        self._cabos([("L", "N")])
        self.sim.avaliar_circuito()
        self.assertTrue(self.sim.curto_detectado)
        self.assertIn("CURTO", self.sim.mensagem_status)

    def test_tensao_invalida_nao_derruba_o_jogo(self):
        self.sim.tensao_fonte = -5
        self.sim.avaliar_circuito()  # não deve lançar exceção
        self.assertIn("Erro", self.sim.mensagem_status)

    def test_resetar_cabos_limpa_tudo(self):
        self._cabos(FASE1)
        self.sim.resetar_cabos()
        self.assertEqual(self.sim.cabos, [])
        self.assertFalse(self.sim.h1_acesa)

    def test_cabo_perto_do_mouse(self):
        cabo = self.be.Cabo(self.sim.bornes["L"], self.sim.bornes["F5_1"], self.be.COR_VERMELHO)
        x, y = cabo.pontos_curva()[16]
        self.assertTrue(cabo.perto_do_mouse((x, y)))
        self.assertFalse(cabo.perto_do_mouse((0, 0)))


if __name__ == "__main__":
    unittest.main()
