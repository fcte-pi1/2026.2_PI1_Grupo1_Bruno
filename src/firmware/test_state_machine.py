import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "firmware"))

import state_machine as sm  


class FakeClock:
    def __init__(self):
        self.us = 1000000

    def ms(self):
        return self.us // 1000

    def now_us(self):
        return self.us

    def advance_ms(self, ms):
        self.us += ms * 1000


class FakeMotors:
    def __init__(self, clock, stop_cost_us=120, fail=False):
        self.clock = clock
        self.stop_cost_us = stop_cost_us
        self.fail = fail
        self.stop_calls = 0

    def stop(self):
        if self.fail:
            raise OSError("falha simulada")
        self.stop_calls += 1
        self.clock.us += self.stop_cost_us


def make(self_check=None, reset_was_wdt=False, fail_motors=False, cfg=None,
         on_transition=None):
    clk = FakeClock()
    motors = FakeMotors(clk, fail=fail_motors)
    fsm = sm.MouseFSM(motors, clk.ms, clk.now_us, self_check=self_check,
                      cfg=cfg, reset_was_wdt=reset_was_wdt,
                      on_transition=on_transition)
    return fsm, motors, clk


def to_running(fsm):
    fsm.update()
    assert fsm.state == sm.READY
    assert fsm.on_button()
    assert fsm.state == sm.RUNNING


class TestBootEArmar(unittest.TestCase):
    def test_boot_inicia_em_idle_com_motores_parados(self):
        fsm, motors, _ = make()
        self.assertEqual(fsm.state, sm.IDLE)
        self.assertGreaterEqual(motors.stop_calls, 1)
        self.assertFalse(fsm.allows_motion)

    def test_autoverificacao_ok_leva_a_ready(self):
        fsm, _, _ = make(self_check=lambda: True)
        fsm.update()
        self.assertEqual(fsm.state, sm.READY)

    def test_autoverificacao_falha_permanece_em_idle(self):
        fsm, _, _ = make(self_check=lambda: False)
        fsm.update()
        self.assertEqual(fsm.state, sm.IDLE)

    def test_falha_de_motores_no_boot_leva_a_fault(self):
        fsm, _, _ = make(fail_motors=True)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_BOOT)

    def test_excecao_na_autoverificacao_leva_a_fault(self):
        def boom():
            raise ValueError("x")
        fsm, _, _ = make(self_check=boom)
        fsm.update()
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_EXCEPTION)


class TestTransicoes(unittest.TestCase):
    def test_ciclo_normal_com_botao(self):
        fsm, motors, _ = make()
        to_running(fsm)
        self.assertTrue(fsm.allows_motion)
        fsm.on_button()
        self.assertEqual(fsm.state, sm.STOPPED)
        self.assertEqual(fsm.stop_cause, sm.S_BUTTON)
        self.assertFalse(fsm.allows_motion)

    def test_novo_start_apos_stopped_exige_duas_acoes(self):
        fsm, _, _ = make()
        to_running(fsm)
        fsm.on_button()
        fsm.on_button()
        self.assertEqual(fsm.state, sm.READY)
        self.assertFalse(fsm.allows_motion)
        fsm.on_button()
        self.assertEqual(fsm.state, sm.RUNNING)

    def test_chegada_leva_a_finished_e_para_motores(self):
        fsm, motors, _ = make()
        to_running(fsm)
        antes = motors.stop_calls
        self.assertTrue(fsm.goal_reached())
        self.assertEqual(fsm.state, sm.FINISHED)
        self.assertGreater(motors.stop_calls, antes)

    def test_start_em_estado_invalido_e_ignorado(self):
        fsm, _, _ = make()
        self.assertFalse(fsm.handle(sm.EV_START))
        self.assertEqual(fsm.state, sm.IDLE)

    def test_botao_em_idle_e_ignorado(self):
        fsm, _, _ = make()
        self.assertFalse(fsm.on_button())
        self.assertEqual(fsm.state, sm.IDLE)


class TestFalhas(unittest.TestCase):
    def test_sensor_frontal_critico(self):
        fsm, motors, clk = make()
        to_running(fsm)
        antes = motors.stop_calls
        clk.advance_ms(10)
        fsm.update(front_mm=10, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_FRONT_CRITICAL)
        self.assertGreater(motors.stop_calls, antes)

    def test_sensor_frontal_sem_leitura_por_tempo_demais(self):
        fsm, _, clk = make()
        to_running(fsm)
        for _ in range(30):
            clk.advance_ms(10)
            fsm.update(front_mm=None, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_SENSOR_INVALID)

    def test_estol(self):
        fsm, _, clk = make()
        to_running(fsm)
        for _ in range(60):
            clk.advance_ms(10)
            fsm.update(front_mm=200, motion_commanded=True, enc_moved=False)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_STALL)

    def test_sem_estol_se_encoder_se_move(self):
        fsm, _, clk = make()
        to_running(fsm)
        for _ in range(100):
            clk.advance_ms(10)
            fsm.update(front_mm=200, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.RUNNING)

    def test_timeout_de_corrida(self):
        cfg = sm.Config(run_timeout_ms=1000)
        fsm, _, clk = make(cfg=cfg)
        to_running(fsm)
        for _ in range(120):
            clk.advance_ms(10)
            fsm.update(front_mm=200, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_RUN_TIMEOUT)

    def test_excecao_no_loop_para_motores(self):
        fsm, motors, _ = make()
        to_running(fsm)
        antes = motors.stop_calls

        def passo():
            raise RuntimeError("bug")
        fsm.guarded(passo)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_EXCEPTION)
        self.assertGreater(motors.stop_calls, antes)

    def test_falha_de_callback_nao_afeta_seguranca(self):
        def ruim(old, new, cause):
            raise OSError("telemetria fora")
        fsm, motors, _ = make(on_transition=ruim)
        to_running(fsm)
        fsm.fault(sm.F_EXCEPTION)
        self.assertEqual(fsm.state, sm.FAULT)


class TestRecuperacaoEWatchdog(unittest.TestCase):
    def test_reset_por_watchdog_nao_reativa_motores(self):
        fsm, motors, _ = make(reset_was_wdt=True)
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertEqual(fsm.fault_cause, sm.F_WDT_RESET)
        self.assertFalse(fsm.allows_motion)
        self.assertGreaterEqual(motors.stop_calls, 1)

    def test_sair_de_fault_exige_acao_explicita_e_novo_start(self):
        fsm, _, _ = make(reset_was_wdt=True)
        fsm.update()
        self.assertEqual(fsm.state, sm.FAULT)
        self.assertFalse(fsm.handle(sm.EV_START))
        fsm.on_button()
        self.assertEqual(fsm.state, sm.IDLE)
        self.assertIsNone(fsm.fault_cause)
        fsm.update()
        self.assertEqual(fsm.state, sm.READY)
        self.assertFalse(fsm.allows_motion)
        fsm.on_button()
        self.assertEqual(fsm.state, sm.RUNNING)

    def test_saude_do_loop_controla_alimentacao_do_watchdog(self):
        fsm, _, clk = make()
        fsm.update()
        clk.advance_ms(20)
        fsm.update()
        self.assertTrue(fsm.health_ok())
        clk.advance_ms(500)
        fsm.update()
        self.assertFalse(fsm.health_ok())
        clk.advance_ms(20)
        fsm.update()
        self.assertTrue(fsm.health_ok())


class TestTelemetriaEComandoRemoto(unittest.TestCase):
    def test_modo_local_ignora_perda_de_telemetria(self):
        fsm, _, clk = make()
        to_running(fsm)
        for _ in range(200):
            clk.advance_ms(10)
            fsm.update(front_mm=200, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.RUNNING)

    def test_modo_remoto_sem_heartbeat_para_o_movimento(self):
        fsm, _, clk = make()
        fsm.update()
        fsm.set_mode(sm.MODE_REMOTE)
        self.assertTrue(fsm.remote_command(sm.EV_START))
        self.assertEqual(fsm.state, sm.RUNNING)
        for _ in range(100):
            clk.advance_ms(10)
            fsm.update(front_mm=200, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.STOPPED)
        self.assertEqual(fsm.stop_cause, sm.S_CMD_TIMEOUT)

    def test_modo_remoto_com_heartbeat_continua(self):
        fsm, _, clk = make()
        fsm.update()
        fsm.set_mode(sm.MODE_REMOTE)
        fsm.remote_command(sm.EV_START)
        for _ in range(100):
            clk.advance_ms(10)
            fsm.command_heartbeat()
            fsm.update(front_mm=200, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.state, sm.RUNNING)

    def test_comando_remoto_em_modo_local_e_ignorado(self):
        fsm, _, _ = make()
        fsm.update()
        self.assertFalse(fsm.remote_command(sm.EV_START))
        self.assertEqual(fsm.state, sm.READY)


class TestLatenciaDeParada(unittest.TestCase):
    def test_latencia_de_parada_e_registrada(self):
        fsm, motors, clk = make()
        to_running(fsm)
        clk.advance_ms(10)
        fsm.update(front_mm=5, motion_commanded=True, enc_moved=True)
        self.assertEqual(fsm.last_stop_latency_us, motors.stop_cost_us)

    def test_latencia_na_parada_por_botao(self):
        fsm, motors, _ = make()
        to_running(fsm)
        fsm.on_button()
        self.assertEqual(fsm.last_stop_latency_us, motors.stop_cost_us)


if __name__ == "__main__":
    unittest.main()