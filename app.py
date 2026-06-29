import os
import re
import uuid
import json
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

PROPOSAL_TYPES = {
    "ai_automation": "AI-автоматизация",
    "software": "Разработка ПО",
    "telegram_bot": "Telegram / MAX бот",
    "rag": "RAG база знаний",
    "n8n": "n8n автоматизация",
    "consulting": "AI-консалтинг",
}

PROPOSAL_TYPE_FOCUS = {
    "ai_automation": "экономии времени, снижении ручной работы и измеримом ROI от автоматизации процессов",
    "software": "архитектуре решения, поэтапной разработке, технической поддержке и масштабируемости",
    "telegram_bot": "автоматизации коммуникации в мессенджерах, обработке заявок 24/7 и росте конверсии обращений",
    "rag": "ускорении поиска по корпоративным документам, снижении нагрузки на поддержку и быстром онбординге сотрудников",
    "n8n": "интеграции разрозненных сервисов, автоматизации сценариев без написания кода и снижении затрат на разработку",
    "consulting": "аудите текущих процессов, конкретных гипотезах внедрения AI и практической дорожной карте трансформации",
}

FONT_SEARCH_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    os.path.expanduser("~/Library/Fonts/Arial.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def find_cyrillic_font() -> str | None:
    for path in FONT_SEARCH_PATHS:
        if os.path.exists(path):
            return path
    return None


def generate_pdf(result: dict, data: dict, filepath: str) -> bool:
    try:
        from fpdf import FPDF

        font_path = find_cyrillic_font()
        if not font_path:
            return False

        # Цвета: белый фон, тёмный текст — хорошо читается при печати
        C_TITLE      = (30, 20, 80)    # тёмно-фиолетовый для заголовка КП
        C_SECTION_BG = (243, 240, 255) # очень светло-фиолетовый фон секции
        C_SECTION_FG = (74, 32, 160)   # фиолетовый текст заголовка секции
        C_BODY       = (30, 30, 35)    # почти чёрный для основного текста
        C_META       = (100, 100, 115) # серый для мета-строки
        C_ACCENT     = (109, 40, 217)  # линия-разделитель
        C_FOOTER     = (150, 150, 165)

        class PDF(FPDF):
            def footer(self):
                self.set_y(-13)
                self.set_font("body", size=8)
                self.set_text_color(*C_FOOTER)
                date_str = datetime.now().strftime("%d.%m.%Y")
                self.cell(0, 8, f"AI Proposal Generator  •  {date_str}  •  Страница {self.page_no()}", align="C")

        pdf = PDF(orientation="P", unit="mm", format="A4")
        pdf.add_font("body", "", font_path)
        pdf.set_auto_page_break(auto=True, margin=22)
        pdf.set_margins(22, 22, 22)
        pdf.add_page()

        # --- Верхняя полоса-акцент ---
        pdf.set_fill_color(*C_ACCENT)
        pdf.rect(0, 0, 210, 3, style="F")
        pdf.ln(6)

        # --- Заголовок КП ---
        pdf.set_font("body", size=18)
        pdf.set_text_color(*C_TITLE)
        title = result.get("title", "Коммерческое предложение")
        pdf.multi_cell(0, 10, title, align="L")
        pdf.ln(2)

        # --- Мета-строка ---
        type_label = PROPOSAL_TYPES.get(data.get("proposal_type", ""), "")
        meta = "  •  ".join(
            p for p in [data.get("client", ""), data.get("industry", ""),
                        type_label, data.get("price", ""), data.get("timeline", "")] if p
        ).replace("₽", "руб.")
        pdf.set_font("body", size=10)
        pdf.set_text_color(*C_META)
        pdf.multi_cell(0, 6, meta, align="L")
        pdf.ln(4)

        # --- Разделитель ---
        pdf.set_draw_color(*C_ACCENT)
        pdf.set_line_width(0.5)
        pdf.line(22, pdf.get_y(), 188, pdf.get_y())
        pdf.ln(6)

        SECTIONS = [
            ("situation", "Ситуация клиента"),
            ("problem", "Проблема"),
            ("solution", "Предлагаемое решение"),
            ("stages", "Этапы внедрения"),
            ("benefits", "Ожидаемые выгоды"),
            ("price_timeline", "Стоимость и сроки"),
            ("next_step", "Следующий шаг"),
        ]

        for key, label in SECTIONS:
            text = result.get(key, "").strip()
            if not text:
                continue

            # Заголовок секции на светлом фоне
            pdf.set_fill_color(*C_SECTION_BG)
            pdf.set_text_color(*C_SECTION_FG)
            pdf.set_font("body", size=10)
            pdf.cell(0, 8, f"  {label.upper()}", ln=True, fill=True)
            pdf.ln(1)

            # Тело секции — тёмный текст, хорошо читается
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            clean = re.sub(r"^#{1,3}\s+", "", clean, flags=re.MULTILINE)
            clean = re.sub(r"^-\s+", "• ", clean, flags=re.MULTILINE)
            clean = clean.replace("₽", "руб.")

            pdf.set_font("body", size=10)
            pdf.set_text_color(*C_BODY)
            pdf.multi_cell(0, 6.5, clean, align="L")
            pdf.ln(5)

        pdf.output(filepath)
        return True

    except Exception as e:
        print(f"PDF generation failed: {e}")
        return False


def generate_fulltext_pdf(result: dict, data: dict, filepath: str) -> bool:
    """PDF с полным текстом КП — как единый документ для отправки клиенту."""
    try:
        from fpdf import FPDF

        font_path = find_cyrillic_font()
        if not font_path:
            return False

        C_TITLE  = (30, 20, 80)
        C_BODY   = (30, 30, 35)
        C_META   = (110, 110, 125)
        C_ACCENT = (109, 40, 217)
        C_FOOTER = (150, 150, 165)

        class PDF(FPDF):
            def footer(self):
                self.set_y(-13)
                self.set_font("body", size=8)
                self.set_text_color(*C_FOOTER)
                date_str = datetime.now().strftime("%d.%m.%Y")
                self.cell(0, 8, f"AI Proposal Generator  •  {date_str}  •  Страница {self.page_no()}", align="C")

        pdf = PDF(orientation="P", unit="mm", format="A4")
        pdf.add_font("body", "", font_path)
        pdf.set_auto_page_break(auto=True, margin=22)
        pdf.set_margins(22, 22, 22)
        pdf.add_page()

        # Верхняя полоса
        pdf.set_fill_color(*C_ACCENT)
        pdf.rect(0, 0, 210, 3, style="F")
        pdf.ln(6)

        # Заголовок
        pdf.set_font("body", size=17)
        pdf.set_text_color(*C_TITLE)
        pdf.multi_cell(0, 10, result.get("title", "Коммерческое предложение"), align="L")
        pdf.ln(2)

        # Мета-строка
        type_label = PROPOSAL_TYPES.get(data.get("proposal_type", ""), "")
        meta = "  •  ".join(
            p for p in [data.get("client", ""), data.get("industry", ""),
                        type_label, data.get("price", ""), data.get("timeline", "")] if p
        ).replace("₽", "руб.")
        pdf.set_font("body", size=10)
        pdf.set_text_color(*C_META)
        pdf.multi_cell(0, 6, meta, align="L")
        pdf.ln(4)

        # Разделитель
        pdf.set_draw_color(*C_ACCENT)
        pdf.set_line_width(0.5)
        pdf.line(22, pdf.get_y(), 188, pdf.get_y())
        pdf.ln(7)

        # Полный текст — разбиваем на абзацы, рендерим блоками
        full_text = result.get("full_text", "").replace("₽", "руб.")
        blocks = re.split(r"\n{2,}", full_text)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # H1
            if block.startswith("# "):
                pdf.set_font("body", size=15)
                pdf.set_text_color(*C_TITLE)
                pdf.multi_cell(0, 9, block[2:].strip())
                pdf.set_x(pdf.l_margin)
                pdf.ln(3)

            # H2 / H3
            elif block.startswith("#"):
                heading = re.sub(r"^#{1,3}\s+", "", block).strip()
                pdf.set_font("body", size=11)
                pdf.set_text_color(74, 32, 160)
                pdf.multi_cell(0, 7, heading.upper())
                pdf.set_x(pdf.l_margin)
                pdf.set_draw_color(200, 190, 240)
                pdf.set_line_width(0.3)
                pdf.line(pdf.l_margin, pdf.get_y(), 188, pdf.get_y())
                pdf.ln(4)

            # Разделитель ---
            elif re.match(r"^-{3,}$", block.strip()):
                pdf.set_draw_color(*C_ACCENT)
                pdf.set_line_width(0.4)
                pdf.line(pdf.l_margin, pdf.get_y(), 188, pdf.get_y())
                pdf.ln(4)

            # Обычный абзац
            else:
                clean = re.sub(r"\*\*(.+?)\*\*", r"\1", block)
                clean = re.sub(r"\*(.+?)\*", r"\1", clean)
                clean = re.sub(r"^-\s+", "• ", clean, flags=re.MULTILINE)
                clean = re.sub(r"^#{1,3}\s+", "", clean, flags=re.MULTILINE)
                pdf.set_font("body", size=11)
                pdf.set_text_color(*C_BODY)
                pdf.multi_cell(0, 7, clean)
                pdf.set_x(pdf.l_margin)
                pdf.ln(3)

        pdf.output(filepath)
        return True

    except Exception as e:
        print(f"Fulltext PDF failed: {e}")
        return False


def save_outputs(result: dict, data: dict) -> dict:
    os.makedirs("outputs", exist_ok=True)
    gen_id = uuid.uuid4().hex[:8]
    base = f"proposal_{gen_id}"
    files = {}

    md_path = os.path.join("outputs", f"{base}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result["full_text"])
    files["md"] = f"{base}.md"

    txt_path = os.path.join("outputs", f"{base}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["full_text"])
    files["txt"] = f"{base}.txt"

    pdf_path = os.path.join("outputs", f"{base}.pdf")
    if generate_pdf(result, data, pdf_path):
        files["pdf"] = f"{base}.pdf"

    full_pdf_path = os.path.join("outputs", f"{base}_full.pdf")
    if generate_fulltext_pdf(result, data, full_pdf_path):
        files["pdf_full"] = f"{base}_full.pdf"

    meta = {
        "id": gen_id,
        "title": result.get("title", "Коммерческое предложение"),
        "client": data.get("client", ""),
        "industry": data.get("industry", ""),
        "proposal_type": data.get("proposal_type", ""),
        "proposal_type_label": PROPOSAL_TYPES.get(data.get("proposal_type", ""), ""),
        "date": datetime.now().isoformat(),
        "date_display": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "files": files,
        "is_fallback": result.get("is_fallback", False),
    }
    with open(os.path.join("outputs", f"{base}.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {"id": gen_id, "base": base, "files": files}


def get_history(limit: int = 5) -> list:
    if not os.path.exists("outputs"):
        return []
    entries = []
    for fname in os.listdir("outputs"):
        if fname.startswith("proposal_") and fname.endswith(".json"):
            try:
                with open(os.path.join("outputs", fname), encoding="utf-8") as f:
                    entries.append(json.load(f))
            except Exception:
                continue
    entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    return entries[:limit]


def generate_with_openai(data: dict) -> dict:
    from openai import OpenAI

    client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    style_label = STYLES.get(data["style"], "деловой и формальный")
    proposal_type = data.get("proposal_type", "ai_automation")
    type_label = PROPOSAL_TYPES.get(proposal_type, "AI-автоматизация")
    type_focus = PROPOSAL_TYPE_FOCUS.get(proposal_type, "")

    system_prompt = (
        "Ты — опытный консультант по AI-автоматизации и цифровой трансформации бизнеса. "
        "Ты пишешь коммерческие предложения на русском языке. "
        f"Тип предложения: {type_label}. "
        f"Стиль: {style_label}. "
        f"Особый акцент: {type_focus}. "
        "Текст убедительный, конкретный с цифрами и измеримыми выгодами."
    )

    user_prompt = f"""Создай коммерческое предложение типа «{type_label}» со следующими данными:

Клиент / компания: {data['client']}
Отрасль: {data['industry']}
Боль / проблема клиента: {data['problem']}
Предлагаемое решение: {data['solution']}
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
[конкретное решение с акцентом на {type_focus}]

## Этапы внедрения
[3-4 этапа с кратким описанием]

## Ожидаемые выгоды
[3-5 измеримых результатов]

## Стоимость и сроки
[стоимость и сроки]

## Следующий шаг
[призыв к действию]

## Полный текст КП
[готовый связный текст коммерческого предложения на 350-450 слов]"""

    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2200,
    )
    return parse_sections(response.choices[0].message.content)


def generate_fallback(data: dict) -> dict:
    style_label = STYLES.get(data["style"], "деловой и формальный")
    proposal_type = data.get("proposal_type", "ai_automation")
    type_label = PROPOSAL_TYPES.get(proposal_type, "AI-автоматизация")
    type_focus = PROPOSAL_TYPE_FOCUS.get(proposal_type, "")

    client = data["client"]
    industry = data["industry"]
    problem = data["problem"]
    solution = data["solution"]
    price = data["price"]
    timeline = data["timeline"]

    title = f"Коммерческое предложение: {type_label} для {client}"

    situation = (
        f"Компания {client}, работающая в сфере {industry}, "
        f"сталкивается с растущими операционными нагрузками и конкурентным давлением. "
        f"Современный рынок требует скорости, точности и эффективности — "
        f"именно здесь решения в области {type_label.lower()} открывают новые возможности."
    )

    problem_text = (
        f"Ключевая проблема: {problem}. "
        f"Это приводит к потере времени сотрудников, снижению качества обслуживания "
        f"и упущенной прибыли. Без изменений ситуация будет усугубляться по мере роста бизнеса."
    )

    solution_text = (
        f"Мы предлагаем внедрить {solution}. "
        f"Решение разработано с упором на {type_focus}. "
        f"Подход позволит {client} перевести рутинные процессы в режим автопилота "
        f"и освободить команду для стратегических задач."
    )

    stages = (
        "1. **Аудит и аналитика** — изучение текущих процессов, сбор требований (1-2 недели)\n"
        "2. **Разработка и интеграция** — построение решения, подключение к существующим системам\n"
        "3. **Тестирование** — проверка на реальных данных, доработка по обратной связи\n"
        "4. **Запуск и обучение** — передача решения команде, документация и поддержка"
    )

    benefits = (
        "- Экономия до 40% времени сотрудников на рутинных задачах\n"
        "- Снижение количества ошибок и повышение качества данных\n"
        "- Масштабируемость без пропорционального роста затрат\n"
        "- Ускорение обработки запросов клиентов в 2-3 раза\n"
        "- ROI окупаемости в первые 3-6 месяцев после запуска"
    )

    price_timeline = (
        f"**Стоимость:** {price}\n"
        f"**Сроки реализации:** {timeline}\n"
        "Оплата поэтапная: 50% предоплата, 50% по завершению проекта."
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
*Тип предложения: {type_label} | Стиль: {style_label}*
*Дата: {datetime.now().strftime("%d.%m.%Y")} (демо-режим)*"""

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
    patterns = {
        "title":          r"##\s*Заголовок КП\s*\n(.*?)(?=\n##|\Z)",
        "situation":      r"##\s*Ситуация клиента\s*\n(.*?)(?=\n##|\Z)",
        "problem":        r"##\s*Проблема\s*\n(.*?)(?=\n##|\Z)",
        "solution":       r"##\s*Предлагаемое решение\s*\n(.*?)(?=\n##|\Z)",
        "stages":         r"##\s*Этапы внедрения\s*\n(.*?)(?=\n##|\Z)",
        "benefits":       r"##\s*Ожидаемые выгоды\s*\n(.*?)(?=\n##|\Z)",
        "price_timeline": r"##\s*Стоимость и сроки\s*\n(.*?)(?=\n##|\Z)",
        "next_step":      r"##\s*Следующий шаг\s*\n(.*?)(?=\n##|\Z)",
        "full_text":      r"##\s*Полный текст КП\s*\n(.*?)(?=\n##|\Z)",
    }
    result = {"is_fallback": False}
    for key, pattern in patterns.items():
        m = re.search(pattern, raw, re.DOTALL)
        result[key] = m.group(1).strip() if m else ""
    if not result["full_text"]:
        result["full_text"] = raw
    return result


@app.route("/")
def index():
    history = get_history()
    return render_template("index.html", history=history, proposal_types=PROPOSAL_TYPES)


@app.route("/generate", methods=["POST"])
def generate():
    data = {
        "client":        request.form.get("client", "").strip(),
        "industry":      request.form.get("industry", "").strip(),
        "problem":       request.form.get("problem", "").strip(),
        "solution":      request.form.get("solution", "").strip(),
        "price":         request.form.get("price", "").strip(),
        "timeline":      request.form.get("timeline", "").strip(),
        "style":         request.form.get("style", "business"),
        "proposal_type": request.form.get("proposal_type", "ai_automation"),
    }

    missing = [f for f in ["client", "industry", "problem", "solution", "price", "timeline"] if not data[f]]
    if missing:
        return render_template("index.html", error="Заполните все обязательные поля.",
                               form_data=data, history=get_history(), proposal_types=PROPOSAL_TYPES)

    api_key = os.getenv("OPENAI_API_KEY", "")
    try:
        if api_key and api_key not in ("your_api_key_here", ""):
            result = generate_with_openai(data)
        else:
            result = generate_fallback(data)
    except Exception as e:
        result = generate_fallback(data)
        result["api_error"] = str(e)

    saved = save_outputs(result, data)
    result["files"] = saved["files"]
    result["gen_id"] = saved["id"]
    result["input"] = data
    result["proposal_type_label"] = PROPOSAL_TYPES.get(data["proposal_type"], "")

    return render_template("result.html", result=result, proposal_types=PROPOSAL_TYPES)


@app.route("/download/<filename>")
def download(filename):
    # Sanitize: only allow filenames from outputs/
    safe_name = os.path.basename(filename)
    filepath = os.path.join("outputs", safe_name)
    if not os.path.exists(filepath):
        return "Файл не найден", 404
    ext = safe_name.rsplit(".", 1)[-1].lower()
    mime_map = {"md": "text/markdown", "txt": "text/plain", "pdf": "application/pdf"}
    return send_file(filepath, mimetype=mime_map.get(ext, "application/octet-stream"),
                     as_attachment=True, download_name=safe_name)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
