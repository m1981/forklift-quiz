from abc import ABC, abstractmethod
from typing import Any

import streamlit as st


class IStateProvider(ABC):
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass


class StreamlitStateProvider(IStateProvider):
    def get(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        st.session_state[key] = value

    def clear(self) -> None:
        st.session_state.clear()
