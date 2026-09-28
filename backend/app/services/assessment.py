"""Первичная диагностика: ответы → оценка навыков → начальный Skill Map."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import InvalidDataError
from backend.app.domain import Skill, User
from backend.app.services.skills import SkillService

VALID_ASSESSMENT_LEVELS = (0, 1, 2, 3)


@dataclass(frozen=True)
class AssessmentQuestion:
    """Вопрос диагностики. Каждый вариант ответа даёт уровень навыка."""

    id: int
    skill: str
    text: str
    options: tuple[tuple[str, int], ...]


# Банк вопросов диагностики. id задан явно, чтобы клиент мог ссылаться на вопросы.
ASSESSMENT_QUESTIONS: tuple[AssessmentQuestion, ...] = (
    AssessmentQuestion(
        1,
        "Python",
        "Насколько уверенно вы пишете на Python?",
        (
            ("Почти не писал(а): знаю только print", 0),
            ("Писал(а) простые скрипты: циклы, условия, списки", 1),
            ("Использую функции, классы, исключения, словари", 2),
            ("Пишу проекты с библиотеками, тестами и типами", 3),
        ),
    ),
    AssessmentQuestion(
        2,
        "SQL",
        "Как вы работаете с базами данных?",
        (
            ("Никогда не работал(а) с SQL", 0),
            ("Знаю SELECT, INSERT, UPDATE, WHERE", 1),
            ("Делаю JOIN'ы, GROUP BY и агрегации", 2),
            ("Проектирую схемы, индексы, оптимизирую запросы", 3),
        ),
    ),
    AssessmentQuestion(
        3,
        "Git",
        "Как вы используете систему контроля версий?",
        (
            ("Не знаком(а) с Git", 0),
            ("Делаю commit и push своих проектов", 1),
            ("Работаю с ветками и делаю pull request'ы", 2),
            ("Настраиваю CI, разрешаю конфликты, использую rebase", 3),
        ),
    ),
    AssessmentQuestion(
        4,
        "JavaScript",
        "Ваш уровень в JavaScript?",
        (
            ("Не знаком(а) с JavaScript", 0),
            ("Знаю переменные, условия, циклы", 1),
            ("Работаю с функциями, массивами, объектами, DOM", 2),
            ("Использую async/await, модули, сборку проекта", 3),
        ),
    ),
    AssessmentQuestion(
        5,
        "Алгоритмы и структуры данных",
        "Как решаются алгоритмические задачи?",
        (
            ("Не решал(а) алгоритмические задачи", 0),
            ("Решаю простые задачи с массивами и строками", 1),
            ("Знаю стек, очередь, деревья, сортировки", 2),
            ("Разбираюсь в графах, динамике и сложности алгоритмов", 3),
        ),
    ),
    AssessmentQuestion(
        6,
        "Testing",
        "Как вы проверяете свой код?",
        (
            ("Не пишу тестов", 0),
            ("Запускаю код вручную и смотрю вывод", 1),
            ("Пишу простые юнит-тесты", 2),
            ("Пишу unit/integration тесты, знаю TDD", 3),
        ),
    ),
    AssessmentQuestion(
        7,
        "Figma",
        "Ваш опыт работы с Figma?",
        (
            ("Никогда не открывал(а) Figma", 0),
            ("Смотрю макеты, знаю базовые инструменты", 1),
            ("Собираю простые макеты и компоненты", 2),
            ("Создаю дизайн-системы и прототипы", 3),
        ),
    ),
    AssessmentQuestion(
        8,
        "Pandas",
        "Как вы работаете с данными?",
        (
            ("Не работал(а) с табличными данными", 0),
            ("Использую Excel для простых таблиц", 1),
            ("Знаю Pandas: чтение, фильтрация, группировка", 2),
            ("Пишу пайплайны анализа данных, использую визуализацию", 3),
        ),
    ),
)


def _find_question(question_id: int) -> AssessmentQuestion | None:
    for question in ASSESSMENT_QUESTIONS:
        if question.id == question_id:
            return question
    return None


class AssessmentService:
    """Сервис первичной диагностики."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.skill_service = SkillService(db)

    def run(self, user: User, answers: list[dict]) -> dict:
        """Оценить ответы и сформировать начальный Skill Map.

        ``answers`` — список ``{"question_id": int, "option_index": int}``.
        """
        if not answers:
            raise InvalidDataError("Диагностика требует хотя бы один ответ")

        levels_by_skill: dict[int, list[int]] = {}
        for answer in answers:
            question = _find_question(answer["question_id"])
            if question is None:
                raise InvalidDataError(
                    f"Вопрос {answer['question_id']} не найден в диагностике"
                )
            option_index = answer["option_index"]
            if not 0 <= option_index < len(question.options):
                raise InvalidDataError(
                    f"Для вопроса {question.id} некорректный вариант {option_index}"
                )
            skill = self.db.scalar(select(Skill).where(Skill.name == question.skill))
            if skill is None:
                # Навык не входит в базу — ответ пропускается.
                continue
            levels_by_skill.setdefault(skill.id, []).append(
                question.options[option_index][1]
            )

        if not levels_by_skill:
            raise InvalidDataError("Нет ни одного ответа, который можно оценить")

        for skill_id, levels in levels_by_skill.items():
            average = sum(levels) / len(levels)
            level = round(average)
            level = min(max(level, 0), 3)
            self.skill_service.set_initial_skill(user.id, skill_id, level)

        evaluated_ids = set(levels_by_skill)
        skill_map = [
            item
            for item in self.skill_service.get_skill_map(user.id)
            if item["skill_id"] in evaluated_ids
        ]

        average_level = (
            sum(item["level"] for item in skill_map) / len(skill_map)
            if skill_map
            else 0
        )
        return {
            "user_id": user.id,
            "evaluated_skills": skill_map,
            "summary": self._summary(average_level),
        }

    @staticmethod
    def _summary(average_level: float) -> str:
        if average_level < 1:
            return (
                "Ваш стартовый уровень — начальный. "
                "Рекомендуем пройти базовые миссии и курсы для старта."
            )
        if average_level < 2:
            return (
                "Ваш стартовый уровень — базовый. "
                "Продолжайте прокачивать навыки через игровые миссии."
            )
        if average_level < 3:
            return (
                "Ваш стартовый уровень — средний. "
                "Готовьтесь к более сложным миссиям и стажировкам."
            )
        return (
            "Ваш стартовый уровень — высокий. "
            "Попробуйте сложные миссии и присматривайтесь к стажировкам."
        )
