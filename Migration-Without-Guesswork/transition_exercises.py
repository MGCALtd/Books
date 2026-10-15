"""Original fictional calculations; no platform, customer data or remote effects."""
import json

STEPS = {
    'freeze': (10, ()),
    'apply': (12, ('freeze',)),
    'data': (18, ('apply',)),
    'access': (8, ('apply',)),
    'decide': (5, ('data', 'access')),
    'switch': (5, ('decide',)),
    'check': (10, ('switch',)),
    'reopen': (5, ('check',)),
}

def schedule(steps):
    """Dependency-only elapsed schedule. Separate available operators are assumed."""
    result, visiting = {}, set()
    def finish(name):
        if name in result:
            return result[name]['finish']
        if name in visiting:
            raise ValueError('dependency cycle')
        if name not in steps:
            raise ValueError('missing prerequisite: ' + name)
        duration, deps = steps[name]
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
            raise ValueError('non-negative numeric duration required')
        visiting.add(name)
        start = max((finish(d) for d in deps), default=0)
        result[name] = {'start': start, 'finish': start + duration}
        visiting.remove(name)
        return start + duration
    for name in steps:
        finish(name)
    return result

def latest_return_decision(window, return_time, allowance):
    if min(window, return_time, allowance) < 0:
        raise ValueError('negative time')
    deadline = window - return_time - allowance
    if deadline < 0:
        raise ValueError('return does not fit the window')
    return deadline

def prewrite_return_available(elapsed, target_work_accepted):
    return elapsed <= latest_return_decision(90, 20, 10) and not target_work_accepted

def go_decision_on_time(completed_at):
    return completed_at <= 55

BASE = {'T1/O-101': 4000, 'T1/O-102': 6500,
        'T1/O-105': 5000, 'T1/O-106': 2500}
JOURNAL = (
    ('insert', 'T1/O-107', None, 3000),
    ('insert', 'T1/O-108', None, 4500),
    ('update', 'T1/O-102', 6500, 7000),
)
EXPECTED = {'T1/O-101': 4000, 'T1/O-102': 7000, 'T1/O-105': 5000,
            'T1/O-106': 2500, 'T1/O-107': 3000, 'T1/O-108': 4500}

def reconstruct(base, journal):
    """Ordered, complete teaching journal with explicit before-value checks.

    Deliberately not an idempotent replay engine or a full order/service model.
    A repeated insert fails rather than silently creating another object.
    """
    state = dict(base)
    for op, key, before, after in journal:
        if op == 'insert':
            if key in state:
                raise ValueError('insert conflict: ' + key)
            state[key] = after
        elif op == 'update':
            if key not in state or state[key] != before:
                raise ValueError('update conflict: ' + key)
            state[key] = after
        else:
            raise ValueError('unsupported teaching operation')
    return state

class Authority:
    """Logical model only; does not implement distributed write fencing."""
    def __init__(self):
        self.state = 'SOURCE'
    def move(self, destination, verified=False):
        if (self.state, destination) not in {
            ('SOURCE', 'NONE'), ('TARGET', 'NONE'),
            ('NONE', 'SOURCE'), ('NONE', 'TARGET')
        }:
            raise ValueError('unsupported authority transition')
        if destination != 'NONE' and not verified:
            raise ValueError('verification gate required')
        self.state = destination
        return self.state

def run():
    delayed_data = dict(STEPS, data=(33, ('apply',)))
    delayed_access = dict(STEPS, access=(24, ('apply',)))
    restored = reconstruct(BASE, JOURNAL)
    authority = Authority()
    states = [authority.state, authority.move('NONE'), authority.move('TARGET', True)]
    return {
        'planned': schedule(STEPS),
        'delayed_data': schedule(delayed_data),
        'delayed_access': schedule(delayed_access),
        'clock_only_pre_write_return_limit_minute': latest_return_decision(90, 20, 10),
        'planned_first_business_write_minute': 50,
        'hard_go_decision_cutoff_minute': 55,
        'delayed_data_forward_schedule_is_executed': False,
        'post_write_orders': restored,
        'post_write_rows': len(restored),
        'post_write_total_minor': sum(restored.values()),
        'exact_teaching_population_matches': restored == EXPECTED,
        'logical_authority_states': states,
        'fictional_timely_correct_fraction': 1990 / 2000,
        'scope': 'fictional arithmetic and logical models; not service acceptance',
    }

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
