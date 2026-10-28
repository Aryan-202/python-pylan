"""Full-screen application views for PyLan Flet UI."""

from pylan.ui.views.home_view import create_home_view
from pylan.ui.views.receive_view import create_receive_view
from pylan.ui.views.send_view import create_send_view
from pylan.ui.views.settings_view import create_settings_view

__all__: list[str] = [
    "create_home_view",
    "create_receive_view",
    "create_send_view",
    "create_settings_view",
]
