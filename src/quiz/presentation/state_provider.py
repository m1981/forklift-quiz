from abc import ABC, abstractmethod
from typing import Any, Optional
import streamlit as st

class IStateProvider(ABC):
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any):
        pass

    @abstractmethod
    def clear(self):
        pass

class StreamlitStateProvider(IStateProvider):
    def get(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)

    def set(self, key: str, value: Any):
        st.session_state[key] = value

    def clear(self):
        st.session_state.clear()