import os
import atexit
import streamlit as st

from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings


@st.cache_resource
def get_application_services():
    values = dict(os.environ)
    try:
        values.update(dict(st.secrets))
    except (FileNotFoundError, KeyError):
        pass
    services = ApplicationFactory(Settings.from_mapping(values))
    atexit.register(services.close)
    return services
