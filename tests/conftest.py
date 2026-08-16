import pytest

import xbmc
import xbmcaddon
import xbmcgui


@pytest.fixture(autouse=True)
def clean_kodi_stubs():
    """Kodi's modules are process-wide singletons; so are the stubs."""
    xbmc.reset()
    xbmcaddon.reset()
    xbmcgui.reset()
    yield
    xbmc.reset()
    xbmcaddon.reset()
    xbmcgui.reset()
