"""Демо-данные SkillQuest.

Наполняет базу навыками, игровыми миссиями, курсами и стажировками.
Вызов: ``python -m backend.app.seed`` или автоматически при старте (см. config).
"""

from __future__ import annotations

import sys
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.domain import (
    Course,
    Internship,
    Mission,
    MissionOption,
    Role,
    RoleSkill,
    Skill,
)

SEED_SKILLS: list[tuple[str, str, str]] = [
    ("Python", "Программирование", "Язык программирования для backend, data и не только"),
    ("SQL", "Данные", "Язык запросов к реляционным базам данных"),
    ("Git", "Инструменты", "Система контроля версий"),
    ("JavaScript", "Программирование", "Язык веб-разработки"),
    ("FastAPI", "Программирование", "Современный фреймворк для бэкенда на Python"),
    ("React", "Программирование", "Библиотека для пользовательских интерфейсов"),
    ("HTML/CSS", "Программирование", "Разметка и стилизация веб-страниц"),
    ("Docker", "Инструменты", "Контейнеризация приложений"),
    ("Алгоритмы и структуры данных", "Программирование", "Базовые алгоритмы и структуры данных"),
    ("Pandas", "Данные", "Библиотека анализа данных на Python"),
    ("Machine Learning", "Данные", "Машинное обучение и модели"),
    ("Testing", "QA", "Тестирование и обеспечение качества ПО"),
    ("Figma", "Дизайн", "Инструмент дизайна интерфейсов"),
    ("UI/UX", "Дизайн", "Проектирование пользовательского опыта"),
    ("Коммуникация", "Soft skills", "Навыки общения и работы в команде"),
    ("Тайм-менеджмент", "Soft skills", "Управление временем и приоритетами"),
]

# Каждая миссия: skill, difficulty, scenario, options [(text, is_correct)], explanation, reward_xp
SEED_MISSIONS: list[dict[str, Any]] = [
    {
        "skill": "Python",
        "difficulty": "easy",
        "scenario": "Нужно вывести сумму чисел от 1 до n включительно. Какой вызов корректнее всего?",
        "options": [
            ("print(sum(n))", False),
            ("print(range(1, n).sum())", False),
            ("print(n + 1)", False),
            ("print(sum(range(1, n + 1)))", True),
        ],
        "explanation": "sum(range(1, n + 1)) суммирует все числа от 1 до n включительно.",
        "reward_xp": 20,
    },
    {
        "skill": "Python",
        "difficulty": "medium",
        "scenario": "Что вернёт выражение [x ** 2 for x in range(4)]?",
        "options": [
            ("[0, 2, 4, 6]", False),
            ("Ошибка: list comprehension не работает с range", False),
            ("[0, 1, 4, 9]", True),
            ("[1, 4, 9, 16]", False),
        ],
        "explanation": "range(4) даёт 0..3, квадраты: 0, 1, 4, 9.",
        "reward_xp": 35,
    },
    {
        "skill": "Python",
        "difficulty": "medium",
        "scenario": "Как безопасно обработать деление на ноль?",
        "options": [
            ("a // 0 — Python сам вернёт 0", False),
            ("try: ... except ZeroDivisionError: ...", True),
            ("if a / 0: ...", False),
            ("catch (ZeroDivisionError) { ... }", False),
        ],
        "explanation": "Деление на ноль вызывает ZeroDivisionError — его нужно перехватывать.",
        "reward_xp": 35,
    },
    {
        "skill": "SQL",
        "difficulty": "easy",
        "scenario": "Выбрать всех пользователей старше 18 лет из таблицы users.",
        "options": [
            ("SELECT users WHERE age > 18;", False),
            ("GET * FROM users WHERE age MORE 18;", False),
            ("SELECT * FROM users HAVING age > 18;", False),
            ("SELECT * FROM users WHERE age > 18;", True),
        ],
        "explanation": "Фильтрация строк выполняется через WHERE.",
        "reward_xp": 20,
    },
    {
        "skill": "SQL",
        "difficulty": "medium",
        "scenario": "Посчитать количество заказов на каждого клиента.",
        "options": [
            ("SELECT COUNT(*) FROM orders ORDER BY client_id;", False),
            ("SELECT client_id WHERE COUNT(*) > 1;", False),
            ("SELECT client_id, COUNT(*) FROM orders GROUP BY client_id;", True),
            ("SELECT client_id, SUM(*) FROM orders;", False),
        ],
        "explanation": "GROUP BY разбивает строки по клиентам, COUNT(*) считает заказы.",
        "reward_xp": 35,
    },
    {
        "skill": "Git",
        "difficulty": "easy",
        "scenario": "Как посмотреть состояние изменений в репозитории?",
        "options": [
            ("git stage", False),
            ("git status", True),
            ("git show", False),
            ("git log", False),
        ],
        "explanation": "git status показывает изменённые, новые и добавленные файлы.",
        "reward_xp": 20,
    },
    {
        "skill": "Git",
        "difficulty": "medium",
        "scenario": "Вы создали ветку feature и хотите переключиться на неё.",
        "options": [
            ("git push feature", False),
            ("git commit feature", False),
            ("git status feature", False),
            ("git checkout feature", True),
        ],
        "explanation": "git checkout <ветка> переключает на указанную ветку.",
        "reward_xp": 30,
    },
    {
        "skill": "JavaScript",
        "difficulty": "easy",
        "scenario": "Какое ключевое слово создаёт неизменяемую переменную?",
        "options": [
            ("var", False),
            ("static", False),
            ("const", True),
            ("let", False),
        ],
        "explanation": "const объявляет константу, её нельзя переприсвоить.",
        "reward_xp": 20,
    },
    {
        "skill": "React",
        "difficulty": "medium",
        "scenario": "Как в React передать данные из родительского компонента в дочерний?",
        "options": [
            ("Через alert()", False),
            ("Через props", True),
            ("Через глобальные переменные", False),
            ("Через прямое изменение DOM", False),
        ],
        "explanation": "Данные передаются сверху вниз через props.",
        "reward_xp": 35,
    },
    {
        "skill": "Testing",
        "difficulty": "easy",
        "scenario": "Что проверяет юнит-тест?",
        "options": [
            ("Скорость работы сервера", False),
            ("Визуальный дизайн интерфейса", False),
            ("Доступность сайта извне", False),
            ("Работу отдельной функции или модуля", True),
        ],
        "explanation": "Юнит-тесты проверяют поведение изолированных единиц кода.",
        "reward_xp": 20,
    },
    {
        "skill": "Docker",
        "difficulty": "medium",
        "scenario": "Какой файл описывает образ контейнера?",
        "options": [
            ("requirements.txt", False),
            ("package.json", False),
            ("Dockerfile", True),
        ],
        "explanation": "Dockerfile описывает шаги сборки образа.",
        "reward_xp": 30,
    },
    {
        "skill": "Алгоритмы и структуры данных",
        "difficulty": "easy",
        "scenario": "Какая сложность у пузырьковой сортировки в худшем случае?",
        "options": [
            ("O(1)", False),
            ("O(n²)", True),
            ("O(n)", False),
            ("O(n log n)", False),
        ],
        "explanation": "Вложенные циклы дают квадратичную сложность O(n²).",
        "reward_xp": 20,
    },
    {
        "skill": "Алгоритмы и структуры данных",
        "difficulty": "medium",
        "scenario": "Какая структура данных работает по принципу FIFO («первым пришёл — первым вышел»)?",
        "options": [
            ("Стек (stack)", False),
            ("Дерево (tree)", False),
            ("Хеш-таблица (hash map)", False),
            ("Очередь (queue)", True),
        ],
        "explanation": "Очередь обслуживает элементы в порядке их добавления.",
        "reward_xp": 30,
    },
    {
        "skill": "FastAPI",
        "difficulty": "hard",
        "scenario": "Как объявить endpoint, принимающий JSON-тело, в FastAPI?",
        "options": [
            ("def create(): return request.read_json()", False),
            ("def create(item: int): ...", False),
            ("def create(item: Item): ..., где Item — Pydantic-модель", True),
            ("def create(item: str): ...", False),
        ],
        "explanation": "FastAPI валидирует JSON-тело по Pydantic-модели из аннотации.",
        "reward_xp": 50,
    },
    {
        "skill": "Pandas",
        "difficulty": "medium",
        "scenario": "Как прочитать CSV-файл в Pandas?",
        "options": [
            ("pd.open('data.csv')", False),
            ("pd.read_csv('data.csv')", True),
            ("pd.load('data.csv')", False),
            ("csv.read_file('data.csv')", False),
        ],
        "explanation": "read_csv — основной способ чтения табличных данных.",
        "reward_xp": 30,
    },
    {
        "skill": "UI/UX",
        "difficulty": "easy",
        "scenario": "Что такое UX-дизайн?",
        "options": [
            ("Создание логотипа компании", False),
            ("Написание кода интерфейса", False),
            ("Настройка серверов", False),
            ("Проектирование удобства и логики взаимодействия", True),
        ],
        "explanation": "UX отвечает за удобство и понятность интерфейса для пользователя.",
        "reward_xp": 20,
    },
    {
        "skill": "Figma",
        "difficulty": "easy",
        "scenario": "Какой инструмент Figma используется для создания прототипа?",
        "options": [
            ("Styles", False),
            ("Export", False),
            ("Prototype", True),
            ("Layers", False),
        ],
        "explanation": "Вкладка Prototype связывает экраны в интерактивный прототип.",
        "reward_xp": 20,
    },
    {
        "skill": "Machine Learning",
        "difficulty": "hard",
        "scenario": "Что такое переобучение (overfitting)?",
        "options": [
            ("Модель работает только на GPU", False),
            ("Модель слишком точно запомнила обучающие данные и плохо обобщает", True),
            ("Модель слишком проста и не может выучить данные", False),
            ("Модель обучается быстрее, чем нужно", False),
        ],
        "explanation": "Переобучение — потеря обобщающей способности из-за «заучивания» данных.",
        "reward_xp": 50,
    },
]

# Курсы: title, description, platform, url, level, category, cost, format, skills
SEED_COURSES: list[dict[str, Any]] = [
    {
        "title": "Поколение Python: курс для начинающих",
        "description": "Базовый курс по Python: синтаксис, циклы, функции, ООП.",
        "platform": "Stepik",
        "url": "https://stepik.org/course/58852",
        "level": "beginner",
        "category": "Программирование",
        "cost": 0.0,
        "format": "online",
        "skills": ["Python"],
    },
    {
        "title": "Python: основы и применение",
        "description": "Углублённый Python: стандартная библиотека, тесты, типизация.",
        "platform": "Stepik",
        "url": "https://stepik.org/course/512",
        "level": "intermediate",
        "category": "Программирование",
        "cost": 0.0,
        "format": "online",
        "skills": ["Python", "Git"],
    },
    {
        "title": "Интерактивный тренажёр по SQL",
        "description": "SQL с нуля: запросы, JOIN, агрегации прямо в браузере.",
        "platform": "Stepik",
        "url": "https://stepik.org/course/63054",
        "level": "beginner",
        "category": "Данные",
        "cost": 0.0,
        "format": "online",
        "skills": ["SQL"],
    },
    {
        "title": "Основы Git",
        "description": "Git для начинающих: commit, ветки, GitHub.",
        "platform": "YouTube",
        "url": "https://www.youtube.com/results?search_query=git+для+начинающих",
        "level": "beginner",
        "category": "Инструменты",
        "cost": 0.0,
        "format": "online",
        "skills": ["Git"],
    },
    {
        "title": "Алгоритмы и структуры данных",
        "description": "Сортировки, деревья, графы, сложность алгоритмов.",
        "platform": "Яндекс Практикум",
        "url": "https://practicum.yandex.ru/algorithms/",
        "level": "intermediate",
        "category": "Программирование",
        "cost": 1990.0,
        "format": "online",
        "skills": ["Алгоритмы и структуры данных", "Python"],
    },
    {
        "title": "React для начинающих",
        "description": "Компоненты, props, state, хуки и сборка проекта.",
        "platform": "Skillbox",
        "url": "https://skillbox.ru/course/react/",
        "level": "intermediate",
        "category": "Программирование",
        "cost": 2500.0,
        "format": "online",
        "skills": ["React", "JavaScript"],
    },
    {
        "title": "Docker и контейнеризация",
        "description": "Образы, контейнеры, docker-compose, деплой.",
        "platform": "OTUS",
        "url": "https://otus.ru/lessons/docker/",
        "level": "advanced",
        "category": "Инструменты",
        "cost": 3000.0,
        "format": "online",
        "skills": ["Docker"],
    },
    {
        "title": "Анализ данных на Python",
        "description": "Pandas, визуализация, очистка данных и отчёты.",
        "platform": "Яндекс Практикум",
        "url": "https://practicum.yandex.ru/data-analysis/",
        "level": "intermediate",
        "category": "Данные",
        "cost": 2490.0,
        "format": "online",
        "skills": ["Pandas", "Python"],
    },
    {
        "title": "Machine Learning: введение",
        "description": "Линейные модели, метрики, переобучение, базовые пайплайны.",
        "platform": "Coursera",
        "url": "https://www.coursera.org/specializations/machine-learning-introduction",
        "level": "advanced",
        "category": "Данные",
        "cost": 1500.0,
        "format": "online",
        "skills": ["Machine Learning", "Python"],
    },
    {
        "title": "Тестирование ПО для начинающих",
        "description": "Виды тестирования, тест-кейсы, основы автоматизации.",
        "platform": "Stepik",
        "url": "https://stepik.org/course/118786",
        "level": "beginner",
        "category": "QA",
        "cost": 0.0,
        "format": "online",
        "skills": ["Testing"],
    },
    {
        "title": "Figma: с нуля до макетов",
        "description": "Инструменты Figma, компоненты, автолейаут, экспорт.",
        "platform": "Skillbox",
        "url": "https://skillbox.ru/course/figma/",
        "level": "beginner",
        "category": "Дизайн",
        "cost": 1500.0,
        "format": "online",
        "skills": ["Figma", "UI/UX"],
    },
    {
        "title": "UI/UX-дизайнер",
        "description": "Исследования, прототипирование, дизайн-системы.",
        "platform": "Яндекс Практикум",
        "url": "https://practicum.yandex.ru/ui-design/",
        "level": "intermediate",
        "category": "Дизайн",
        "cost": 2990.0,
        "format": "online",
        "skills": ["UI/UX", "Figma"],
    },
    {
        "title": "Frontend-разработчик",
        "description": "HTML/CSS, JavaScript, React и сборка фронтенд-проекта.",
        "platform": "Яндекс Практикум",
        "url": "https://practicum.yandex.ru/frontend-developer/",
        "level": "intermediate",
        "category": "Программирование",
        "cost": 2900.0,
        "format": "online",
        "skills": ["JavaScript", "React", "HTML/CSS"],
    },
    {
        "title": "FastAPI: современный бэкенд",
        "description": "REST API на FastAPI: роуты, валидация, SQLAlchemy, документация.",
        "platform": "YouTube",
        "url": "https://www.youtube.com/results?search_query=fastapi+курс",
        "level": "intermediate",
        "category": "Программирование",
        "cost": 0.0,
        "format": "online",
        "skills": ["FastAPI", "Python"],
    },
]

# Стажировки: title, company, description, url, level, city, remote, format, requirements, direction, skills
SEED_INTERNSHIPS: list[dict[str, Any]] = [
    {
        "title": "Стажировка Python-разработчик",
        "company": "Яндекс",
        "description": "Полгода практики в бэкенд-командах с ментором.",
        "url": "https://yandex.ru/jobs/internships",
        "level": "beginner",
        "city": "Москва",
        "remote": False,
        "format": "office",
        "requirements": "Базовый Python, желательно SQL и Git",
        "direction": "backend",
        "skills": ["Python", "SQL", "Git"],
    },
    {
        "title": "Веб-разработчик (React)",
        "company": "VK",
        "description": "Практика в веб-команде над продуктовыми интерфейсами.",
        "url": "https://vk.company/career/",
        "level": "beginner",
        "city": "Санкт-Петербург",
        "remote": False,
        "format": "office",
        "requirements": "JavaScript, HTML/CSS, базовый React",
        "direction": "frontend",
        "skills": ["JavaScript", "React", "HTML/CSS"],
    },
    {
        "title": "Аналитик данных",
        "company": "Т-Банк",
        "description": "Удалённая работа с данными: отчёты, метрики, исследования.",
        "url": "https://www.tbank.ru/career/",
        "level": "intermediate",
        "city": "Москва",
        "remote": True,
        "format": "remote",
        "requirements": "SQL, Pandas, Python",
        "direction": "data",
        "skills": ["SQL", "Pandas", "Python"],
    },
    {
        "title": "QA-инженер",
        "company": "Ozon",
        "description": "Ручное и автоматизированное тестирование сервисов.",
        "url": "https://job.ozon.ru/",
        "level": "beginner",
        "city": "Казань",
        "remote": False,
        "format": "office",
        "requirements": "Внимательность, базовые SQL и тестирование",
        "direction": "qa",
        "skills": ["Testing", "SQL"],
    },
    {
        "title": "UI/UX-дизайнер",
        "company": "Сбер",
        "description": "Стажировка в продуктовом дизайне с наставником.",
        "url": "https://www.sberbank.ru/career",
        "level": "beginner",
        "city": "Москва",
        "remote": False,
        "format": "office",
        "requirements": "Figma, понимание UX",
        "direction": "design",
        "skills": ["Figma", "UI/UX"],
    },
    {
        "title": "Backend-стажировка Python",
        "company": "СКБ Контур",
        "description": "Удалённая стажировка с реальными задачами бэкенда.",
        "url": "https://kontur.ru/career",
        "level": "intermediate",
        "city": "Екатеринбург",
        "remote": True,
        "format": "remote",
        "requirements": "Python, SQL, Git; Docker — плюс",
        "direction": "backend",
        "skills": ["Python", "SQL", "Git", "Docker"],
    },
    {
        "title": "ML-стажёр",
        "company": "SberDevices",
        "description": "Работа над ML-пайплайнами и моделями.",
        "url": "https://sberdevices.ru/career",
        "level": "advanced",
        "city": "Москва",
        "remote": True,
        "format": "remote",
        "requirements": "Python, ML, Pandas",
        "direction": "data",
        "skills": ["Machine Learning", "Python", "Pandas"],
    },
    {
        "title": "Frontend-практика",
        "company": "Avito",
        "description": "Практика в команде интерфейсов маркетплейса.",
        "url": "https://career.avito.ru/",
        "level": "beginner",
        "city": "Москва",
        "remote": False,
        "format": "office",
        "requirements": "JavaScript, React",
        "direction": "frontend",
        "skills": ["JavaScript", "React"],
    },
]


# Роли: name, direction, level, description, skills [(skill_name, required_level, importance, is_mandatory)]
SEED_ROLES: list[dict[str, Any]] = [
    {
        "name": "Backend Junior",
        "direction": "backend",
        "level": "junior",
        "description": "Разработка серверной части: API, базы данных, интеграции.",
        "skills": [
            ("Python", 3, 0.9, True),
            ("SQL", 3, 0.8, True),
            ("FastAPI", 2, 0.6, False),
            ("Git", 2, 0.6, False),
            ("Docker", 1, 0.4, False),
        ],
    },
    {
        "name": "Frontend Junior",
        "direction": "frontend",
        "level": "junior",
        "description": "Разработка пользовательских интерфейсов на JavaScript/React.",
        "skills": [
            ("JavaScript", 3, 0.9, True),
            ("HTML/CSS", 3, 0.8, True),
            ("React", 2, 0.7, False),
            ("Git", 2, 0.5, False),
        ],
    },
    {
        "name": "QA Junior",
        "direction": "qa",
        "level": "junior",
        "description": "Тестирование ПО: ручное и автоматизированное.",
        "skills": [
            ("Testing", 3, 0.9, True),
            ("SQL", 2, 0.6, False),
            ("Git", 2, 0.5, False),
            ("Python", 1, 0.4, False),
        ],
    },
    {
        "name": "Data Analyst Junior",
        "direction": "data",
        "level": "junior",
        "description": "Анализ данных: SQL, Pandas, визуализация и отчёты.",
        "skills": [
            ("SQL", 3, 0.9, True),
            ("Python", 3, 0.8, True),
            ("Pandas", 2, 0.7, False),
            ("Git", 1, 0.4, False),
        ],
    },
    {
        "name": "ML Trainee",
        "direction": "data",
        "level": "trainee",
        "description": "Ученик в ML: базовые модели, пайплайны, работа с данными.",
        "skills": [
            ("Python", 3, 0.9, True),
            ("Machine Learning", 2, 0.7, True),
            ("Pandas", 2, 0.6, False),
            ("SQL", 2, 0.5, False),
        ],
    },
]


def seed_database(db: Session) -> int:
    """Идемпотентное наполнение базы демо-данными. Возвращает число записей."""
    if db.scalar(select(func.count(Skill.id))) or 0:
        return _seed_roles_if_empty(db)

    skills_by_name: dict[str, Skill] = {}
    for name, category, description in SEED_SKILLS:
        skill = Skill(name=name, category=category, description=description)
        db.add(skill)
        skills_by_name[name] = skill
    db.flush()  # присвоить id навыкам

    for mission_data in SEED_MISSIONS:
        mission = Mission(
            skill_id=skills_by_name[mission_data["skill"]].id,
            difficulty=mission_data["difficulty"],
            scenario=mission_data["scenario"],
            explanation=mission_data.get("explanation"),
            reward_xp=mission_data["reward_xp"],
        )
        for text, is_correct in mission_data["options"]:
            mission.options.append(MissionOption(text=text, is_correct=is_correct))
        db.add(mission)
    db.flush()

    for course_data in SEED_COURSES:
        course = Course(
            title=course_data["title"],
            description=course_data["description"],
            platform=course_data["platform"],
            url=course_data["url"],
            level=course_data["level"],
            category=course_data["category"],
            cost=course_data["cost"],
            format=course_data["format"],
        )
        course.skills = [skills_by_name[name] for name in course_data["skills"]]
        db.add(course)

    for internship_data in SEED_INTERNSHIPS:
        internship = Internship(
            title=internship_data["title"],
            company=internship_data["company"],
            description=internship_data["description"],
            url=internship_data["url"],
            level=internship_data["level"],
            city=internship_data["city"],
            remote=internship_data["remote"],
            format=internship_data["format"],
            requirements=internship_data["requirements"],
            direction=internship_data["direction"],
        )
        internship.skills = [skills_by_name[name] for name in internship_data["skills"]]
        db.add(internship)

    role_count = _seed_roles(db, skills_by_name)
    db.commit()
    return (
        len(SEED_SKILLS)
        + len(SEED_MISSIONS)
        + len(SEED_COURSES)
        + len(SEED_INTERNSHIPS)
        + role_count
    )


def _seed_roles(db: Session, skills_by_name: dict[str, Skill]) -> int:
    """Создать целевые роли и их требования к навыкам ровно один раз."""
    if db.scalar(select(func.count(Role.id))) or 0:
        return 0
    for role_data in SEED_ROLES:
        role = Role(
            name=role_data["name"],
            direction=role_data["direction"],
            level=role_data["level"],
            description=role_data.get("description"),
        )
        for name, required_level, importance, is_mandatory in role_data["skills"]:
            role.requirements.append(
                RoleSkill(
                    skill=skills_by_name[name],
                    required_level=required_level,
                    importance=importance,
                    is_mandatory=is_mandatory,
                )
            )
        db.add(role)
    db.flush()
    return len(SEED_ROLES) + sum(len(r["skills"]) for r in SEED_ROLES)


def _seed_roles_if_empty(db: Session) -> int:
    """До-сидировать роли в уже наполненной базе (обратная совместимость)."""
    if db.scalar(select(func.count(Role.id))) or 0:
        return 0
    skills_by_name = {skill.name: skill for skill in db.scalars(select(Skill))}
    role_count = _seed_roles(db, skills_by_name)
    db.commit()
    return role_count


def seed_if_empty() -> int:
    """Наполнить базу, если она пуста. Возвращает число добавленных записей."""
    from backend.app.database.session import SessionLocal

    with SessionLocal() as db:
        return seed_database(db)


if __name__ == "__main__":  # pragma: no cover (entry point, покрывается e2e-запуском)
    # python -m backend.app.seed
    added = seed_if_empty()
    print(f"Seed завершён: добавлено записей: {added}" if added else "База уже наполнена")
    sys.exit(0)
