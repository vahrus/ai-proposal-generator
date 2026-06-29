import os
import re
import uuid
from datetime import datetime
from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

STYLES = {
    "business": "деловой и формальный",
    "simple": "простой и понятный",
    "expert": "экспертный и аналитический",
    "confident": "уверенный и продающий",
}


def generate_with_openai(data: dict) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    style_label = STYLES.get(data["style"], "деловой и формальный")

    system_prompt = (
        "Ты — опытный консультант по AI-автоматизации. "
        "Ты пишешь коммерческие предложения для бизнеса на русском языке. "
        f"Стиль письма: {style_label}. "
        "Текст должен быть убедительным, конкретным и профессиональным."
    )

    user_prompt = f"""Создай коммерческое предложение по AI-автоматизации со следующими данными:

Клиент / компания: {data['client']}
Отрасль: {data['industry']}
Боль / проблема клиента: {data['problem']}
Предлагаемое AI-решение: {data['solution']}
Стоимость проекта: {data['price']}
Сроки реализации: {data['timeline']}

Верни ответ строго в следующем формате (с заголовками):

## Заголовок КП
[заголовок]

## Ситуация клиента
[2-3 предложения о текущей ситуации]

## Проблема
[описание боли клиента]

## Предлагаемое решение
[конкретное AI-решение]

## Этапы внедрения
[3-4 этапа с кратким описанием]

## Ожидаемые выгоды
[3-5 измеримых результатов]

## Стоимость и сроки
[стоимость и сроки]

## Следующий шаг
[призыв к действию]

## Полный текст КП
[готовый связный текст коммерческого предложения на 300-400 слов]"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content
    return parse_sections(raw)


def generate_fallback(data: dict) -> dict:
    """Генерация КП по шаблону без API."""
    style_label = STYLES.get(data["style"], "деловой и формальный")
    client = data["client"]
    industry = data["industry"]
    problem = data["problem"]
    solution = data["solution"]
    price = data["price"]
    timeline = data["timeline"]

    title = f"Коммерческое предложение: AI-автоматизация для {client}"

    situation = (
        f"Компания {client}, работающая в сфере {industry}, "
        f"сталкивается с растущими операционными нагрузками и конкурентным давлением. "
        f"Современный рынок требует скорости, точности и эффективности — "
        f"именно здесь AI-решения открывают новые возможности."
    )

    problem_text = (
        f"Ключевая проблема: {problem}. "
        f"Это приводит к потере времени сотрудников, снижению качества обслуживания "
        f"и упущенной прибыли. Без автоматизации ситуация будет усугубляться по мере роста бизнеса."
    )

    solution_text = (
        f"Мы предлагаем внедрить {solution}. "
        f"Решение разработано специально под задачи отрасли {industry} "
        f"и позволит {client} перевести рутинные процессы в режим автопилота, "
        f"освободив команду для стратегических задач."
    )

    stages = (
        "1. **Аудит и аналитика** — изучение текущих процессов, сбор требований (1-2 недели)\n"
        "2. **Разработка и интеграция** — построение AI-решения, подключение к существующим системам\n"
        "3. **Тестирование** — проверка на реальных данных, доработка по обратной связи\n"
        "4. **Запуск и обучение** — передача решения команде, документация и поддержка"
    )

    benefits = (
        f"- Экономия до 40% времени сотрудников на рутинных задачах\n"
        f"- Снижение количества ошибок и повышение качества данных\n"
        f"- Масштабируемость без пропорционального роста затрат\n"
        f"- Ускорение обработки запросов клиентов в 2-3 раза\n"
        f"- ROI окупаемости в первые 3-6 месяцев после запуска"
    )

    price_timeline = (
        f"**Стоимость:** {price}\n"
        f"**Сроки реализации:** {timeline}\n"
        f"Оплата поэтапная: 50% предоплата, 50% по завершению проекта."
    )

    next_step = (
        f"Готовы обсудить детали? Свяжитесь с нами для бесплатной 30-минутной консультации. "
        f"Мы проанализируем процессы {client} и покажем конкретный план внедрения."
    )

    full_text = f"""# {title}

Уважаемые коллеги из {client},

{situation}

**Проблема**
{problem_text}

**Наше решение**
{solution_text}

**Этапы внедрения**
{stages}

**Что вы получите**
{benefits}

**Инвестиции**
{price_timeline}

**Следующий шаг**
{next_step}

---
*Коммерческое предложение подготовлено в стиле: {style_label}*
*Сгенерировано: {datetime.now().strftime("%d.%m.%Y")} (демо-режим)*"""

    return {
        "title": title,
        "situation": situation,
        "problem": problem_text,
        "solution": solution_text,
        "stages": stages,
        "benefits": benefits,
        "price_timeline": price_timeline,
        "next_step": next_step,
        "full_text": full_text,
        "is_fallback": True,
    }


def parse_sections(raw: str) -> dict:
    """Парсит секции из ответа OpenAI."""
    section_map = {
        "title": r"##\s*Заголовок КП\s*\n(.*?)(?=\n##|\Z)",
        "situation": r"##\s*Ситуация клиента\s*\n(.*?)(?=\n##|\Z)",
        "problem": r"##\s*Проблема\s*\n(.*?)(?=\n##|\Z)",
        "solution": r"##\s*Предлагаемое решение\s*\n(.*?)(?=\n##|\Z)",
        "stages": r"##\s*Этапы внедрения\s*\n(.*?)(?=\n##|\Z)",
        "benefits": r"##\s*Ожидаемые выгоды\s*\n(.*?)(?=\n##|\Z)",
        "price_timeline": r"##\s*Стоимость и сроки\s*\n(.*?)(?=\n##|\Z)",
        "next_step": r"##\s*Следующий шаг\s*\n(.*?)(?=\n##|\Z)",
        "full_text": r"##\s*Полный текст КП\s*\n(.*?)(?=\n##|\Z)",
    }

    result = {"is_fallback": False}
    for key, pattern in section_map.items():
        match = re.search(pattern, raw, re.DOTALL)
        result[key] = match.group(1).strip() if match else ""

    if not result["full_text"]:
        result["full_text"] = raw

    return result


def save_output(content: str, fmt: str) -> str:
    os.makedirs("outputs", exist_ok=True)
    filename = f"proposal_{uuid.uuid4().hex[:8]}.{fmt}"
    filepath = os.path.join("outputs", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = {
        "client": request.form.get("client", "").strip(),
        "industry": request.form.get("industry", "").strip(),
        "problem": request.form.get("problem", "").strip(),
        "solution": request.form.get("solution", "").strip(),
        "price": request.form.get("price", "").strip(),
        "timeline": request.form.get("timeline", "").strip(),
        "style": request.form.get("style", "business"),
    }

    required = ["client", "industry", "problem", "solution", "price", "timeline"]
    missing = [f for f in required if not data[f]]
    if missing:
        return render_template("index.html", error="Заполните все обязательные поля.", form_data=data)

    api_key = os.getenv("OPENAI_API_KEY", "")

    try:
        if api_key and api_key != "your_api_key_here":
            result = generate_with_openai(data)
        else:
            result = generate_fallback(data)
    except Exception as e:
        result = generate_fallback(data)
        result["api_error"] = str(e)

    fmt = request.form.get("format", "md")
    filepath = save_output(result["full_text"], fmt)
    result["download_path"] = filepath
    result["filename"] = os.path.basename(filepath)
    result["input"] = data

    return render_template("result.html", result=result)


@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join("outputs", filename)
    if not os.path.exists(filepath):
        return "Файл не найден", 404
    ext = filename.rsplit(".", 1)[-1]
    mime = "text/markdown" if ext == "md" else "text/plain"
    return send_file(filepath, mimetype=mime, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
