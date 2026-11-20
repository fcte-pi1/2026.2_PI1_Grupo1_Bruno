import importlib
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'firmware'))
from robot import config
from robot.control import Halt, Motion
from robot.app import Robot
from robot.planner import Explorer, DELTA, patrol_choice, classify


def settings(**overrides):
    values = {n: getattr(config, n) for n in dir(config) if n.isupper()}
    values.update(COUNTS_PER_MM=(1, 1), TURN_90_COUNTS=(30, 30),
                  TURN_CLEARANCE_MM=30, RAMP_PER_SECOND=4,
                  STABLE_CHASSIS=True, CALIBRATED=True)
    values.update(overrides)
    values['validate_motion'] = lambda: None
    values['validate_grid'] = lambda: None
    return SimpleNamespace(**values)


class Plant:
    """Planta virtual de contagens; nao modela derrapagem/ultrassom fisico."""
    def __init__(self):
        self.t = 0
        self.position = [0.0, 0.0]
        self.output = (0, 0)
        self.commands = []
        self.gains = [1, 1]
        self.front = 500
        self.button_at = None
        self.failure_at = None

    def now(self): return self.t % (1 << 30)
    def diff(self, a, b): return ((a-b+(1 << 29)) % (1 << 30)) - (1 << 29)
    def counts(self): return tuple(round(p) for p in self.position)
    def power(self, a, b):
        self.output = (a, b)
        self.commands.append((self.t, a, b))
    def stop(self): self.output = (0, 0)
    def sleep(self, ms):
        for i in (0, 1): self.position[i] += self.output[i] * self.gains[i] * ms
        self.t += ms
    def pressed(self): return self.button_at is not None and self.t >= self.button_at
    def distance(self, name):
        if self.failure_at is not None and self.t >= self.failure_at:
            return None
        return self.front if name == 'front' else 500
    def scan(self, service=lambda: None):
        self.stop()
        result = {}
        for n in ('front', 'right', 'back', 'left'):
            service()
            result[n] = self.distance(n)
        return result


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.h = Plant()
        self.c = settings()
        self.m = Motion(self.h, self.c)

    def test_forward_reaches_both_targets_and_stops(self):
        self.h.gains = [1, .7]
        result = self.m.forward(80)
        self.assertTrue(all(p >= 80 for p in result))
        self.assertEqual(self.h.output, (0, 0))
        self.assertTrue(all(0 <= a <= self.c.DRIVE_PWM and 0 <= b <= self.c.DRIVE_PWM
                            for _, a, b in self.h.commands))

    def test_ramp_limits_first_command(self):
        self.m.forward(30)
        nonzero = [(a,b) for _,a,b in self.h.commands if a or b]
        self.assertLessEqual(max(nonzero[0]), .041)

    def test_obstacle_blocks_before_power(self):
        self.h.front = 100
        with self.assertRaisesRegex(Halt, 'OBSTACLE'): self.m.forward(40)
        self.assertEqual(self.h.commands, [])

    def test_invalid_sensor_blocks_before_power(self):
        self.h.front = None
        with self.assertRaisesRegex(Halt, 'INVALID'): self.m.forward(40)
        self.assertEqual(self.h.output, (0,0))

    def test_sensor_loss_during_motion(self):
        self.h.failure_at = 100
        with self.assertRaisesRegex(Halt, 'INVALID'): self.m.forward(200)
        self.assertLess(self.h.t, 200)
        self.assertEqual(self.h.output, (0,0))

    def test_stall_of_one_wheel_stops_both(self):
        self.h.gains[0] = 0
        with self.assertRaisesRegex(Halt, 'STALL_0'): self.m.forward(200)
        self.assertLess(self.h.t, 600)
        self.assertEqual(self.h.output, (0,0))

    def test_wrong_encoder_direction(self):
        self.h.gains[1] = -1
        with self.assertRaisesRegex(Halt, 'DIRECTION'): self.m.forward(100)
        self.assertEqual(self.h.output, (0,0))

    def test_timeout_even_when_encoder_changes(self):
        self.c.MOVE_TIMEOUT_MS = 80
        with self.assertRaisesRegex(Halt, 'TIMEOUT'): self.m.forward(200)
        self.assertEqual(self.h.output, (0,0))

    def test_ticks_wrap(self):
        self.h.t = (1 << 30)-30
        self.m.forward(20)
        self.assertEqual(self.h.output, (0,0))

    def test_turn_directions_and_180(self):
        for rel, expected in ((1,(1,-1)),(2,(1,-1)),(3,(-1,1))):
            h=Plant(); m=Motion(h,self.c)
            m.turn(rel)
            a,b=h.counts()
            self.assertGreater(a*expected[0], 0)
            self.assertGreater(b*expected[1], 0)
            if rel==2: self.assertGreaterEqual(abs(a),60)
            self.assertEqual(h.output,(0,0))

    def test_turn_requires_all_clearances(self):
        self.h.scan=lambda service: {'front':500,'back':500,'left':10,'right':500}
        with self.assertRaisesRegex(Halt,'CLEARANCE'): self.m.turn(1)
        self.assertEqual(self.h.commands,[])

    def test_exception_stops_even_after_power(self):
        def service():
            if self.h.t>60: raise RuntimeError('unexpected')
        self.m.service=service
        with self.assertRaises(RuntimeError): self.m.forward(100)
        self.assertEqual(self.h.output,(0,0))


class AppTests(unittest.TestCase):
    def test_default_calibration_blocks_motion(self):
        h=Plant(); r=Robot(h,config,log=lambda *a:None)
        r.run()
        self.assertEqual(r.state,'FAULT')
        self.assertEqual(h.commands,[])

    def test_each_missing_calibration_blocks(self):
        old={k:getattr(config,k) for k in ('STABLE_CHASSIS','CALIBRATED','COUNTS_PER_MM','TURN_90_COUNTS','TURN_CLEARANCE_MM')}
        try:
            config.STABLE_CHASSIS=config.CALIBRATED=True
            config.COUNTS_PER_MM=(1,1); config.TURN_90_COUNTS=(30,30)
            config.TURN_CLEARANCE_MM=30
            config.validate_motion()
            for name in ('COUNTS_PER_MM','TURN_90_COUNTS','TURN_CLEARANCE_MM'):
                saved=getattr(config,name)
                setattr(config,name,(None,1) if isinstance(saved,tuple) else None)
                with self.assertRaises(ValueError): config.validate_motion()
                setattr(config,name,saved)
        finally:
            for k,v in old.items(): setattr(config,k,v)

    def test_button_during_motion_stops(self):
        h=Plant(); h.button_at=150
        r=Robot(h,settings(),log=lambda *a:None)
        self.assertEqual(r.run(),'BUTTON_STOP')
        self.assertEqual(r.state,'STOPPED')
        self.assertEqual(h.output,(0,0))

    def test_global_deadline(self):
        h=Plant(); r=Robot(h,settings(RUN_TIMEOUT_MS=120),log=lambda *a:None)
        self.assertEqual(r.run(),'RUN_TIMEOUT')
        self.assertEqual(h.output,(0,0))

    def test_action_limit(self):
        h=Plant(); r=Robot(h,settings(MAX_ACTIONS=2),log=lambda *a:None)
        self.assertEqual(r.run(),'ACTION_LIMIT')
        self.assertEqual(h.output,(0,0))

    def test_scan_failure_never_means_open(self):
        h=Plant(); h.front=None
        r=Robot(h,settings(),log=lambda *a:None)
        self.assertEqual(r.run(),'SENSOR_INVALID')
        self.assertEqual(h.commands,[])

    def test_grid_pose_not_committed_on_incomplete_move(self):
        h=Plant(); h.gains=[0,0]
        r=Robot(h,settings(),log=lambda *a:None)
        r.run('explore')
        self.assertEqual(r.explorer.pos,(0,0))
        self.assertIsNone(r.explorer.pending)
        self.assertEqual(r.state,'FAULT')

    def test_bench_pulse_requires_explicit_lifted(self):
        h=Plant(); r=Robot(h,settings())
        with self.assertRaises(ValueError): r.pulse(.4,.4)
        self.assertEqual(h.commands,[])

    def test_bench_pulse_bounded_and_stopped(self):
        h=Plant(); r=Robot(h,settings())
        r.pulse(.4,.4,300,wheels_lifted=True)
        self.assertEqual(h.t,300)
        self.assertEqual(h.output,(0,0))

    def test_grid_geometry_requires_measurement(self):
        with self.assertRaises(ValueError): config.validate_grid()

    def test_jog_limited_and_stability_required(self):
        h=Plant(); c=settings(STABLE_CHASSIS=False)
        r=Robot(h,c,log=lambda *a:None)
        with self.assertRaises(ValueError): r.jog()
        c.STABLE_CHASSIS=True
        with self.assertRaises(ValueError): r.jog(duration_ms=301)
        r.jog('right',150)
        self.assertEqual(h.output,(0,0))
        self.assertGreater(h.position[0],0)
        self.assertLess(h.position[1],0)

    def test_obstacle_appearing_during_movement(self):
        h=Plant()
        h.distance=lambda name: 500 if h.t<100 else 100
        r=Robot(h,settings(),log=lambda *a:None)
        self.assertEqual(r.run(),'FRONT_OBSTACLE')
        self.assertEqual(h.output,(0,0))
        self.assertLess(h.t,200)


class PlannerTests(unittest.TestCase):
    def test_ambiguous_or_invalid_wall(self):
        for v in (None,180,175,190):
            with self.assertRaises(ValueError): classify(dict(front=v,right=500,back=500,left=500),180,15)

    def test_patrol_decisions(self):
        self.assertEqual(patrol_choice(dict(front=500,right=500,left=500,back=500),200,30),'FORWARD')
        self.assertEqual(patrol_choice(dict(front=100,right=500,left=500,back=500),200,30),'RIGHT')
        self.assertEqual(patrol_choice(dict(front=100,right=100,left=500,back=500),200,30),'LEFT')
        self.assertEqual(patrol_choice(dict(front=100,right=100,left=100,back=500),200,30),'BACK')
        self.assertEqual(patrol_choice(dict(front=10,right=500,left=500,back=500),200,30),'BLOCKED')
        self.assertEqual(patrol_choice(dict(front=None,right=500,left=500,back=500),200,30),'FAULT')

    def test_commit_contract(self):
        e=Explorer(); e.choose([True]*4)
        self.assertEqual(e.pos,(0,0))
        with self.assertRaises(ValueError): e.choose([True]*4)
        e.abort(); self.assertEqual(e.pos,(0,0))
        e.choose([True]*4); e.commit(); self.assertEqual(e.pos,(1,0))

    def test_limit_and_goal(self):
        self.assertEqual(Explorer(max_cells=1).choose([True]*4)[0],'LIMIT')
        self.assertEqual(Explorer(goal=(0,0)).choose([True]*4)[0],'GOAL')

    def test_blocked_return(self):
        e=Explorer(); e.choose([True,False,False,False]); e.commit()
        self.assertEqual(e.choose([False]*4)[0],'BLOCKED')

    def test_200_random_mazes_loops_deadends_arbitrary_start(self):
        for seed in range(200):
            rng=random.Random(seed)
            w,h=rng.choice(((4,4),(4,12),(8,8)))
            edges={ (x,y):set() for x in range(w) for y in range(h) }
            # Arvore conectada aleatoria, depois adiciona ciclos.
            stack=[(0,0)]; visited={(0,0)}
            while stack:
                p=stack[-1]
                candidates=[(p[0]+dx,p[1]+dy) for dx,dy in DELTA
                            if (p[0]+dx,p[1]+dy) in edges and (p[0]+dx,p[1]+dy) not in visited]
                if not candidates: stack.pop(); continue
                q=rng.choice(candidates); edges[p].add(q); edges[q].add(p)
                visited.add(q); stack.append(q)
            for p in edges:
                for dx,dy in DELTA:
                    q=(p[0]+dx,p[1]+dy)
                    if q in edges and rng.random()<.15:
                        edges[p].add(q); edges[q].add(p)
            origin=rng.choice(list(edges))
            explorer=Explorer()
            for step in range(w*h*2+1):
                p=(explorer.pos[0]+origin[0], explorer.pos[1]+origin[1])
                opening=[]
                for r in range(4):
                    dx,dy=DELTA[(explorer.heading+r)%4]
                    opening.append((p[0]+dx,p[1]+dy) in edges[p])
                status,rel=explorer.choose(opening)
                if status=='EXPLORED': break
                self.assertEqual(status,'MOVE',seed)
                target=explorer.pending[0]
                q=(target[0]+origin[0],target[1]+origin[1])
                self.assertIn(q,edges[p])  # nunca atravessa parede
                explorer.commit()
            else: self.fail('Nao terminou: '+str(seed))
            self.assertEqual(len(explorer.visited),w*h)
            self.assertEqual(explorer.pos,(0,0))


if __name__=='__main__': unittest.main()
