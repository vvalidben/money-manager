from sqlalchemy.orm import Session

from money_manager.persistence.models import SettingModel


class SettingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> str | None:
        setting = self._session.get(SettingModel, key)
        return None if setting is None else setting.value

    def set(self, key: str, value: str) -> None:
        setting = self._session.get(SettingModel, key)
        if setting is None:
            self._session.add(SettingModel(key=key, value=value))
        else:
            setting.value = value
        self._session.flush()

    def delete(self, key: str) -> None:
        setting = self._session.get(SettingModel, key)
        if setting is not None:
            self._session.delete(setting)
            self._session.flush()
