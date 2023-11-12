from zafkiel.device.template import ImageTemplate as Template
from zafkiel.exception import ScriptError


class Switch:
    """
    A wrapper to handle switches in game, switch among states with retries.
    Main code comes from https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/ui/switch.py

    Examples:
        # Definitions
        submarine_hunt = Switch('Submarine_hunt', offset=120)
        submarine_hunt.add_state('on', check_button=Template(r"assets/ON.png"))
        submarine_hunt.add_state('off', check_button=Template(r"assets/OFF.png"))

        # Change state to ON
        submarine_view.set(TPL_ON)
    """

    def __init__(self, name: str = 'Switch', is_selector: bool = False):
        """
        Args:
            name:
            is_selector: True if this is a multi choice, click to choose one of the switches.
                For example: | [Daily] | Urgent | -> click -> | Daily | [Urgent] |
                False if this is a switch, click the switch itself, and it changed in the same position.
                For example: | [ON] | -> click -> | [OFF] |
        """
        self.name = name
        self.is_choice = is_selector
        self.state_list = []

    def __str__(self):
        return self.name

    __repr__ = __str__

    def add_state(self, state: str, check_button: Template, click_button: Template = None):
        """
        Args:
            state: Must match check_button.name
            check_button:
            click_button:
        """
        self.state_list.append({
            'state': state,
            'check_button': check_button,
            'click_button': click_button if click_button is not None else check_button,
        })

    def get_data(self, state: Template) -> dict:
        """
        Args:
            state:

        Returns:
            Dictionary in add_state

        Raises:
            ScriptError: If state invalid
        """
        for row in self.state_list:
            if row['state'] == state.name:
                return row

        raise ScriptError(f'Switch {self.name} received an invalid state {state}')
