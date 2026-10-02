# Mlution

**From idea to ML solution.**

Mlution — AI-агент, который самостоятельно создаёт и улучшает ML-решения на основе описания задачи на естественном языке и загруженного CSV-файла. Вы описываете задачу — агент анализирует данные, планирует эксперимент, обучает несколько моделей, сравнивает метрики, критикует результат, улучшает решение и выдаёт отчёт, обученную модель и готовый Python-код для инференса.

MVP поддерживает табличные CSV-данные и три типа задач: **binary classification**, **multiclass classification**, **regression**.

## Возможности

- Автоматический Data Profile: строки/колонки, типы признаков, пропуски, дубликаты, числовые и категориальные колонки, дисбаланс классов.
- Детекция потенциальной target-колонки, ID-колонок и data leakage.
- Безопасный ограниченный набор моделей: Logistic/Linear Regression, Random Forest, HistGradientBoosting (+ CatBoost и Optuna как опциональные зависимости).
- Цикл улучшения `ANALYZE → PLAN → BUILD BASELINE → EVALUATE → CRITIQUE → IMPROVE → FINALIZE` с сохранением гипотез, действий и метрик «до/после».
- Live-статус работы агентов через SSE, чат с агентом, leaderboard экспериментов, confusion matrix, feature importance.
- Скачивание модели (`.joblib`) и сгенерированного Python-кода инференса; Prediction Playground с динамической формой признаков.
- Встроенный демо-датасет churn prediction — приложение работает без ручной загрузки файла.

## Архитектура

```
┌──────────────┐   HTTP/JSON + SSE   ┌───────────────────────────────────────┐
│   Frontend   │ ◄─────────────────► │                Backend                │
│ Next.js 14   │                     │  FastAPI + pandas + scikit-learn      │
│ TS/Tailwind  │                     │                                       │
└──────────────┘                     │  SupervisorAgent ──► DataAnalyst      │
                                     │        │             TaskPlanner      │
                                     │        │             FeatureEngineering
                                     │        │             ModelBuilder     │
                                     │        │             Experiment       │
                                     │        │             Critic           │
                                     │        └────────────► Report          │
                                     │  SQLite (данные) · joblib (артефакты) │
                                     └───────────────────────────────────────┘
```

Принцип разделения ответственности: **все числа и метрики производит только Python-код** (sklearn). LLM (опционально, через `LLM_API_KEY`) используется исключительно для нарративных объяснений и ответов в чате; без ключа работают детерминированные шаблоны — продукт полностью функционален и без LLM.

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API + Swagger: http://localhost:8000/docs

## Быстрый старт (локально, без Docker)

Требования: Python 3.10+, Node.js 18.17+.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
# . .venv/bin/activate               # Linux/macOS
pip install -r requirements.txt
python -m app.seed                   # демо-датасет + демо-проект
uvicorn app.main:app --port 8000

# Frontend (в другом терминале)
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Опциональные зависимости (CatBoost, Optuna) — `pip install -r requirements-optional.txt`. Без них backend автоматически использует sklearn-эквиваленты.

## Демо-сценарий

1. Откройте http://localhost:3000 → **Create project**.
2. Включите **Use built-in churn demo dataset** (telecom churn, 1500 строк, целевая колонка `churn`).
3. Нажмите **Run agent** — на странице workspace в реальном времени видны стадии пайплайна, события агентов и логи.
4. Через ~1–2 минуты: leaderboard из 3–4 экспериментов, лучшая модель, шаг улучшения (class weights + порог решения), отчёт.
5. Откройте **Results** (сравнение моделей, confusion matrix, feature importance, история улучшений) и **Playground** (тестовое предсказание).
6. Скачайте модель и Python-код кнопками **Download Model** / **Download Code**.

## End-to-end проверка

```bash
cd backend
.venv/Scripts/python scripts/e2e_demo.py   # требует запущенный сервер на :8000
```

Скрипт проходит весь путь: создание проекта → профиль данных → обучение → отчёт → предсказание → скачивание артефактов, с проверками на каждом шаге.

## API

| Method | Endpoint | Назначение |
|---|---|---|
| POST | `/api/projects` | Создать проект |
| POST | `/api/projects/{id}/dataset` | Загрузить CSV (или `demo=true`) |
| POST | `/api/projects/{id}/run` | Запустить пайплайн агента |
| GET | `/api/projects/{id}/status` | Статус и стадии пайплайна |
| GET | `/api/projects/{id}/events` `/events/stream` | События агентов (JSON / SSE) |
| GET | `/api/projects/{id}/profile` | Data Profile |
| GET | `/api/projects/{id}/experiments` | Leaderboard экспериментов |
| GET | `/api/projects/{id}/report` | Итоговый отчёт |
| GET | `/api/projects/{id}/model` | Скачать модель (.joblib) |
| GET | `/api/projects/{id}/code` | Скачать Python-код инференса |
| POST | `/api/projects/{id}/predict` | Предсказание по признакам |
| POST | `/api/projects/{id}/chat` | Чат с агентом |

Интерактивная документация: http://localhost:8000/docs (Swagger UI).

## Безопасность выполнения

- Обучение моделей выполняется только доверенным кодом backend'а; сгенерированный Python-код инференса предназначен для скачивания и **никогда не исполняется сервером**.
- В Docker ML-нагрузка изолирована контейнером backend'а: лимиты CPU (`2.0`) и RAM (`4G`) заданы в `docker-compose.yml`, рабочая директория — отдельный volume, сетевой доступ контейнеру не нужен для обучения.
- Каждый запуск ограничен временным бюджетом (`time_budget_seconds`) и лимитом экспериментов (`max_experiments`).
- Дополнительное укрепление для продакшена: вынос экспериментов в отдельный контейнер-воркер без сети, seccomp/AppArmor-профили, read-only root FS.

## Структура репозитория

```
Mlution/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, startup
│   │   ├── schemas.py         # Pydantic-схемы (Project, DatasetProfile, MLTask, ...)
│   │   ├── db.py              # SQLite
│   │   ├── agents/            # Supervisor, DataAnalyst, TaskPlanner, FeatureEngineering,
│   │   │                      # ModelBuilder, Experiment, Critic, Report
│   │   ├── services/          # runner (фон), storage, llm
│   │   ├── api/projects.py    # REST + SSE endpoints
│   │   ├── demo_data.py       # генератор демо-датасета churn
│   │   └── seed.py            # seed-скрипт
│   ├── scripts/e2e_demo.py    # end-to-end сценарий
│   └── requirements*.txt
└── frontend/
    ├── app/                   # landing, dashboard, new project, workspace, results, playground
    ├── components/            # shadcn-стиль UI + feature-компоненты
    └── lib/                   # API-клиент, типы, live-хуки
```

## Ограничения MVP

- Только табличные CSV; один файл на проект.
- Одно train/validation-разбиение без кросс-валидации; один шаг улучшения.
- Модели только из безопасного списка; CatBoost/Optuna — опционально.
