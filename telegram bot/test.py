# =========================================================
# TELEGRAM AI LEARNING BOT - FULL WORKING CODE
# =========================================================
import smtplib
import os
import re
import json
import asyncio
from turtle import update
import psycopg2
from email.mime.text import MIMEText
from groq import Groq
from dotenv import load_dotenv
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# =========================================================
# GROQ
# =========================================================

client = Groq(api_key=GROQ_API_KEY)
# =========================================================
# GMAIL
# =========================================================

EMAIL_ADDRESS = "teddyvishwa123@gmail.com"

EMAIL_PASSWORD = "wqjo qxep yxpx ywds"

# =========================================================
# DATABASE
# =========================================================

conn = psycopg2.connect(
    host="localhost",
    database="study",
    user="postgres",
    password="VIVOT35G",
    port="5432"
)

cursor = conn.cursor()

print("✅ Database Connected")

# =========================================================
# MEMORY
# =========================================================

user_state = {}
quiz_state = {}
chat_memory = {}
otp_storage = {}

# =========================================================
# EMAIL VALIDATION
# =========================================================

def valid_email(email):

    pattern = r'^[a-z0-9._%+-]+@gmail\.com$'

    return re.match(pattern, email)

# =========================================================
# SEND OTP
# =========================================================

def send_otp(receiver_email):

    otp = str(random.randint(100000, 999999))

    body = f"""
Your Telegram Learning Bot OTP:

{otp}

Valid for 5 minutes.
"""

    msg = MIMEText(body)

    msg["Subject"] = "OTP Verification"

    msg["From"] = EMAIL_ADDRESS

    msg["To"] = receiver_email

    server = smtplib.SMTP("smtp.gmail.com", 587)

    server.starttls()

    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    server.send_message(msg)

    server.quit()

    return otp
# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(text):

    return re.sub(r'[*_`#]', '', text).strip()


# =========================================================
# AI CALL
# =========================================================

async def ai_call(messages):

    try:

        def run():

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.3,
                max_tokens=120
            )

            return response.choices[0].message.content

        return await asyncio.wait_for(
            asyncio.to_thread(run),
            timeout=35
        )

    except asyncio.TimeoutError:

        return "❌ AI timeout. Ask again."

    except Exception as e:

        print("AI ERROR:", e)

        return "❌ AI server busy."

# =========================================================
# SHOW SUBJECTS
# =========================================================

async def show_subjects(update, uid):

    cursor.execute("""
    SELECT sem
    FROM users
    WHERE user_id=%s
    """, (uid,))

    sem_data = cursor.fetchone()

    if not sem_data:

        return await update.message.reply_text(
            "❌ Semester not found"
        )

    sem = sem_data[0]

    cursor.execute("""
    SELECT DISTINCT subject
    FROM academic_data
    WHERE sem=%s
    """, (sem,))

    subjects = cursor.fetchall()

    if not subjects:

        return await update.message.reply_text(
            "❌ No subjects found"
        )

    buttons = []

    for s in subjects:

        buttons.append([
            InlineKeyboardButton(
                s[0],
                callback_data=f"subject|{s[0]}"
            )
        ])

    await update.message.reply_text(
        f"📚 Semester {sem} Subjects",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    cursor.execute("""
    SELECT name
    FROM users
    WHERE user_id=%s
    """, (uid,))

    user = cursor.fetchone()

    # EXISTING USER
    if user:

        await update.message.reply_text(
            f"👋 Welcome Back {user[0]}"
        )

        return await show_subjects(update, uid)

    # NEW USER
    user_state[uid] = {
        "step": "name"
    }

    await update.message.reply_text(
        "👤 Enter Your Name:"
    )

# =========================================================
# REGISTER
# =========================================================

async def register(update, uid, text):

    state = user_state[uid]

    # NAME
    if state["step"] == "name":

        state["name"] = text

        state["step"] = "email"

        return await update.message.reply_text(
            "📧 Enter Gmail:"
        )

    # EMAIL
    elif state["step"] == "email":

        if not valid_email(text):

            return await update.message.reply_text(
                "❌ Invalid Gmail\n\nExample:\nvishwa123@gmail.com"
            )

        otp = send_otp(text)

        otp_storage[uid] = {
            "otp": otp,
            "email": text
        }

        state["step"] = "otp"

        return await update.message.reply_text(
            f"""
📩 OTP sent to:

{text}

Enter OTP:
"""
        )

    # OTP
    elif state["step"] == "otp":

        if uid not in otp_storage:

            return await update.message.reply_text(
                "❌ OTP expired"
            )

        saved_otp = otp_storage[uid]["otp"]

        if text != saved_otp:

            return await update.message.reply_text(
                "❌ Wrong OTP"
            )

        state["email"] = otp_storage[uid]["email"]

        del otp_storage[uid]

        state["step"] = "university"

        return await update.message.reply_text(
            """
✅ Gmail Verified

🏫 Enter University:
"""
        )

    # UNIVERSITY
    elif state["step"] == "university":

        state["university"] = text

        state["step"] = "sem"

        return await update.message.reply_text(
            "🎓 Enter Semester:"
        )

        # SEM
    elif state["step"] == "sem":

        try:

            sem = int(text)

        except:

            return await update.message.reply_text(
                "❌ Enter valid semester"
            )

        cursor.execute("""
        INSERT INTO users (
            user_id,
            name,
            email,
            university,
            sem
        )

        VALUES (%s,%s,%s,%s,%s)

        ON CONFLICT (user_id)

        DO UPDATE SET
        name=EXCLUDED.name,
        email=EXCLUDED.email,
        university=EXCLUDED.university,
        sem=EXCLUDED.sem
        """, (
            uid,
            state["name"],
            state["email"],
            state["university"],
            sem
        ))

        conn.commit()

        del user_state[uid]

        await update.message.reply_text(
            "✅ Registration Completed"
        )

        return await show_subjects(update, uid)

# =========================================================
# PROFILE
# =========================================================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    cursor.execute("""
    SELECT name, email, university, sem
    FROM users
    WHERE user_id=%s
    """, (uid,))

    user = cursor.fetchone()

    if not user:

        return await update.message.reply_text(
            "❌ Profile not found"
        )

    await update.message.reply_text(
        f"""
👤 PROFILE

🧑 Name: {user[0]}

📧 Gmail:
{user[1]}

🏫 University:
{user[2]}

🎓 Semester:
{user[3]}
"""
    )

# =========================================================
# EDIT
# =========================================================

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    buttons = [
        [
            InlineKeyboardButton(
                "👤 Name",
                callback_data="edit_name"
            )
        ],
        [
            InlineKeyboardButton(
                "📧 Email",
                callback_data="edit_email"
            )
        ],
        [
            InlineKeyboardButton(
                "🎓 Semester",
                callback_data="edit_sem"
            )
        ]
    ]

    await update.message.reply_text(
        "⚙️ Select field to edit",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# =========================================================
# STATUS
# =========================================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    cursor.execute("""
    SELECT topic
    FROM progress
    WHERE user_id=%s
    """, (uid,))

    topics = cursor.fetchall()

    msg = f"""
📊 LIVE STATUS

✅ Completed Topics: {len(topics)}
"""

    for t in topics:

        msg += f"\n✅ {t[0]}"

    await update.message.reply_text(msg)

# =========================================================
# NEXT TOPIC
# =========================================================

async def next_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    cursor.execute("""
    SELECT topic
    FROM progress
    WHERE user_id=%s
    ORDER BY completed_at DESC
    LIMIT 1
    """, (uid,))

    last = cursor.fetchone()

    if not last:

        return await update.message.reply_text(
            "❌ Complete one topic first"
        )

    last_topic = last[0]

    cursor.execute("""
    SELECT id
    FROM academic_data
    WHERE topic=%s
    """, (last_topic,))

    current = cursor.fetchone()

    if not current:

        return await update.message.reply_text(
            "❌ Topic not found"
        )

    current_id = current[0]

    cursor.execute("""
    SELECT topic, subject, module
    FROM academic_data
    WHERE id > %s
    ORDER BY id ASC
    LIMIT 1
    """, (current_id,))

    nxt = cursor.fetchone()

    if not nxt:

        return await update.message.reply_text(
            "🎉 All topics completed"
        )

    topic = nxt[0]
    subject = nxt[1]
    module = nxt[2]

    answer = await ai_call([
        {
            "role": "system",
            "content": "You are a simple engineering teacher."
        },
        {
            "role": "user",
            "content": f"""
Explain {topic} in 3 short lines.

Simple English only.
"""
        }
    ])

    answer = clean_text(answer)

    sent = await update.message.reply_text(
        f"""
📘 Topic: {topic}

{answer}

✅ After studying type:
/completed
"""
    )

    quiz_state[uid] = {
        "subject": subject,
        "module": module,
        "topic": topic,
        "chat_id": sent.chat_id,
        "message_id": sent.message_id
    }

    chat_memory[uid] = [
    {
        "role": "system",
        "content": f"""
You are a STRICT engineering learning assistant.

Current Topic:
{topic}

IMPORTANT RULES:

Answer ONLY doubts related to:
{topic}


Allowed:
- definition
- explanation
- formula
- example
- application


If the question is not related to {topic}, reply exactly:

❌ Ask only topic related doubts


Never answer:
- current time
- weather
- politics
- movies
- sports
- general knowledge
- personal questions

📘 Current Topic:
{topic}

4. Keep answers short and simple.

5. Never change the topic.
"""
    }
]
# =========================================================
# BUTTONS
# =========================================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    uid = query.from_user.id

    data = query.data

    # EDIT NAME
    if data == "edit_name":

        user_state[uid] = {
            "edit": "name"
        }

        return await query.message.reply_text(
            "👤 Enter new name:"
        )

    # EDIT EMAIL
    elif data == "edit_email":

        user_state[uid] = {
            "edit": "email"
        }

        return await query.message.reply_text(
            "📧 Enter new gmail:"
        )

    # EDIT SEM
    elif data == "edit_sem":

        user_state[uid] = {
            "edit": "sem"
        }

        return await query.message.reply_text(
            "🎓 Enter new semester:"
        )

    # NORMAL BUTTONS
    parts = data.split("|")

    # SUBJECT
    if parts[0] == "subject":

        subject = parts[1]

        cursor.execute("""
        SELECT DISTINCT module
        FROM academic_data
        WHERE subject=%s
        """, (subject,))

        modules = cursor.fetchall()

        buttons = []

        for m in modules:

            buttons.append([
                InlineKeyboardButton(
                    m[0],
                    callback_data=f"module|{m[0]}"
                )
            ])

        return await query.edit_message_text(
            f"📘 {subject} Modules",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # MODULE
    elif parts[0] == "module":

        module = parts[1]

        cursor.execute("""
        SELECT topic, subject
        FROM academic_data
        WHERE module=%s
        """, (module,))

        topics = cursor.fetchall()

        buttons = []

        for t in topics:

            buttons.append([
                InlineKeyboardButton(
                    t[0],
                    callback_data=f"topic|{t[1]}|{module}|{t[0]}"
                )
            ])

        return await query.edit_message_text(
            f"📖 {module}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # TOPIC
    elif parts[0] == "topic":

        subject = parts[1]
        module = parts[2]
        topic = parts[3]

        await query.edit_message_text(
            "⏳ Generating explanation..."
        )

        answer = await ai_call([
            {
                "role": "system",
                "content": "You are a simple engineering teacher."
            },
            {
                "role": "user",
                "content": f"""
Explain {topic} in only 3 short lines.

Very simple English.
"""
            }
        ])

        answer = clean_text(answer)

        sent = await query.edit_message_text(
            f"""
📘 Topic: {topic}

{answer}

✅ After studying type:
/completed
"""
        )

        quiz_state[uid] = {
            "subject": subject,
            "module": module,
            "topic": topic,
            "chat_id": query.message.chat_id,
            "message_id": sent.message_id
        }

        chat_memory[uid] = [
            {
                "role": "system",
                "content": f"""
Current Topic:
{topic}

Answer only topic related doubts.
"""
            }
        ]

    # MCQ
    elif parts[0] == "mcq":

        selected_index = int(parts[1])

        options = quiz_state[uid]["options"]

        selected = options[selected_index]

        correct = quiz_state[uid]["correct"]

        info = quiz_state[uid]

        # CORRECT
        if selected == correct:

            cursor.execute("""
            INSERT INTO progress (
                user_id,
                department,
                subject,
                topic,
                completed
            )

            VALUES (%s,%s,%s,%s,TRUE)

            ON CONFLICT (user_id, topic)

            DO UPDATE SET
            completed=TRUE,
            completed_at=CURRENT_TIMESTAMP
            """, (
                uid,
                "Robotics and Automation",
                info["subject"],
                info["topic"]
            ))

            conn.commit()

            await query.edit_message_text(
                f"""
✅ Correct Answer

🎉 Topic Completed:
{info['topic']}

➡️ Use:
/nexttopic
"""
            )

        # WRONG
        else:

            mcq = await ai_call([
                {
                    "role": "system",
                    "content": "You are an engineering examiner."
                },
                {
                    "role": "user",
                    "content": f"""
Create another EASY MCQ from:
{info['topic']}

Return ONLY JSON.

Format:
{{
"question":"",
"options":["","","",""],
"correct":""
}}
"""
                }
            ])

            try:

                mcq_data = json.loads(mcq)

            except:

                return await query.answer(
                    "❌ MCQ generation failed",
                    show_alert=True
                )

            question = mcq_data["question"]

            options = mcq_data["options"]

            correct = mcq_data["correct"]

            quiz_state[uid]["correct"] = correct
            quiz_state[uid]["options"] = options

            buttons = []

            for i, opt in enumerate(options):

                buttons.append([
                    InlineKeyboardButton(
                        opt,
                        callback_data=f"mcq|{i}"
                    )
                ])

            await query.edit_message_text(
                f"""
❌ Wrong Answer

🔁 Try Again

📝 {question}
""",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

# =========================================================
# COMPLETED
# =========================================================

async def completed(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    if uid not in quiz_state:

        return await update.message.reply_text(
            "❌ Select topic first"
        )

    data = quiz_state[uid]

    try:

        await context.bot.delete_message(
            chat_id=data["chat_id"],
            message_id=data["message_id"]
        )

    except:
        pass

    topic = data["topic"]

    mcq = await ai_call([
        {
            "role": "system",
            "content": "You are an engineering examiner."
        },
        {
            "role": "user",
            "content": f"""
Create one EASY MCQ from:
{topic}

Return ONLY JSON.

Format:
{{
"question":"",
"options":["","","",""],
"correct":""
}}
"""
        }
    ])

    try:

        mcq_data = json.loads(mcq)

    except:

        return await update.message.reply_text(
            "❌ Failed generating MCQ"
        )

    question = mcq_data["question"]

    options = mcq_data["options"]

    correct = mcq_data["correct"]

    quiz_state[uid]["correct"] = correct
    quiz_state[uid]["options"] = options

    buttons = []

    for i, opt in enumerate(options):

        buttons.append([
            InlineKeyboardButton(
                opt,
                callback_data=f"mcq|{i}"
            )
        ])

    await update.message.reply_text(
        f"📝 {question}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# =========================================================
# CHAT
# =========================================================

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id

    text = update.message.text.strip()

    # REGISTRATION
    if uid in user_state and "step" in user_state[uid]:

        return await register(update, uid, text)

    # EDIT
    if uid in user_state and "edit" in user_state[uid]:

        edit_type = user_state[uid]["edit"]

        # NAME
        if edit_type == "name":

            cursor.execute("""
            UPDATE users
            SET name=%s
            WHERE user_id=%s
            """, (text, uid))

            conn.commit()

            del user_state[uid]

            return await update.message.reply_text(
                "✅ Name Updated"
            )

        # EMAIL
        elif edit_type == "email":

            if not valid_email(text):

                return await update.message.reply_text(
                    "❌ Invalid Gmail"
                )

            cursor.execute("""
            UPDATE users
            SET email=%s
            WHERE user_id=%s
            """, (text, uid))

            conn.commit()

            del user_state[uid]

            return await update.message.reply_text(
                "✅ Email Updated"
            )

        # SEM
        elif edit_type == "sem":

            try:

                sem = int(text)

            except:

                return await update.message.reply_text(
                    "❌ Enter valid semester"
                )

            cursor.execute("""
            UPDATE users
            SET sem=%s
            WHERE user_id=%s
            """, (sem, uid))

            conn.commit()

            del user_state[uid]

            return await update.message.reply_text(
                "✅ Semester Updated"
            )

    # TOPIC CHAT

    if uid in chat_memory:


     await update.message.reply_text(
        "🤖 Thinking..."
    )


    text_lower = text.lower()


    # get current topic
    topic_info = chat_memory[uid][0]["content"]


    # block unrelated questions
    blocked_words = [

        "time",
        "current time",
        "weather",
        "movie",
        "song",
        "cricket",
        "football",
        "president",
        "politics",
        "news",
        "joke",
        "game"

    ]


    if any(word in text_lower for word in blocked_words):

        return await update.message.reply_text(
            "❌ Ask only topic related doubts\n\n"
            + topic_info
        )



    chat_memory[uid].append({

        "role":"user",

        "content":text

    })



    if len(chat_memory[uid]) > 10:

        chat_memory[uid] = chat_memory[uid][-10:]



    answer = await ai_call(

        chat_memory[uid]

    )


    answer = clean_text(answer)



    chat_memory[uid].append({

        "role":"assistant",

        "content":answer

    })


    return await update.message.reply_text(
        answer
    )

    # save user message

    chat_memory[uid].append({
        "role": "user",
        "content": text
    })


    # keep only last 10 messages

    if len(chat_memory[uid]) > 10:

        chat_memory[uid] = chat_memory[uid][-10:]



    # Study only prompt

    prompt = [

        {
            "role": "system",

            "content": """
You are a STUDY ONLY AI assistant.

Your job:
Help students learn academic topics.

You can answer ONLY:

- Programming
- Computer Science
- Mathematics
- Science
- Engineering
- School subjects
- College subjects
- Exam preparation
- Learning concepts


IMPORTANT RULE:

If the user asks anything outside studies:

Do NOT answer.
Do NOT explain.
Do NOT give information.

Reply exactly:

"📚 I can help only with study related questions."


Examples:


User:
Explain Python loop

Assistant:
A loop is used to repeat...


User:
What is current time?

Assistant:
📚 I can help only with study related questions.


User:
Who is the president?

Assistant:
📚 I can help only with study related questions.


Always follow this rule.
"""
        }

    ]


# add conversation history
    prompt.extend(
        chat_memory[uid]
    )



    # call AI

    answer = await ai_call(
        prompt
    )



    answer = clean_text(answer)



    # save assistant response

    chat_memory[uid].append({

        "role": "assistant",

        "content": answer

    })



    return await update.message.reply_text(
        answer
    )



    await update.message.reply_text(
    "📚 Use /start"
)

# =========================================================
# RUN BOT
# =========================================================

app = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .read_timeout(120)
    .write_timeout(120)
    .connect_timeout(120)
    .pool_timeout(120)
    .build()
)

# COMMANDS
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("completed", completed))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("edit", edit))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(CommandHandler("nexttopic", next_topic))

# BUTTONS
app.add_handler(
    CallbackQueryHandler(buttons)
)

# CHAT
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat
    )
)

print("🚀 BOT RUNNING")

app.run_polling(
    drop_pending_updates=True,
    timeout=60
)