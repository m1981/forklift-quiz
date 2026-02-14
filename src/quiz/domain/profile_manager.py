from datetime import date
from typing import cast

import streamlit as st

from src.quiz.domain.models import Language, UserProfile
from src.quiz.domain.ports import IQuizRepository


class ProfileManager:
    """
    Centralized profile management with session caching.
    Ensures profile is fetched once per session and updates are batched.
    """

    def __init__(self, repo: IQuizRepository, user_id: str):
        self.repo = repo
        self.user_id = user_id
        self._cache_key = f"profile_{user_id}"
        self._dirty_fields: set[str] = set()
        self._change_count = 0
        self._batch_threshold = 5

    def get(self) -> UserProfile:
        """Get profile from cache or DB."""
        if self._cache_key not in st.session_state:
            profile = self.repo.get_or_create_profile(self.user_id)
            st.session_state[self._cache_key] = profile
            return profile

        return cast(UserProfile, st.session_state[self._cache_key])

    def update_language(self, lang: Language) -> None:
        """Update language preference and mark for save."""
        profile = self.get()
        if profile.preferred_language != lang:
            profile.preferred_language = lang
            self._dirty_fields.add("preferred_language")
            self._flush()  # Critical change - save immediately

    def increment_daily_progress(self) -> None:
        """Increment daily progress, resetting if new day."""
        profile = self.get()
        today = date.today()

        # Reset if new day (but don't flush yet - let batching handle it)
        if profile.last_daily_reset < today:
            profile.daily_progress = 0
            profile.last_daily_reset = today
            self._dirty_fields.update(["daily_progress", "last_daily_reset"])
            # Flush immediately on date change
            self._flush()
            self._change_count = 0

        # Increment
        profile.daily_progress += 1
        self._dirty_fields.add("daily_progress")
        self._change_count += 1

        # Auto-flush every 5 changes
        if self._change_count >= self._batch_threshold:
            self._flush()
            self._change_count = 0

    def complete_onboarding(self) -> None:
        """Mark onboarding as complete."""
        profile = self.get()
        profile.has_completed_onboarding = True
        self._dirty_fields.add("has_completed_onboarding")
        self._flush()  # Critical change - save immediately

    def _flush(self) -> None:
        """Write dirty fields to database."""
        if not self._dirty_fields:
            return

        profile = self.get()
        self.repo.save_profile(profile)
        self._dirty_fields.clear()

    def flush(self) -> None:
        """Public method to force flush. Alias for _flush()."""
        self._flush()

    def flush_on_exit(self) -> None:
        """Call this at end of quiz to ensure all changes are saved."""
        self._flush()
