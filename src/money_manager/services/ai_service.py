"""AI settings, API key, request flow and insight history.

Flow for every AI request::

    prepared = ai.prepare(kind=..., question=...)  # analysis → context → request + disclosure
    if prepared.disclosure.requires_consent:       # online provider
        show prepared.disclosure to the user       # warning + the exact text to be sent
        consent = prepared.disclosure.accept()     # only when the user agrees
    answer = ai.send(prepared, consent)            # may run on a worker thread (no database)
    insight = ai.record(prepared, answer)          # stored in the local history

The provider is fixed when the request is prepared, so changing the
settings in between can never send the reviewed text somewhere else.
"""

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

from money_manager.ai.context import ContextOptions, build_financial_context
from money_manager.ai.privacy import DataDisclosure, OnlineConsent
from money_manager.ai.prompts import AIRequest, AIResponse, build_request
from money_manager.ai.providers import AIProvider, ClientFactory, ProviderStatus, create_provider
from money_manager.ai.secrets import (
    ANTHROPIC_KEY_NAME,
    ApiKey,
    KeyStatus,
    SecretStore,
    resolve_key,
)
from money_manager.ai.settings import AIMode, AISettings, validate_settings
from money_manager.core.errors import NotFoundError, ValidationError
from money_manager.domain.insights import MAX_ANSWER_LENGTH, MAX_HISTORY, Insight, InsightKind
from money_manager.domain.periods import DateRange
from money_manager.domain.validation import is_record_id
from money_manager.persistence.database import Database
from money_manager.persistence.mappers import insight_to_domain
from money_manager.persistence.models import AIInsightModel
from money_manager.persistence.repositories import AIInsightRepository, SettingRepository
from money_manager.services.analysis_service import FinancialAnalysisService

logger = logging.getLogger(__name__)

AI_SETTINGS_KEY = "ai"


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    request: AIRequest
    disclosure: DataDisclosure
    provider: AIProvider
    kind: InsightKind
    question: str
    period: DateRange


class AIService:
    def __init__(
        self,
        database: Database,
        analysis: FinancialAnalysisService,
        *,
        secret_store: SecretStore,
        environ: Mapping[str, str] | None = None,
        anthropic_client_factory: ClientFactory | None = None,
    ) -> None:
        self._database = database
        self._analysis = analysis
        self._secrets = secret_store
        self._environ = os.environ if environ is None else environ
        self._client_factory = anthropic_client_factory

    # ------------------------------------------------------------- settings

    def settings(self) -> AISettings:
        with self._database.session() as session:
            raw = SettingRepository(session).get(AI_SETTINGS_KEY)
        if raw is None:
            return AISettings()
        try:
            data = json.loads(raw)
        except ValueError:
            logger.warning("Stored AI settings are unreadable; using the defaults")
            return AISettings()
        return AISettings.from_dict(data if isinstance(data, dict) else {})

    def save_settings(self, settings: AISettings) -> AISettings:
        settings = validate_settings(settings)
        with self._database.session() as session:
            SettingRepository(session).set(AI_SETTINGS_KEY, json.dumps(settings.to_dict()))
        logger.info("AI settings saved (mode %s)", settings.mode.value)
        return settings

    # -------------------------------------------------------------- API key

    @property
    def key_location(self) -> str:
        return self._secrets.location

    def key_status(self) -> KeyStatus:
        return resolve_key(self._secrets, self._environ)[1]

    def save_api_key(self, text: str) -> KeyStatus:
        key = ApiKey(text)
        self._secrets.set(ANTHROPIC_KEY_NAME, key.reveal())
        logger.info("API key saved to %s", self._secrets.location)
        return self.key_status()

    def remove_api_key(self) -> KeyStatus:
        self._secrets.delete(ANTHROPIC_KEY_NAME)
        logger.info("API key removed from %s", self._secrets.location)
        return self.key_status()

    # ------------------------------------------------------------ providers

    def provider(self, settings: AISettings | None = None) -> AIProvider:
        """The provider for ``settings`` (default: the saved ones); unsaved settings
        may leave the local model open, to list the installed models first."""
        settings = (self.settings() if settings is None
                    else validate_settings(settings, complete=False))
        key = (resolve_key(self._secrets, self._environ)[0]
               if settings.mode in (AIMode.ONLINE, AIMode.AUTO) else None)
        return create_provider(settings, key, self._client_factory)

    def check_availability(self, settings: AISettings | None = None, *,
                           probe: bool = False) -> ProviderStatus:
        return self.provider(settings).check_availability(probe=probe)

    def set_mode(self, mode: AIMode) -> AISettings:
        """Switch between off / local / online, keeping the other settings."""
        try:
            chosen = AIMode(mode)
        except ValueError:
            raise ValidationError("Choose off, local, online or automatic.", "mode") from None
        try:
            return self.save_settings(self.settings().with_changes(mode=chosen))
        except ValidationError as exc:
            if exc.field == "local_model":
                raise ValidationError("Choose a local model in Settings first.", "mode") from exc
            raise

    # ------------------------------------------------------------- requests

    def prepare(self, question: str | None = None, *, kind: InsightKind | None = None,
                period: DateRange | None = None,
                options: ContextOptions = ContextOptions()) -> PreparedRequest:
        """Build the request for a fixed task or a question (default: insights,
        or the question when one is given) about ``period`` (default: this month)."""
        if question is not None and not isinstance(question, str):
            raise ValidationError("Type a question about your finances.", "question")
        if kind is None:
            kind = InsightKind.QUESTION if question and question.strip() else InsightKind.INSIGHTS
        else:
            try:
                kind = InsightKind(kind)
            except ValueError:
                raise ValidationError("Choose what the advisor should do.", "kind") from None
        provider = self.provider()
        analysis = self._analysis.analyze(period)
        if not analysis.has_accounts:
            raise ValidationError("There is no financial data to analyse yet. Create an "
                                  "account and record some transactions first.")
        context = build_financial_context(analysis, options)
        request = build_request(context, kind, question)
        disclosure = DataDisclosure(
            provider=provider.name, destination=provider.destination, model=provider.model,
            is_online=provider.is_online, request=request, included=context.included)
        asked = (question or "").strip() if kind is InsightKind.QUESTION else ""
        return PreparedRequest(request, disclosure, provider, kind, asked, analysis.period)

    def send(self, prepared: PreparedRequest, consent: OnlineConsent | None = None) -> AIResponse:
        """Talks to the provider only (no database), so it may run on a worker thread."""
        return prepared.provider.complete(prepared.request, consent)

    # -------------------------------------------------------------- history

    def record(self, prepared: PreparedRequest, response: AIResponse) -> Insight:
        """Store an answer with the exact analysis it was based on."""
        model = AIInsightModel(
            kind=prepared.kind.value, question=prepared.question,
            period_start=prepared.period.start, period_end=prepared.period.end,
            provider=response.provider[:40], model=response.model[:100],
            is_online=prepared.provider.is_online,
            answer=response.text[:MAX_ANSWER_LENGTH], context=prepared.request.user,
            truncated=response.truncated or len(response.text) > MAX_ANSWER_LENGTH)
        with self._database.session() as session:
            repository = AIInsightRepository(session)
            repository.add(model)
            repository.keep_newest(MAX_HISTORY)
            session.flush()
            session.refresh(model)
            insight = insight_to_domain(model)
        logger.info("AI insight %s stored (%s)", insight.id, insight.kind.value)
        return insight

    def history(self, limit: int = MAX_HISTORY) -> list[Insight]:
        with self._database.session() as session:
            return [insight_to_domain(m) for m in AIInsightRepository(session).recent(limit)]

    def insight(self, insight_id: int) -> Insight:
        with self._database.session() as session:
            model = (AIInsightRepository(session).get(insight_id)
                     if is_record_id(insight_id) else None)
            if model is None:
                raise NotFoundError("This insight no longer exists.")
            return insight_to_domain(model)

    def delete_insight(self, insight_id: int) -> None:
        with self._database.session() as session:
            repository = AIInsightRepository(session)
            model = repository.get(insight_id) if is_record_id(insight_id) else None
            if model is None:
                raise NotFoundError("This insight no longer exists.")
            repository.delete(model)
        logger.info("AI insight %s deleted", insight_id)

    def clear_history(self) -> int:
        with self._database.session() as session:
            count = AIInsightRepository(session).delete_all()
        logger.info("AI insight history cleared (%d)", count)
        return count

    def prepare_again(self, insight: Insight,
                      options: ContextOptions = ContextOptions()) -> PreparedRequest:
        """Regenerate: the same task or question and period, with today's data and the
        currently selected provider."""
        return self.prepare(insight.question or None, kind=insight.kind, period=insight.period,
                            options=options)
