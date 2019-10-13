from cosmic_ray.utils.config import Config, root_config, Entry
from cosmic_ray.operators.operator import Operator
from cosmic_ray.utils.plugins import get_operators_providers
from cosmic_ray.utils.util import dict_filter, LazyDict

operators_config = Config(
    root_config,
    'operators',
    valid_entries={
        'load': Entry(default=['.*'], choices=lambda : operators.keys()),
    },
)


class Operators(LazyDict):

    def _load(self):
        providers = dict(get_operators_providers())
        d = ((name, provider_class())
             for name, provider_class in providers.items())

        available_operators = {
            '%s/%s' % (provider_name, op_name): provider[op_name]
            for provider_name, provider in d
            for op_name in provider
        }

        load_patterns = operators_config['load']
        operators = dict_filter(available_operators, load_patterns)
        # Instantiate
        return {
            name: op(name)
            for name, op in operators.items()  # type: str, Operator
        }


operators = Operators()
